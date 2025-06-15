# app/tablo/routes.py

from flask import render_template, request, jsonify, redirect, url_for, flash, current_app, session, g
from flask_login import login_required, current_user
from app.db_manager import get_current_db, get_db_session
from app.models.secondary_admin import ServiceAssignment, Ticket, Service, User
from . import tablo
import os
import json

@tablo.route('/tablo_dashboard')
@login_required
def tablo_dashboard():
    if current_user.role != 'tablo':
        flash('Доступ запрещен.', 'warning')
        return redirect(url_for('main.home'))
    
    org_db = get_current_db()
    if not org_db:
        flash('Не удалось подключиться к базе данных организации.', 'danger')
        return redirect(url_for('main.login'))
    
    try:
        style_type = getattr(current_user, 'style_type', 'default')
        org_username = getattr(current_user, 'org_username', None)
        
        if style_type == 'custom' and org_username:
            css_path = f'css/{org_username}/tablo.css'
        else:
            css_path = 'css/tablo_default.css'
        
        settings = {'columns': 4, 'rows': 2, 'refresh_rate': 5}
        host = request.host.split(':')[0]
        port = 5551
        
        video_value = str(getattr(current_user, 'video', '0')) if getattr(current_user, 'video', None) is not None else '0'
        show_video = video_value != '0'
        video_folder = video_value if show_video else None
        
        fresh_user = org_db.query(User).get(current_user.id)
        marquee_text = getattr(fresh_user, 'marquee_text', None)
        
        return render_template('tablo_dashboard.html',
                            settings=settings,
                            host=host,
                            port=port,
                            show_video=show_video,
                            video_folder=video_folder,
                            marquee_text=marquee_text,
                            css_path=css_path)
                            
    except Exception as e:
        import traceback
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('main.login'))

        
@tablo.route('/tablo_data')
@login_required
def tablo_data():
    if current_user.role != 'tablo':
        return jsonify({"error": "Unauthorized"}), 403
    
    org_db = get_current_db()
    if not org_db:
        return jsonify({"error": "Database not found"}), 500
    
    try:
        assignments = org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()
        service_ids = [assignment.service_id for assignment in assignments]
        
        tickets = org_db.query(Ticket).filter(Ticket.service_id.in_(service_ids)).order_by(Ticket.issue_time).all()
        
        ticket_data = []
        for ticket in tickets:
            cabinet = "Неизвестно"
            if ticket.user_id:
                user = org_db.query(User).get(ticket.user_id)
                if user:
                    cabinet = user.cabinet or "Неизвестно"
            
            service = org_db.query(Service).get(ticket.service_id)
            service_name = service.name if service else "Неизвестно"
            
            ticket_data.append({
                'id': ticket.id,
                'number': ticket.number,
                'cabinet': cabinet,
                'status': ticket.status,
                'service_id': ticket.service_id,
                'service_name': service_name
            })
        
        return jsonify(ticket_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@tablo.route('/get_assigned_services')
@login_required
def get_assigned_services():
    if current_user.role != 'tablo':
        return jsonify({"error": "Unauthorized"}), 403
    
    org_db = get_current_db()
    if not org_db:
        return jsonify({"error": "Database not found"}), 500
    
    try:
        assignments = org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()
        service_ids = [assignment.service_id for assignment in assignments]
        
        return jsonify({"assigned_services": service_ids})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@tablo.route('/check_auth_status')
@login_required
def check_auth_status():
    return jsonify({"authenticated": current_user.is_authenticated})

@tablo.route('/get_video_list')
@login_required
def get_video_list():
    if current_user.role != 'tablo':
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        video_value = str(getattr(current_user, 'video', '0'))
        
        if video_value == '0':
            return jsonify({"videos": []})
        
        org_db = get_current_db()
        if not org_db:
            return jsonify({"error": "Database not found"}), 500
        
        admin_id = session.get('org_admin_id')
        
        from app.models.models_app import Admin
        
        database_name = None
        if admin_id:
            admin = Admin.query.get(admin_id)
            if admin:
                database_name = admin.database_name
        
        if not database_name and hasattr(g, 'current_org_db'):
            database_name = g.current_org_db
        
        if not database_name:
            try:
                connection = org_db.get_bind()
                db_url = str(connection.url)
                
                if '.db' in db_url:
                    db_path = db_url.split('///')[-1]
                    database_name = os.path.basename(db_path).replace('.db', '')
            except Exception:
                pass
        
        if not database_name:
            return jsonify({"error": "Could not determine database name"}), 500
        
        if video_value == '/':
            # Если в User.video указано "/", то ищем видео в корневой директории базы данных
            video_dir = os.path.join(current_app.static_folder, 'video', database_name)
        else:
            # Иначе ищем в директории видео со значением из User.video
            video_dir = os.path.join(current_app.static_folder, 'video', database_name, video_value)
        
        if not os.path.exists(video_dir):
            return jsonify({
                "videos": [], 
                "error": f"Video directory not found: {video_dir}",
                "database_name": database_name
            }), 404
        
        video_files = []
        for file in os.listdir(video_dir):
            if file.lower().endswith(('.mp4', '.webm', '.ogg')):
                if video_value == '/':
                    video_url = url_for('static', filename=f'video/{database_name}/{file}')
                else:
                    video_url = url_for('static', filename=f'video/{database_name}/{video_value}/{file}')
                video_files.append(video_url)
        
        return jsonify({
            "videos": video_files,
            "database_name": database_name,
            "video_dir": video_dir
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e)}), 500