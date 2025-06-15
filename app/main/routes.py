# app/main/routes.py
from flask import render_template, jsonify, url_for, flash, redirect, request, g, session
from flask_login import login_user, current_user, logout_user, login_required
from ..forms import LoginForm, UserForm, ServiceForm, AssignServiceForm
from ..models.models_app import Admin  # Изменяем импорт на новую модель
from ..db_manager import get_db_session, get_db_session_by_username, get_current_db
from ..models.secondary_admin import User  # Импорт модели пользователя из базы данных организации
from . import main


@main.route('/benefits')
def benefits():
    """Маршрут для отображения главной страницы продукта Quick Queue"""
    # Создаем экземпляры форм
    user_form = UserForm()
    service_form = ServiceForm()
    assign_service_form = AssignServiceForm()
    
    # Теперь передаем созданные экземпляры в шаблон
    return render_template('benefits.html', 
                           title='Quick Queue - Мультитенантная система электронной очереди', 
                           user_form=user_form, 
                           service_form=service_form, 
                           assign_service_form=assign_service_form)
@main.route('/')
@main.route('/home')
def home():
    # Если пользователь не авторизован, сначала показываем лендинг
    if not current_user.is_authenticated:
        return redirect(url_for('main.benefits'))
    
    print(f"Home route: current_user={current_user}, role={getattr(current_user, 'role', 'N/A')}")
    print(f"is_org_user={getattr(current_user, 'is_org_user', False)}")
    print(f"is_main_admin={getattr(current_user, 'is_main_admin', False)}")
    print(f"is_secondary_admin={getattr(current_user, 'is_secondary_admin', False)}")
    
    # Проверяем роль пользователя в новой структуре
    if hasattr(current_user, 'is_main_admin') and current_user.is_main_admin:
        return redirect(url_for('main_admin.dashboard'))
    elif hasattr(current_user, 'is_secondary_admin') and current_user.is_secondary_admin:
        return redirect(url_for('secondary_admin.dashboard'))
    else:
        # Для пользователей организации (роли: user, terminal, tablo)
        if hasattr(current_user, 'role'):
            if current_user.role == 'user':
                return redirect(url_for('user.user_dashboard'))
            elif current_user.role == 'terminal':
                return redirect(url_for('terminal.terminal_dashboard'))
            elif current_user.role == 'tablo':
                return redirect(url_for('tablo.tablo_dashboard'))
            elif current_user.role == 'admin':
                # Администратор в рамках организации
                return redirect(url_for('secondary_admin.dashboard'))
    
    return render_template('home.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    
    # Отладочный вывод
    print(f"Form submitted: {request.method == 'POST'}")
    if request.method == 'POST':
        print(f"Form data: {request.form}")
        print(f"Form validation: {form.validate()}")
        print(f"Form errors: {form.errors}")
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        print(f"Login attempt: username='{username}', password='{password}'")
        
        # Check if the username contains @ symbol (for organization users)
        if '@' in username:
            admin_username, user_username = username.split('@', 1)
            
            print(f"Organization user login: admin='{admin_username}', user='{user_username}'")
            
            # Find the admin to get the organization database
            admin = Admin.query.filter_by(username=admin_username).first()
            
            if admin and admin.is_active:
                print(f"Found active admin: {admin.username}, database: {admin.database_name}")
                
                # Get the database session for this organization
                org_db = get_db_session(admin.id)
                
                if org_db:
                    # Look for the user in this organization's database
                    from app.models.secondary_admin import User
                    user = org_db.query(User).filter_by(username=user_username).first()
                    
                    print(f"Organization user found: {user is not None}")
                    
                    if user and user.check_password(password):
                        print(f"Password check passed for user: {user.username}")
                        
                        # Create a temporary user object for Flask-Login using the helper method
                        temp_user = Admin.create_org_user_proxy(user, admin.id)
                        
                        # Выполняем вход
                        login_success = login_user(temp_user, remember=True)
                        print(f"Login user result: {login_success}")
                        
                        # Store the database session in g
                        g.org_db = org_db
                        
                        # Store org_db_id in session to retrieve it later
                        session['org_admin_id'] = admin.id
                        session['is_org_user'] = True
                        
                        print(f"Session data set: org_admin_id={admin.id}")
                        
                        flash(f'Успешный вход в систему как пользователь организации {admin.organization_name}', 'success')
                        
                        # Явное перенаправление в зависимости от роли
                        next_page = request.args.get('next')
                        if next_page:
                            return redirect(next_page)
                        
                        # Определяем куда перенаправить в зависимости от роли пользователя
                        if user.role == 'user':
                            return redirect(url_for('user.user_dashboard'))
                        elif user.role == 'terminal':
                            return redirect(url_for('terminal.terminal_dashboard'))
                        elif user.role == 'tablo':
                            return redirect(url_for('tablo.tablo_dashboard'))
                        elif user.role == 'admin':
                            return redirect(url_for('secondary_admin.dashboard'))
                        else:
                            return redirect(url_for('main.home'))
                    else:
                        if user:
                            print(f"Password check failed for user: {user.username}")
                        flash('Неверное имя пользователя или пароль.', 'danger')
                else:
                    print("Could not get organization database session")
                    flash('Не удалось подключиться к базе данных организации.', 'danger')
            else:
                if admin:
                    print(f"Admin found but inactive: {admin.username}, active={admin.active}")
                else:
                    print(f"Admin not found: {admin_username}")
                flash('Администратор организации не найден или неактивен.', 'danger')
        else:
            # Standard login process for admins
            admin = Admin.query.filter_by(username=username).first()
            
            print(f"Admin login: admin found={admin is not None}")
            
            if admin and admin.check_password(password):
                if admin.is_active:
                    login_success = login_user(admin, remember=True)
                    print(f"Admin login success: {login_success}")
                    
                    # Очищаем данные организации из сессии для администраторов
                    session.pop('org_admin_id', None)
                    session.pop('is_org_user', None)
                    
                    if admin.is_main_admin:
                        flash('Успешный вход в систему как главный администратор.', 'success')
                        return redirect(url_for('main_admin.dashboard'))
                    else:
                        flash(f'Успешный вход в систему как администратор организации {admin.organization_name}.', 'success')
                        return redirect(url_for('secondary_admin.dashboard'))
                else:
                    flash('Аккаунт неактивен или срок его действия истек.', 'danger')
            else:
                flash('Неверное имя пользователя или пароль.', 'danger')
    else:
        # Если POST-запрос, но форма не валидна, выводим причины
        if request.method == 'POST':
            print(f"Form validation failed: {form.errors}")
    
    # Get list of active secondary admins for autocomplete
    secondary_admins = Admin.query.filter_by(role='secondary_admin', active=True).all()
    admin_usernames = [admin.username for admin in secondary_admins]
    
    return render_template('login.html', title='Вход в систему', form=form, admin_usernames=admin_usernames)

@main.route('/logout')
def logout():
    # Очищаем информацию о БД организации в сессии
    session.pop('org_admin_id', None)
    session.pop('is_org_user', None)
    
    if hasattr(g, 'org_db'):
        delattr(g, 'org_db')
    
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('main.login'))

@main.route('/check_auth_status')
def check_auth_status():
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'user_type': 'org_user' if getattr(current_user, 'is_org_user', False) else 'admin',
        'role': getattr(current_user, 'role', None),
        'username': getattr(current_user, 'username', None)
    })

@main.before_request
def load_org_db():
    """Загружает БД организации из сессии при каждом запросе для пользователей организаций"""
    print(f"Before request: authenticated={current_user.is_authenticated}")
    if current_user.is_authenticated:
        print(f"Current user: {current_user.username}, is_org_user={getattr(current_user, 'is_org_user', False)}")
        
        if getattr(current_user, 'is_org_user', False) and 'org_admin_id' in session:
            org_admin_id = session['org_admin_id']
            print(f"Loading org_db for admin_id: {org_admin_id}")
            g.org_db = get_db_session(org_admin_id)
            print(f"Loaded org_db: {g.org_db is not None}")
        else:
            g.org_db = None