# app/secondary_admin/routes.py
from flask import render_template, url_for, flash, redirect, g, jsonify, request
from flask_login import login_required, current_user
import os

from app.db_manager import get_current_db
from app.models.secondary_admin import User, Service, Ticket, ServiceAssignment
from app.forms import UserForm, ServiceForm, AssignServiceForm
from . import secondary_admin
from .groups import load_groups


@secondary_admin.route('/dashboard')
@login_required
def dashboard():
    if not hasattr(current_user, 'is_secondary_admin') or not current_user.is_secondary_admin:
        flash('Доступ разрешен только для администраторов организаций', 'danger')
        return redirect(url_for('main.index'))

    # Получаем сессию БД для текущего администратора
    org_db = get_current_db()
    if not org_db:
        flash('Ошибка доступа к базе данных организации', 'danger')
        return redirect(url_for('main.index'))

    # Используем org_db вместо прямого обращения к модели
    users = org_db.query(User).all()
    services = org_db.query(Service).all()

    # Загружаем группы пользователей
    groups = load_groups(current_user.database_name)
    
    # Создаем список ID пользователей, которые уже в группах
    group_users_ids = []
    for group in groups:
        if 'users' in group:
            group_users_ids.extend(group['users'])

    # Создаем формы
    user_form = UserForm()
    
    # Заполняем выпадающие списки формы для назначения услуг
    assign_service_form = AssignServiceForm()
    assign_service_form.user_id.choices = [(user.id, user.username) for user in users]
    assign_service_form.service_id.choices = [(service.id, service.name) for service in services]
    
    service_form = ServiceForm()

    return render_template('secondary_admin_dashboard.html',
                           users=users,
                           user_form=user_form,
                           service_form=service_form,
                           assign_service_form=assign_service_form,
                           services=services,
                           groups=groups,
                           group_users_ids=group_users_ids)