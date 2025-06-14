from flask import jsonify, request
from flask_login import login_required, current_user
from app.db_manager import get_current_db
from app.models.secondary_admin import Service, ServiceAssignment
from . import terminal

@terminal.route('/api/get_service_availability', methods=['GET'])
@login_required
def get_service_availability():
    if current_user.role != 'terminal':
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403

    # Получаем сессию БД организации
    org_db = get_current_db()
    if not org_db:
        return jsonify({'status': 'error', 'message': 'Database not found'}), 500
    
    # Получаем назначенные услуги
    assigned_services = org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()
    assigned_service_ids = [assignment.service_id for assignment in assigned_services]
    services = org_db.query(Service).filter(Service.id.in_(assigned_service_ids)).all()

    # Формируем данные о доступности услуг
    services_with_availability = []
    for service in services:
        is_available = True
        if hasattr(service, 'is_available_now'):
            is_available = service.is_available_now()
            
        services_with_availability.append({
            'id': service.id,
            'name': service.name,
            'cabinet': service.cabinet,
            'is_available': is_available
        })

    return jsonify({'status': 'success', 'services': services_with_availability})

@terminal.route('/service/<int:service_id>/is_available', methods=['GET'])
def is_service_available(service_id):
    # Получаем сессию БД организации
    org_db = get_current_db()
    if not org_db:
        return jsonify({'status': 'error', 'message': 'Database not found'}), 500
    
    # Получаем услугу
    service = org_db.query(Service).get(service_id)
    if not service:
        return jsonify({'status': 'error', 'message': 'Service not found'}), 404

    is_available = True
    if hasattr(service, 'is_available_now'):
        is_available = service.is_available_now()

    return jsonify({'status': 'success', 'is_available': is_available})