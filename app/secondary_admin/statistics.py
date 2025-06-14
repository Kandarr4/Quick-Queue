# app/secondary_admin/statistics.py
from datetime import datetime, timedelta, date
import calendar
from flask import jsonify, render_template, request
from flask_login import login_required, current_user

from app.db_manager import get_current_db
from app.models.secondary_admin import Service, TicketStatistics
from . import secondary_admin

@secondary_admin.route('/statistics')
@login_required
def statistics():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    services = org_db.query(Service).all()
    current_date = date.today().isoformat()
    return render_template('secondary_admin_statistics.html', services=services, current_date=current_date)

def get_ticket_statistics(org_db, service_id, period):
    today = date.today()
    if period == 'daily':
        start_date = today
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'monthly':
        start_date = today.replace(day=1)
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)

    stats = org_db.query(TicketStatistics).filter(
        TicketStatistics.service_id == service_id,
        TicketStatistics.date >= start_date
    ).all()

    return len(stats)  # Простой подсчет количества записей

@secondary_admin.route('/api/statistics/<int:service_id>', methods=['GET'])
@login_required
def get_statistics(service_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    stats = {
        'daily': get_ticket_statistics(org_db, service_id, period='daily'),
        'weekly': get_ticket_statistics(org_db, service_id, period='weekly'),
        'monthly': get_ticket_statistics(org_db, service_id, period='monthly'),
        'yearly': get_ticket_statistics(org_db, service_id, period='yearly'),
    }
    return jsonify(stats)

@secondary_admin.route('/api/statistics/<int:service_id>/daily', methods=['GET'])
@login_required
def get_daily_statistics(service_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    selected_date = request.args.get('date')
    if not selected_date:
        return jsonify({'error': 'Date not provided'}), 400

    date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
    stats = org_db.query(TicketStatistics).filter(
        TicketStatistics.service_id == service_id,
        TicketStatistics.date == date_obj
    ).all()

    return jsonify([
        {
            'date': stat.date.strftime('%Y-%m-%d'),
            'issue_time': stat.issue_time.strftime('%H:%M:%S') if stat.issue_time else None,
            'call_time': stat.call_time.strftime('%H:%M:%S') if stat.call_time else None
        } for stat in stats
    ])

@secondary_admin.route('/api/statistics/<int:service_id>/monthly', methods=['GET'])
@login_required
def get_monthly_statistics(service_id):
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        return jsonify({"status": "error", "message": "Доступ запрещен"}), 403
        
    org_db = get_current_db()
    if not org_db:
        return jsonify({"status": "error", "message": "Ошибка доступа к базе данных организации"}), 500
        
    selected_month = request.args.get('month')
    if not selected_month:
        return jsonify({'error': 'Month not provided'}), 400

    year, month = map(int, selected_month.split('-'))
    start_date = datetime(year, month, 1).date()
    end_date = (start_date + timedelta(days=calendar.monthrange(year, month)[1] - 1))

    stats = org_db.query(TicketStatistics).filter(
        TicketStatistics.service_id == service_id,
        TicketStatistics.date >= start_date,
        TicketStatistics.date <= end_date
    ).all()

    return jsonify([
        {
            'date': stat.date.strftime('%Y-%m-%d'),
            'issue_time': stat.issue_time.strftime('%H:%M:%S') if stat.issue_time else None,
            'call_time': stat.call_time.strftime('%H:%M:%S') if stat.call_time else None
        } for stat in stats
    ])