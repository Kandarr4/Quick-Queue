from flask import render_template, url_for, flash, redirect, request, g
from flask_login import login_required, current_user
from sqlalchemy.orm import Session

from ..models import User, Service, Ticket, ServiceAssignment
from ..forms import UserForm, ServiceForm, AssignServiceForm
from .. import db
from . import user
from ..db_manager import get_current_db

@user.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        flash('Доступ запрещен.', 'warning')
        return redirect(url_for('main_admin.admin_dashboard'))

    # Используем сессию БД организации вместо основной БД
    org_db = get_current_db()
    if not org_db:
        flash('Не удалось подключиться к базе данных организации.', 'danger')
        return redirect(url_for('main.login'))
    
    try:
        # Получаем настройки стиля пользователя
        style_type = getattr(current_user, 'style_type', 'default')
        org_username = getattr(current_user, 'org_username', None)
        
        # Определяем путь к файлу CSS в зависимости от настроек
        if style_type == 'custom' and org_username:
            css_path = f'css/{org_username}/user.css'
        else:
            css_path = 'css/operator_default.css'
        
        # Запросы через сессию БД организации
        assignments = org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()
        service_ids = [assignment.service_id for assignment in assignments]
        tickets_by_service = {}
        for service_id in service_ids:
            tickets = org_db.query(Ticket).filter_by(service_id=service_id).order_by(Ticket.number.asc()).all()
            filtered_tickets = [ticket for ticket in tickets if not ticket.user_id or ticket.user_id == current_user.id]
            tickets_by_service[service_id] = filtered_tickets

        has_active_ticket = any(
            org_db.query(Ticket).filter_by(service_id=service_id, user_id=current_user.id, status='at work').first()
            for service_id in service_ids
        )

        services = {service_id: org_db.query(Service).get(service_id) for service_id in service_ids}
        host = request.host.split(':')[0]
        port = 5551
        
        return render_template('user_dashboard.html',
                            assignments=assignments,
                            tickets_by_service=tickets_by_service,
                            services=services,
                            host=host,
                            port=port,
                            has_active_ticket=has_active_ticket,
                            css_path=css_path)
                            
    except Exception as e:
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
        return redirect(url_for('main.login'))