# app/main_admin/routes.py
import os
from flask import render_template, url_for, flash, redirect, request, g, jsonify, current_app
from flask_login import login_required, current_user

import psutil  
from datetime import datetime, timedelta
import random  

from ..models.models_app import Admin  # Импорт модели администратора из главной базы данных
from ..models.secondary_admin import User, Service, Ticket, ServiceAssignment  # Импорт моделей из базы данных организации
from ..forms import UserForm, ServiceForm, AssignServiceForm, AdminUserForm, DisplaySettingsForm, SecondaryAdminForm, UserStyleSettingsForm
from .. import db
from ..db_manager import get_db_session, get_current_db
from . import main_admin
from sqlalchemy import func, inspect, text
from ..models.secondary_admin import TicketStatistics


@main_admin.route('/dashboard')
@login_required
def dashboard():
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        flash('Доступ разрешен только для главного администратора', 'danger')
        return redirect(url_for('main.home'))

    # Получаем список всех администраторов организаций
    secondary_admins = Admin.query.filter_by(role='secondary_admin').all()
    
    # Создаем экземпляр формы для создания нового администратора организации
    form = SecondaryAdminForm()
    
    # Создаем экземпляры других форм
    from ..forms import UserForm, ServiceForm, AssignServiceForm
    user_form = UserForm()
    service_form = ServiceForm()
    assign_service_form = AssignServiceForm()
    
    # Инициализируем пустые списки
    users = []
    services = []
    groups = []
    group_users_ids = []
    
    # Здесь должна быть логика для получения данных из базы
    try:
        # Получаем сессию базы данных
        org_db = get_current_db()
        if org_db:
            # Получаем список пользователей
            users = org_db.query(User).all()
            # Получаем список услуг
            services = org_db.query(Service).all()
            
            # Заполняем choices для формы назначения услуги
            assign_service_form.user_id.choices = [(user.id, user.username) for user in users]
            assign_service_form.service_id.choices = [(service.id, service.name) for service in services]
            
            # Загружаем группы пользователей
            try:
                from .groups import load_groups
                groups, group_users_ids = load_groups()
            except ImportError:
                # Если модуль groups не найден, используем пустые списки
                groups = []
                group_users_ids = []
    except Exception as e:
        import traceback
        traceback.print_exc()  # Это поможет увидеть полный стек ошибки в консоли
        flash(f'Ошибка при загрузке данных: {str(e)}', 'danger')
    
    return render_template('dashboard.html',
                          users=users,
                          user_form=user_form,
                          service_form=service_form,
                          assign_service_form=assign_service_form,
                          services=services,
                          groups=groups,
                          group_users_ids=group_users_ids,
                          secondary_admins=secondary_admins,
                          form=form)  # Добавляем форму в контекст
    
# Пример обновления маршрута создания организации
@main_admin.route('/create_secondary_admin', methods=['POST'])
@login_required
def create_secondary_admin():
    if not current_user.is_main_admin:
        flash('Доступ запрещен.', 'danger')
        return redirect(url_for('main.index'))
    
    form = SecondaryAdminForm()
    if form.validate_on_submit():
        # Получаем данные из формы
        organization_name = form.organization_name.data
        username = form.username.data
        password = form.password.data
        organization_address = form.organization_address.data
        additional_info = form.additional_info.data
        access_expiry_date = form.access_expiry_date.data
        
        # Получаем лимит дискового пространства (может прийти как в ГБ, так и в байтах)
        if 'disk_space_limit_bytes' in request.form:
            # Если передано в байтах через скрытое поле
            disk_space_limit = int(request.form['disk_space_limit_bytes'])
        elif 'disk_space_limit' in request.form:
            # Если передано в ГБ через обычное поле
            disk_space_gb = int(request.form['disk_space_limit'])
            disk_space_limit = disk_space_gb * 1024 * 1024 * 1024
        else:
            # Значение по умолчанию - 1 ГБ
            disk_space_limit = 1 * 1024 * 1024 * 1024
        
        # Создаем уникальное имя базы данных
        database_name = generate_unique_database_name(organization_name)
        
        # Создаем нового администратора организации
        new_admin = Admin(
            username=username,
            organization_name=organization_name,
            role='secondary_admin',
            organization_address=organization_address,
            additional_info=additional_info,
            access_expiry_date=access_expiry_date,
            database_name=database_name,
            disk_space_limit=disk_space_limit  # Добавляем новое поле
        )
        new_admin.set_password(password)
        
        # Добавляем в базу данных
        db.session.add(new_admin)
        db.session.commit()
        
        # Создаем базу данных организации
        create_secondary_admin_database(database_name)
        
        flash(f'Организация "{organization_name}" успешно создана!', 'success')
        return redirect(url_for('main_admin.dashboard'))
    
    # Если форма не прошла валидацию, показываем ошибки
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('main_admin.dashboard'))

@main_admin.route('/view_secondary_admin/<int:admin_id>')
@login_required
def view_secondary_admin(admin_id):
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        flash('Доступ разрешен только для главного администратора', 'danger')
        return redirect(url_for('main.home'))
    
    # Получаем информацию об администраторе организации
    admin = Admin.query.get_or_404(admin_id)
    if admin.role != 'secondary_admin':
        flash('Указанный пользователь не является администратором организации', 'danger')
        return redirect(url_for('main_admin.admin_dashboard'))
    
    # Получаем сессию для работы с БД организации
    org_db = get_db_session(admin.id)
    if not org_db:
        flash('Не удалось подключиться к базе данных организации', 'danger')
        return redirect(url_for('main_admin.admin_dashboard'))
    
    # Получаем статистику по организации
    users_count = org_db.query(User).count()
    services_count = org_db.query(Service).count()
    tickets_count = org_db.query(Ticket).count()
    
    return render_template('main_admin/view_secondary_admin.html',
                          admin=admin,
                          users_count=users_count,
                          services_count=services_count,
                          tickets_count=tickets_count)

    
@main_admin.route('/api/toggle_secondary_admin/<int:admin_id>', methods=['POST'])
@login_required
def api_toggle_secondary_admin(admin_id):
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        print(f"TOGGLE DEBUG: Доступ запрещен. current_user: {current_user}, is_main_admin: {getattr(current_user, 'is_main_admin', False)}")
        return jsonify({"error": "Доступ разрешен только для главного администратора"}), 403
    
    print(f"TOGGLE DEBUG: admin_id={admin_id}, тип: {type(admin_id)}")
    
    # Получаем информацию об администраторе организации
    admin = Admin.query.get_or_404(admin_id)
    
    print(f"TOGGLE DEBUG: admin found: {admin}, role: {admin.role}")
    
    if admin.role != 'secondary_admin':
        print(f"TOGGLE DEBUG: Неправильная роль: {admin.role}")
        return jsonify({"error": "Указанный пользователь не является администратором организации"}), 400
    
    # Изменяем статус активности
    old_status = admin.active
    admin.active = not admin.active
    db.session.commit()
    
    status = 'активирован' if admin.active else 'деактивирован'
    
    print(f"TOGGLE DEBUG: Статус изменен с {old_status} на {admin.active}")
    
    return jsonify({
        "success": True,
        "active": admin.active,
        "message": f'Администратор организации "{admin.organization_name}" успешно {status}!'
    })

@main_admin.route('/statistics')
@login_required
def statistics():
    """
    Заглушка для страницы статистики администратора
    """
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        flash('Доступ разрешен только для главного администратора', 'danger')
        return redirect(url_for('main.home'))
    
    # Здесь в будущем будет логика получения статистических данных
    # Пока просто создаем демонстрационные данные
    
    stats_data = {
        "total_organizations": 15,
        "active_organizations": 12,
        "inactive_organizations": 3,
        "total_users": 150,
        "total_services": 45,
        "total_tickets": 1250,
        "tickets_per_day": [
            {"date": "2025-06-01", "count": 120},
            {"date": "2025-06-02", "count": 145},
            {"date": "2025-06-03", "count": 135},
            {"date": "2025-06-04", "count": 160},
            {"date": "2025-06-05", "count": 175},
            {"date": "2025-06-06", "count": 165},
            {"date": "2025-06-07", "count": 140},
        ],
        "services_distribution": [
            {"name": "Консультации", "tickets": 450},
            {"name": "Регистрация документов", "tickets": 325},
            {"name": "Финансовые операции", "tickets": 275},
            {"name": "Техническая поддержка", "tickets": 200},
        ]
    }
    
    return render_template('main_admin_statistics.html', 
                           title='Статистика системы',
                           stats=stats_data)


@main_admin.route('/api/organization/<int:admin_id>', methods=['GET', 'POST'])
@login_required
def api_organization(admin_id):
    if not current_user.is_main_admin:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    admin = Admin.query.get_or_404(admin_id)
    
    if request.method == 'GET':
        # Получаем информацию об администраторе организации
        if admin.role != 'secondary_admin':
            return jsonify({"error": "Указанный пользователь не является администратором организации"}), 400
        
        # Формируем базовые данные об организации
        admin_data = {
            'id': admin.id,
            'username': admin.username,
            'organization_name': admin.organization_name,
            'organization_address': admin.organization_address,
            'additional_info': admin.additional_info,
            'created_at': admin.created_at.isoformat() if admin.created_at else None,
            'access_expiry_date': admin.access_expiry_date.isoformat() if admin.access_expiry_date else None,
            'active': admin.active,
            'database_name': admin.database_name,
            'disk_space_limit': admin.disk_space_limit
        }
        
        # Получаем сессию для работы с БД организации
        org_db = get_db_session(admin.id)
        if not org_db:
            return jsonify({
                "organization": admin_data,
                "users": [],
                "services": [],
                "statistics": {
                    "tickets_today": 0,
                    "tickets_week": 0,
                    "tickets_month": 0, 
                    "total_tickets": 0,
                    "tickets_per_day": []
                }
            })
        
        # Формируем данные для ответа
        try:
            # Проверяем наличие колонки style_type в таблице users
            inspector = inspect(org_db.get_bind())
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            # Если колонки style_type нет, добавляем её
            if 'style_type' not in columns:
                try:
                    print(f"Adding missing column 'style_type' to table 'users'")
                    org_db.execute(text("ALTER TABLE users ADD COLUMN style_type VARCHAR(50) DEFAULT 'default'"))
                    org_db.commit()
                    print(f"Successfully added column 'style_type' to table 'users'")
                except Exception as e:
                    print(f"Error adding column 'style_type' to table 'users': {e}")
                    # Продолжаем без добавления колонки
            
            # Получаем список пользователей
            users = org_db.query(User).all()
            users_data = [
                {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "cabinet": user.cabinet,
                    "style_type": getattr(user, 'style_type', 'default')
                }
                for user in users
            ]
            
            # Получаем список услуг
            services = org_db.query(Service).all()
            services_data = [
                {
                    "id": service.id,
                    "name": service.name,
                    "start_number": service.start_number,
                    "end_number": service.end_number,
                    "cabinet": service.cabinet
                }
                for service in services
            ]
            
            # Получаем актуальную статистику из таблицы TicketStatistics
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)
            
            # Запрос для получения статистики за сегодня
            tickets_today_count = org_db.query(TicketStatistics).filter(
                TicketStatistics.date == today
            ).count()
            
            # Запрос для получения статистики за неделю
            tickets_week_count = org_db.query(TicketStatistics).filter(
                TicketStatistics.date >= week_ago
            ).count()
            
            # Запрос для получения статистики за месяц
            tickets_month_count = org_db.query(TicketStatistics).filter(
                TicketStatistics.date >= month_ago
            ).count()
            
            # Запрос для получения общего количества талонов
            tickets_total_count = org_db.query(TicketStatistics).count()
            
            # Получаем статистику за последние 30 дней для графика
            tickets_per_day_query = org_db.query(
                TicketStatistics.date, 
                func.count(TicketStatistics.id).label('count')
            ).filter(
                TicketStatistics.date >= month_ago
            ).group_by(
                TicketStatistics.date
            ).order_by(
                TicketStatistics.date
            ).all()
            
            tickets_per_day = [
                {
                    "date": day.date.strftime("%Y-%m-%d"),
                    "count": day.count
                } 
                for day in tickets_per_day_query
            ]
            
            # Формируем ответ
            response = {
                "organization": admin_data,
                "users": users_data,
                "services": services_data,
                "statistics": {
                    "tickets_today": tickets_today_count,
                    "tickets_week": tickets_week_count,
                    "tickets_month": tickets_month_count,
                    "total_tickets": tickets_total_count,
                    "tickets_per_day": tickets_per_day
                }
            }
            
            return jsonify(response)
        except Exception as e:
            import traceback
            print(f"Ошибка при получении данных организации: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "organization": admin_data,
                "users": [],
                "services": [],
                "statistics": {
                    "tickets_today": 0,
                    "tickets_week": 0,
                    "tickets_month": 0,
                    "total_tickets": 0,
                    "tickets_per_day": []
                },
                "error_info": str(e)
            })
        
    elif request.method == 'POST':
        # Проверяем, является ли администратор организации
        if admin.role != 'secondary_admin':
            return jsonify({"error": "Указанный пользователь не является администратором организации"}), 400
        
        try:
            # Получаем данные из формы
            organization_name = request.form.get('organization_name')
            username = request.form.get('username')
            organization_address = request.form.get('organization_address')
            additional_info = request.form.get('additional_info')
            
            # Обработка даты окончания доступа
            access_expiry_date_str = request.form.get('access_expiry_date')
            if access_expiry_date_str and access_expiry_date_str.strip():
                try:
                    access_expiry_date = datetime.strptime(access_expiry_date_str, '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({"error": "Неверный формат даты окончания доступа"}), 400
            else:
                access_expiry_date = None
            
            # Обработка пароля
            password = request.form.get('password')
            
            # Обработка лимита дискового пространства
            disk_space_limit = request.form.get('disk_space_limit')
            if disk_space_limit:
                try:
                    disk_space_limit = int(disk_space_limit)
                except ValueError:
                    return jsonify({"error": "Неверный формат лимита дискового пространства"}), 400
            else:
                disk_space_limit = admin.disk_space_limit  # Сохраняем текущее значение
            
            # Обновляем данные администратора
            admin.organization_name = organization_name
            admin.username = username
            admin.organization_address = organization_address
            admin.additional_info = additional_info
            admin.access_expiry_date = access_expiry_date
            admin.disk_space_limit = disk_space_limit
            
            # Если указан новый пароль, обновляем его
            if password and password.strip():
                admin.set_password(password)
            
            # Сохраняем изменения в базе данных
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Информация об организации успешно обновлена"
            })
        
        except Exception as e:
            # Отменяем транзакцию в случае ошибки
            db.session.rollback()
            
            import traceback
            print(f"Ошибка при обновлении данных организации: {str(e)}")
            print(traceback.format_exc())
            
            return jsonify({
                "success": False,
                "error": f"Ошибка при обновлении: {str(e)}"
            }), 500

@main_admin.route('/api/system_info', methods=['GET'])
@login_required
def api_get_system_info():
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    try:
        # Подсчет общего количества пользователей и услуг
        total_users = 0
        total_services = 0
        
        # Получаем всех администраторов организаций
        secondary_admins = Admin.query.filter_by(role='secondary_admin').all()
        
        for admin in secondary_admins:
            org_db = get_db_session(admin.id)
            if org_db:
                try:
                    # Проверяем наличие колонки style_type в таблице users
                    inspector = inspect(org_db.get_bind())
                    columns = [col['name'] for col in inspector.get_columns('users')]
                    
                    # Если колонки style_type нет, используем raw SQL запрос без этой колонки
                    if 'style_type' not in columns:
                        # Выполняем прямой SQL-запрос для подсчета пользователей
                        user_count_result = org_db.execute(text("SELECT COUNT(*) FROM users")).scalar()
                        total_users += user_count_result
                    else:
                        # Используем ORM-запрос, если колонка существует
                        total_users += org_db.query(User).count()
                    
                    # Подсчет услуг (не зависит от колонки style_type)
                    total_services += org_db.query(Service).count()
                except Exception as e:
                    print(f"Error counting users/services for admin {admin.username}: {e}")
                    # Продолжаем со следующим администратором
        
        # Пытаемся получить системную информацию с psutil, если доступно
        try:
            import psutil
            disk = psutil.disk_usage('/')
            disk_space = f"{disk.used // (1024 ** 3)} ГБ из {disk.total // (1024 ** 3)} ГБ ({disk.percent}%)"
            cpu_load = f"{psutil.cpu_percent()}%"
            memory = psutil.virtual_memory()
            ram_usage = f"{memory.used // (1024 ** 3)} ГБ из {memory.total // (1024 ** 3)} ГБ ({memory.percent}%)"
        except (ImportError, Exception):
            # Если psutil не доступен, возвращаем заглушки
            disk_space = "Нет данных"
            cpu_load = "Нет данных"
            ram_usage = "Нет данных"
        
        # Генерируем демо-данные для последних действий
        # В реальном приложении здесь будет запрос к базе данных
        recent_activities = [
            {
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "description": "Создана организация \"ООО Пример\"",
                "type": "create",
                "type_text": "Создание"
            },
            {
                "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
                "description": "Изменен пароль \"МедЦентр\"",
                "type": "update",
                "type_text": "Изменение"
            },
            {
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "description": "Деактивирована \"Старая Орг\"",
                "type": "delete",
                "type_text": "Деактивация"
            }
        ]
        
        # Формируем ответ
        response = {
            "total_users": total_users,
            "total_services": total_services,
            "disk_space": disk_space,
            "cpu_load": cpu_load,
            "ram_usage": ram_usage,
            "recent_activities": recent_activities
        }
        
        return jsonify(response)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# API-эндпоинт для сброса пароля администратора
@main_admin.route('/api/reset_password/<int:admin_id>', methods=['POST'])
@login_required
def api_reset_password(admin_id):
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    # Получаем информацию об администраторе организации
    admin = Admin.query.get_or_404(admin_id)
    if admin.role != 'secondary_admin':
        return jsonify({"error": "Указанный пользователь не является администратором организации"}), 400
    
    # Получаем новый пароль из запроса
    data = request.get_json()
    new_password = data.get('new_password')
    
    if not new_password:
        return jsonify({"error": "Не указан новый пароль"}), 400
    
    # Устанавливаем новый пароль
    admin.set_password(new_password)
    db.session.commit()
    
    return jsonify({"message": "Пароль успешно сброшен"})


def get_admin_style_folder(admin_username):
    """
    Получает или создает папку для стилей администратора организации.
    
    Args:
        admin_username (str): Имя пользователя администратора организации
        
    Returns:
        tuple: (folder_path, exists) - путь к папке и флаг существования папки
    """
    # Определяем путь к папке со стилями
    css_folder = os.path.join(current_app.static_folder, 'css')
    if not os.path.exists(css_folder):
        os.makedirs(css_folder)
        print(f"Created CSS folder: {css_folder}")
    
    # Определяем путь к папке со стилями организации
    org_css_folder = os.path.join(css_folder, admin_username)
    folder_exists = os.path.exists(org_css_folder)
    
    return org_css_folder, folder_exists

def create_style_folder(admin_username):
    """
    Создает папку для стилей администратора организации, если она не существует.
    
    Args:
        admin_username (str): Имя пользователя администратора организации
        
    Returns:
        tuple: (success, message) - успешность операции и сообщение
    """
    folder_path, exists = get_admin_style_folder(admin_username)
    
    if exists:
        return True, f"Папка для стилей {admin_username} уже существует"
    
    try:
        os.makedirs(folder_path)
        print(f"Created style folder for {admin_username}: {folder_path}")
        return True, f"Папка для стилей {admin_username} успешно создана"
    except Exception as e:
        print(f"Error creating style folder for {admin_username}: {e}")
        return False, f"Ошибка при создании папки для стилей: {str(e)}"

def list_style_files(admin_username):
    """
    Возвращает список файлов стилей в папке администратора организации.
    
    Args:
        admin_username (str): Имя пользователя администратора организации
        
    Returns:
        list: Список файлов стилей
    """
    folder_path, exists = get_admin_style_folder(admin_username)
    
    if not exists:
        return []
    
    try:
        files = [f for f in os.listdir(folder_path) if f.endswith('.css')]
        return files
    except Exception as e:
        print(f"Error listing style files for {admin_username}: {e}")
        return []

def check_style_files(admin_username, roles_with_custom_style):
    """
    Проверяет наличие файлов стилей для указанных ролей.
    
    Args:
        admin_username (str): Имя пользователя администратора организации
        roles_with_custom_style (list): Список ролей с кастомными стилями
        
    Returns:
        tuple: (success, missing_files) - успешность проверки и список отсутствующих файлов
    """
    folder_path, exists = get_admin_style_folder(admin_username)
    
    if not exists:
        return False, []
    
    missing_files = []
    
    for role in roles_with_custom_style:
        file_name = f"{role}.css"
        file_path = os.path.join(folder_path, file_name)
        
        if not os.path.exists(file_path):
            missing_files.append(file_name)
    
    if missing_files:
        return False, missing_files
    
    return True, []

def update_user_style_settings(org_db, role, style_type):
    """
    Обновляет настройки стилей для пользователей указанной роли.
    
    Args:
        org_db: Сессия SQLAlchemy для базы данных организации
        role (str): Роль пользователей ('admin', 'user', 'tablo', 'terminal')
        style_type (str): Тип стиля ('default' или 'custom')
        
    Returns:
        int: Количество обновленных пользователей
    """
    try:
        # Проверяем наличие поля style_type в таблице users
        inspector = inspect(org_db.get_bind())
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'style_type' not in columns:
            # Если поле отсутствует, добавляем его
            print(f"Adding missing column 'style_type' to table 'users'")
            org_db.execute(text("ALTER TABLE users ADD COLUMN style_type VARCHAR(50) DEFAULT 'default'"))
            org_db.commit()
            print(f"Successfully added column 'style_type' to table 'users'")
        
        # Получаем всех пользователей с указанной ролью
        users = org_db.query(User).filter_by(role=role).all()
        
        # Обновляем настройки стиля
        count = 0
        for user in users:
            user.style_type = style_type
            count += 1
        
        # Сохраняем изменения
        org_db.commit()
        print(f"Updated style_type to {style_type} for {count} users with role {role}")
        
        return count
    except Exception as e:
        org_db.rollback()
        print(f"Error updating style settings: {e}")
        return 0
    
# Добавьте эти маршруты в файл main_admin/routes.py

@main_admin.route('/style_settings/<int:org_admin_id>', methods=['GET'])
@login_required
def style_settings(org_admin_id):
    """Отображает информацию о настройках стилей для организации в формате JSON"""
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    # Получаем информацию об администраторе организации
    org_admin = Admin.query.get_or_404(org_admin_id)
    if org_admin.role != 'secondary_admin':
        return jsonify({"error": "Указанный пользователь не является администратором организации"}), 400
    
    # Получаем сессию для работы с БД организации
    org_db = get_db_session(org_admin.id)
    if not org_db:
        return jsonify({"error": "Не удалось подключиться к базе данных организации"}), 500
    
    # Получаем список текущих файлов стилей
    style_files = list_style_files(org_admin.username)
    
    # Проверяем наличие поля style_type в таблице users
    try:
        inspector = inspect(org_db.get_bind())
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'style_type' not in columns:
            # Если поле отсутствует, добавляем его
            print(f"Adding missing column 'style_type' to table 'users'")
            org_db.execute(text("ALTER TABLE users ADD COLUMN style_type VARCHAR(50) DEFAULT 'default'"))
            org_db.commit()
            print(f"Successfully added column 'style_type' to table 'users'")
    except Exception as e:
        print(f"Error checking or adding style_type column: {e}")
        # Продолжаем работу, даже если произошла ошибка
    
    # Определяем роли с кастомными стилями по текущим настройкам
    custom_roles = {
        'admin': 'default',
        'user': 'default',
        'tablo': 'default',
        'terminal': 'default'
    }
    
    try:
        # Проверяем, есть ли пользователи с каждой ролью и какой у них стиль
        for role in custom_roles.keys():
            # Пытаемся найти пользователей с этой ролью
            users = org_db.query(User).filter_by(role=role).all()
            
            if users:
                # Если есть пользователи, проверяем их стили
                style_types = set(getattr(user, 'style_type', 'default') for user in users)
                
                # Если все пользователи имеют один и тот же стиль, используем его
                if len(style_types) == 1:
                    custom_roles[role] = next(iter(style_types)) or 'default'
                else:
                    # В противном случае, используем наиболее распространенный стиль
                    style_counts = {}
                    for style in style_types:
                        style = style or 'default'
                        style_counts[style] = style_counts.get(style, 0) + 1
                    
                    custom_roles[role] = max(style_counts.items(), key=lambda x: x[1])[0]
    except Exception as e:
        print(f"Error determining custom roles: {e}")
        # Продолжаем работу с настройками по умолчанию
    
    # Проверяем наличие необходимых файлов стилей
    roles_with_custom_style = [role for role, style_type in custom_roles.items() if style_type == 'custom']
    _, missing_files = check_style_files(org_admin.username, roles_with_custom_style)
    
    # Формируем ответ
    response = {
        "org_admin": {
            "id": org_admin.id,
            "username": org_admin.username,
            "organization_name": org_admin.organization_name
        },
        "style_settings": custom_roles,
        "style_files": style_files,
        "missing_files": missing_files
    }
    
    return jsonify(response)

@main_admin.route('/update_org_styles/<int:org_admin_id>', methods=['POST'])
@login_required
def update_org_styles(org_admin_id):
    """Обновляет настройки стилей для организации"""
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    # Получаем информацию об администраторе организации
    org_admin = Admin.query.get_or_404(org_admin_id)
    if org_admin.role != 'secondary_admin':
        return jsonify({"error": "Указанный пользователь не является администратором организации"}), 400
    
    # Получаем сессию для работы с БД организации
    org_db = get_db_session(org_admin.id)
    if not org_db:
        return jsonify({"error": "Не удалось подключиться к базе данных организации"}), 500
    
    # Получаем данные запроса
    admin_style = request.form.get('admin_style', 'default')
    user_style = request.form.get('user_style', 'default')
    tablo_style = request.form.get('tablo_style', 'default')
    terminal_style = request.form.get('terminal_style', 'default')
    
    # Создаем список ролей с кастомными стилями
    roles_with_custom_style = []
    if admin_style == 'custom':
        roles_with_custom_style.append('admin')
    if user_style == 'custom':
        roles_with_custom_style.append('user')
    if tablo_style == 'custom':
        roles_with_custom_style.append('tablo')
    if terminal_style == 'custom':
        roles_with_custom_style.append('terminal')
    
    # Проверяем наличие необходимых файлов стилей
    success, missing_files = check_style_files(org_admin.username, roles_with_custom_style)
    
    if not success and roles_with_custom_style:
        # Если выбраны кастомные стили, но файлы отсутствуют
        missing_files_str = ', '.join(missing_files)
        return jsonify({
            "success": False,
            "error": f"Отсутствуют необходимые файлы стилей: {missing_files_str}. Создайте их и повторите попытку."
        }), 400
    
    # Создаем папку для стилей, если она не существует
    if roles_with_custom_style:
        create_style_folder(org_admin.username)
    
    # Обновляем настройки стилей для всех пользователей
    update_count = 0
    update_count += update_user_style_settings(org_db, 'admin', admin_style)
    update_count += update_user_style_settings(org_db, 'user', user_style)
    update_count += update_user_style_settings(org_db, 'tablo', tablo_style)
    update_count += update_user_style_settings(org_db, 'terminal', terminal_style)
    
    return jsonify({
        "success": True,
        "message": f"Настройки стилей успешно обновлены для {update_count} пользователей"
    })

@main_admin.route('/check_style_files/<int:org_admin_id>', methods=['POST'])
@login_required
def check_style_files_route(org_admin_id):
    """API-эндпоинт для проверки наличия файлов стилей"""
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    # Получаем информацию об администраторе организации
    org_admin = Admin.query.get_or_404(org_admin_id)
    
    # Получаем список ролей с кастомными стилями из запроса
    data = request.get_json() or {}
    roles = data.get('roles', [])
    
    # Проверяем наличие файлов стилей
    success, missing_files = check_style_files(org_admin.username, roles)
    
    return jsonify({
        "success": success,
        "missing_files": missing_files
    })

@main_admin.route('/create_style_folder/<int:org_admin_id>', methods=['POST'])
@login_required
def create_style_folder_route(org_admin_id):
    """API-эндпоинт для создания папки для стилей"""
    # Проверяем, является ли пользователь главным администратором
    if not hasattr(current_user, 'is_main_admin') or not current_user.is_main_admin:
        return jsonify({"error": "Доступ запрещен"}), 403
    
    # Получаем информацию об администраторе организации
    org_admin = Admin.query.get_or_404(org_admin_id)
    
    # Создаем папку для стилей
    success, message = create_style_folder(org_admin.username)
    
    return jsonify({
        "success": success,
        "message": message
    })