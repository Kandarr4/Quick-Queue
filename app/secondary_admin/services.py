# app/secondary_admin/services.py
from flask import request, jsonify, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import exc
from datetime import datetime

from app.db_manager import get_current_db
from app.models.secondary_admin import Service, ServiceAssignment, ServiceSchedule, Ticket, TicketStatistics
from app.forms import ServiceForm, AssignServiceForm
from . import secondary_admin

@secondary_admin.route('/add-service', methods=['POST'])
@login_required
def add_service():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    name = request.form.get('name')
    start_number = request.form.get('start_number', type=int)
    end_number = request.form.get('end_number', type=int)
    cabinet = request.form.get('cabinet', type=int)

    existing_service = org_db.query(Service).filter_by(name=name).first()
    if existing_service:
        return jsonify({'status': 'error', 'message': 'Услуга с таким названием уже существует. Выберите другое название.'}), 400

    service = Service(name=name, start_number=start_number, end_number=end_number, cabinet=cabinet)
    org_db.add(service)
    try:
        org_db.commit()
        return jsonify({
            'status': 'success',
            'message': 'Услуга добавлена.',
            'service': {
                'id': service.id,
                'name': service.name,
                'start_number': start_number,
                'end_number': end_number,
                'cabinet': cabinet
            }
        })
    except exc.IntegrityError:
        org_db.rollback()
        return jsonify({'status': 'error', 'message': 'Ошибка добавления услуги. Попробуйте снова.'}), 400

@secondary_admin.route('/edit-service/<int:service_id>', methods=['POST'])
@login_required
def edit_service(service_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500

    service = org_db.query(Service).get(service_id)
    if not service:
        return jsonify({'status': 'error', 'message': 'Услуга не найдена'}), 404
        
    data = request.get_json()

    form = ServiceForm(obj=service)
    form.name.data = data['name']
    form.start_number.data = data['start_number']
    form.end_number.data = data['end_number']
    form.cabinet.data = data['cabinet']

    if form.validate():
        try:
            service.name = form.name.data
            service.start_number = form.start_number.data
            service.end_number = form.end_number.data
            service.cabinet = form.cabinet.data
            org_db.commit()
            return jsonify({'status': 'success', 'message': 'Услуга успешно обновлена'})
        except exc.IntegrityError:
            org_db.rollback()
            return jsonify({'status': 'error', 'message': 'Ошибка сохранения данных.'}), 400
    else:
        return jsonify({'status': 'error', 'message': 'Ошибка валидации данных.', 'errors': form.errors}), 400

@secondary_admin.route('/service/<int:service_id>/schedule', methods=['GET'])
@login_required
def get_service_schedule(service_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    service = org_db.query(Service).get(service_id)
    if not service:
        return jsonify({'status': 'error', 'message': 'Service not found'}), 404

    schedules = org_db.query(ServiceSchedule).filter_by(service_id=service_id).all()
    schedule_list = [{'day_of_week': s.day_of_week,
                      'start_time': s.start_time.strftime('%H:%M'),
                      'end_time': s.end_time.strftime('%H:%M')} for s in schedules]
    return jsonify({'status': 'success', 'planName': service.name, 'schedules': schedule_list})

@secondary_admin.route('/service/<int:service_id>/schedule', methods=['POST'])
@login_required
def save_service_schedule(service_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    service = org_db.query(Service).get(service_id)
    if not service:
        return jsonify({'status': 'error', 'message': 'Service not found'}), 404

    data = request.get_json()
    if not data or 'schedule' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    try:
        # Удаляем старое расписание
        org_db.query(ServiceSchedule).filter_by(service_id=service_id).delete()
        
        # Добавляем новое расписание
        for item in data['schedule']:
            new_schedule = ServiceSchedule(
                service_id=service_id,
                day_of_week=item['day_of_week'],
                start_time=datetime.strptime(item['start_time'], '%H:%M').time(),
                end_time=datetime.strptime(item['end_time'], '%H:%M').time(),
            )
            org_db.add(new_schedule)
        org_db.commit()
        return jsonify({'status': 'success', 'message': 'Schedule updated successfully'})
    except Exception as e:
        org_db.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@secondary_admin.route('/load-services')
@login_required
def load_services():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    services = org_db.query(Service).all()
    services_data = [{'id': service.id, 'name': service.name} for service in services]
    return jsonify(services_data)

@secondary_admin.route('/delete-service/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    service = org_db.query(Service).get(service_id)
    if not service:
        return jsonify({'status': 'error', 'message': 'Услуга не найдена'}), 404

    # Удаляем связанные записи
    org_db.query(Ticket).filter_by(service_id=service_id).delete()
    org_db.query(ServiceAssignment).filter_by(service_id=service_id).delete()
    org_db.query(TicketStatistics).filter_by(service_id=service_id).delete()
    org_db.query(ServiceSchedule).filter_by(service_id=service_id).delete()

    # Удаляем саму услугу
    org_db.delete(service)
    org_db.commit()

    return jsonify({'message': 'Услуга успешно удалена.', 'service_id': service_id})

@secondary_admin.route('/assign_service_to_user', methods=['POST'])
@login_required
def assign_service_to_user():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    user_id = request.form.get('user_id')
    service_id = request.form.get('service_id')
    
    if not user_id or not service_id:
        return jsonify({'status': 'error', 'message': 'Не указан пользователь или услуга'}), 400
        
    # Проверяем существование пользователя и услуги
    if not org_db.query(Service).get(service_id):
        return jsonify({'status': 'error', 'message': 'Услуга не найдена'}), 404
        
    # Проверяем существование назначения
    existing = org_db.query(ServiceAssignment).filter_by(user_id=user_id, service_id=service_id).first()
    if existing:
        return jsonify({'status': 'error', 'message': 'Такое назначение уже существует. Нельзя назначить одну услугу дважды.'}), 400
        
    # Создаем назначение
    service_assignment = ServiceAssignment(
        user_id=user_id,
        service_id=service_id
    )
    org_db.add(service_assignment)
    org_db.commit()
    return jsonify({'status': 'success', 'message': 'Услуга успешно назначена'})

@secondary_admin.route('/user_service_tree/<int:user_id>')
@login_required
def user_service_tree(user_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500

    user_services = org_db.query(ServiceAssignment, Service.name, ServiceAssignment.id)\
        .join(Service, Service.id == ServiceAssignment.service_id)\
        .filter(ServiceAssignment.user_id == user_id)\
        .all()

    tree = [{'service': us[1], 'assignmentId': us[2]} for us in user_services]
    return jsonify(tree)

@secondary_admin.route('/delete_service_assignment/<int:assignment_id>', methods=['POST'])
@login_required
def delete_service_assignment(assignment_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500

    assignment = org_db.query(ServiceAssignment).get(assignment_id)
    if not assignment:
        return jsonify({'error': 'Назначение не найдено'}), 404
        
    org_db.delete(assignment)
    org_db.commit()

    return jsonify({'success': 'Зависимость успешно удалена'})