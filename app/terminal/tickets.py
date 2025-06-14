from flask import jsonify, request
from flask_login import login_required, current_user
from app.db_manager import get_current_db
from app.models.secondary_admin import Ticket, Service, ServiceAssignment, TicketStatistics
from app.utils import get_local_time
from . import terminal

@terminal.route('/generate_ticket/<int:service_id>', methods=['GET'])
def generate_ticket(service_id):
    # Получаем сессию БД организации
    org_db = get_current_db()
    if not org_db:
        return jsonify({'error': 'Database not found'}), 500
    
    # Получаем услугу
    service = org_db.query(Service).get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404

    # Проверяем доступность услуги
    is_available = True
    if hasattr(service, 'is_available_now'):
        is_available = service.is_available_now()
    
    if not is_available:
        return jsonify({'error': 'Услуга не доступна в данное время'}), 403

    # Генерируем следующий номер талона с учетом диапазона
    # Проверяем, находится ли last_ticket_number в допустимом диапазоне
    if service.last_ticket_number < service.start_number or service.last_ticket_number >= service.end_number:
        # Если last_ticket_number вне диапазона, сбрасываем на начальное значение
        next_number = service.start_number
    else:
        # Если last_ticket_number в диапазоне, увеличиваем на 1
        next_number = service.last_ticket_number + 1
        # Проверяем, не вышли ли за верхнюю границу
        if next_number >= service.end_number:
            next_number = service.start_number

    # Создаем новый талон
    now = get_local_time()
    new_ticket = Ticket(number=next_number, service_id=service.id, issue_time=now)
    org_db.add(new_ticket)
    service.last_ticket_number = next_number
    
    # Добавляем статистику
    stat = TicketStatistics(service_id=service.id, date=now.date(), issue_time=now.time())
    org_db.add(stat)
    org_db.commit()

    # Считаем количество активных талонов
    active_tickets_behind = org_db.query(Ticket).filter(
        Ticket.service_id == service.id, 
        Ticket.status == 'waiting',
        Ticket.id < new_ticket.id
    ).count()

    ticket_info = {
        'ticket_number': new_ticket.number,
        'service_name': service.name,
        'cabinet_number': service.cabinet,
        'issue_time': now.strftime('%H:%M:%S'),
        'active_tickets_behind': active_tickets_behind
    }

    # Отправляем уведомление операторам через Socket.IO
    assignments = org_db.query(ServiceAssignment).filter_by(service_id=service.id).all()
    
    try:
        from app import socketio
        for assignment in assignments:
            operator_id = assignment.user_id
            if operator_id:
                socketio.emit('new_ticket', {
                    'ticketNumber': new_ticket.number,
                    'serviceId': service.id,
                    'serviceName': service.name,
                    'issueTime': now.strftime('%H:%M')
                }, room=f'user_{operator_id}', namespace='/voicing')
    except Exception as e:
        # Логируем ошибку, но продолжаем выполнение
        print(f"Error sending socketio event: {e}")

    return jsonify(ticket_info)

@terminal.route('/check_service_availability', methods=['GET'])
@login_required
def check_service_availability():
    if current_user.role != 'terminal':
        return jsonify({'error': 'Access denied'}), 403

    # Получаем сессию БД организации
    org_db = get_current_db()
    if not org_db:
        return jsonify({'error': 'Database not found'}), 500
    
    # Получаем назначенные услуги
    assigned_services = org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()
    assigned_service_ids = [assignment.service_id for assignment in assigned_services]
    services = org_db.query(Service).filter(Service.id.in_(assigned_service_ids)).all()

    # Формируем данные о доступности услуг
    services_data = []
    for service in services:
        is_available = True
        if hasattr(service, 'is_available_now'):
            is_available = service.is_available_now()
            
        services_data.append({
            'id': service.id,
            'is_available': is_available
        })

    return jsonify({'services': services_data})