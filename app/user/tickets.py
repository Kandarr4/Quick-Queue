from flask import jsonify
from flask_login import login_required, current_user

from .. import socketio
from ..models import Ticket, ServiceAssignment, Service, TicketStatistics
from ..utils import get_local_time
from . import user
from ..db_manager import get_current_db

@user.route('/call_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def call_ticket(ticket_id):
    # Используем сессию БД организации вместо основной БД
    org_db = get_current_db()
    if not org_db:
        return jsonify({'message': 'Не удалось подключиться к базе данных организации.', 'status': 'error'}), 500
    
    try:
        ticket = org_db.query(Ticket).get(ticket_id)
        if ticket:
            ticket.status = 'at work'
            ticket.user_id = current_user.id
            org_db.commit()

            now = get_local_time()
            stat = org_db.query(TicketStatistics).filter_by(
                service_id=ticket.service_id,
                date=ticket.issue_time.date(),
                issue_time=ticket.issue_time.time()
            ).first()
            if stat:
                stat.call_time = now.time()
                org_db.commit()

            socketio.emit('call_ticket', {
                'ticketNumber': ticket.number,
                'cabinetNumber': current_user.cabinet,
                'serviceId': ticket.service_id
            }, namespace='/voicing')

            return jsonify({'message': 'Ticket called', 'status': 'success'}), 200
        else:
            return jsonify({'message': 'Ticket not found', 'status': 'error'}), 404
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

@user.route('/remove_and_call_next_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def remove_and_call_next_ticket(ticket_id):
    # Используем сессию БД организации вместо основной БД
    org_db = get_current_db()
    if not org_db:
        return jsonify({'message': 'Не удалось подключиться к базе данных организации.', 'status': 'error'}), 500
    
    try:
        current_ticket = org_db.query(Ticket).get(ticket_id)
        if current_ticket:
            org_db.delete(current_ticket)
            org_db.commit()

        service_ids = [assignment.service_id for assignment in 
                      org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()]

        active_service_ids = set()
        for service_id in service_ids:
            active_ticket = org_db.query(Ticket).filter(
                Ticket.status == 'at work',
                Ticket.service_id == service_id,
                Ticket.user_id == current_user.id
            ).first()
            if active_ticket:
                active_service_ids.add(service_id)

        service_ids = [service_id for service_id in service_ids if service_id not in active_service_ids]

        if not service_ids:
            return jsonify({'status': 'error', 'message': 'Сперва надо вызвать клиента'}), 409

        next_ticket = org_db.query(Ticket).filter(
            Ticket.status == 'waiting',
            Ticket.service_id.in_(service_ids),
            Ticket.user_id.is_(None)
        ).order_by(Ticket.issue_time.asc()).first()

        if next_ticket:
            next_ticket.status = 'at work'
            next_ticket.user_id = current_user.id
            org_db.commit()

            now = get_local_time()
            next_stat = org_db.query(TicketStatistics).filter_by(
                service_id=next_ticket.service_id,
                date=next_ticket.issue_time.date(),
                issue_time=next_ticket.issue_time.time()
            ).first()
            if next_stat:
                next_stat.call_time = now.time()
                org_db.commit()

            socketio.emit('call_ticket', {
                'ticketNumber': next_ticket.number,
                'cabinetNumber': current_user.cabinet,
                'serviceId': next_ticket.service_id
            }, namespace='/voicing')

            return jsonify({
                'status': 'success',
                'message': 'Next ticket called, current ticket deleted',
                'ticket': {
                    'id': next_ticket.id,
                    'number': next_ticket.number,
                    'cabinet': current_user.cabinet
                },
                'announce': True
            }), 200
        else:
            return jsonify({'status': 'error', 'message': 'No next ticket available'}), 404
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

@user.route('/get_assigned_services')
@login_required
def get_assigned_services():
    # Используем сессию БД организации вместо основной БД
    org_db = get_current_db()
    if not org_db:
        return jsonify({'message': 'Не удалось подключиться к базе данных организации.', 'status': 'error'}), 500
    
    try:
        assignments = org_db.query(ServiceAssignment).filter_by(user_id=current_user.id).all()
        assigned_services = [assignment.service_id for assignment in assignments]
        return jsonify({'assigned_services': assigned_services})
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

@user.route('/delete_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def delete_ticket(ticket_id):
    # Используем сессию БД организации вместо основной БД
    org_db = get_current_db()
    if not org_db:
        return jsonify({'message': 'Не удалось подключиться к базе данных организации.', 'status': 'error'}), 500
    
    try:
        ticket = org_db.query(Ticket).get_or_404(ticket_id)
        org_db.delete(ticket)
        org_db.commit()
        return jsonify({'status': 'success', 'message': 'Ticket successfully deleted'}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500

@user.route('/delete_all_tickets/<int:service_id>', methods=['POST'])
@login_required
def delete_all_tickets(service_id):
    # Используем сессию БД организации вместо основной БД
    org_db = get_current_db()
    if not org_db:
        return jsonify({'message': 'Не удалось подключиться к базе данных организации.', 'status': 'error'}), 500
    
    try:
        service = org_db.query(Service).get(service_id)
        if not service:
            return jsonify({'message': 'Услуга не найдена'}), 404

        tickets_to_delete = org_db.query(Ticket).filter_by(service_id=service_id).all()
        for ticket in tickets_to_delete:
            org_db.delete(ticket)

        service.last_ticket_number = service.start_number - 1
        org_db.commit()

        return jsonify({'message': 'Все тикеты успешно удалены'}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}', 'status': 'error'}), 500