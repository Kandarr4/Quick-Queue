from flask import render_template, url_for, flash, redirect, request, g
from flask_login import login_required, current_user
from app.db_manager import get_current_db
from app.models.secondary_admin import Service, ServiceAssignment
from . import terminal

@terminal.route('/terminal_dashboard')
@login_required
def terminal_dashboard():
    if current_user.role != 'terminal':
        flash('Доступ запрещен.', 'warning')
        return redirect(url_for('main.home'))
    
    # Get the organization database session
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
            css_path = f'css/{org_username}/terminal.css'
        else:
            css_path = 'css/terminal_default.css'
        
        # Query the organization database using the session
        assigned_services = org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()
        assigned_service_ids = [assignment.service_id for assignment in assigned_services]
        services = org_db.query(Service).filter(Service.id.in_(assigned_service_ids)).all()

        # Add is_available check for each service
        services_with_availability = []
        for service in services:
            # If the service doesn't have an is_available_now method, default to True
            is_available = True
            if hasattr(service, 'is_available_now'):
                is_available = service.is_available_now()
                
            services_with_availability.append({
                'id': service.id,
                'name': service.name,
                'cabinet': service.cabinet,
                'is_available': is_available
            })

        # Добавим host и port для возможных веб-сокетов
        host = request.host.split(':')[0]
        port = 5551  # Предполагаемый порт для веб-сокетов

        return render_template('terminal_services.html', 
                            services=services_with_availability,
                            css_path=css_path,
                            host=host,
                            port=port)
                            
    except Exception as e:
        return redirect(url_for('main.login'))