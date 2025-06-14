# app/__init__.py
from flask import Flask, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler
import logging
from flask_jwt_extended import JWTManager
import os

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
socketio = SocketIO(async_mode='eventlet')
migrate = Migrate()
scheduler = BackgroundScheduler()
jwt = JWTManager()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# app/__init__.py
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config.get('DB_FOLDER', 'org_databases'), exist_ok=True)

    app.config['JWT_SECRET_KEY'] = 'your_real_secret_key'

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    csrf.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app)

    def reset_tickets_daily():
        pass

    scheduler.add_job(func=reset_tickets_daily, trigger='cron', hour=0, minute=1)
    scheduler.start()

    # Импорт blueprints
    from app.main import main as main_blueprint
    from app.main_admin import main_admin as main_admin_blueprint
    from app.secondary_admin import secondary_admin as secondary_admin_blueprint
    from app.user import user as user_blueprint
    from app.terminal import terminal as terminal_blueprint
    from app.tablo import tablo as tablo_blueprint

    # Настройка middleware для blueprints ПЕРЕД их регистрацией
    from app.middleware import setup_db_middleware
    
    # Регистрация blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(main_admin_blueprint, url_prefix='/main_admin')
    app.register_blueprint(secondary_admin_blueprint, url_prefix='/secondary_admin')
    app.register_blueprint(user_blueprint, url_prefix='/user')
    app.register_blueprint(terminal_blueprint, url_prefix='/terminal')
    app.register_blueprint(tablo_blueprint, url_prefix='/tablo')

    # Регистрация обработчиков событий для озвучивания тикетов
    from app.voicing_tickets import register_voicing_tickets_events
    register_voicing_tickets_events(socketio)

    CORS(app, resources={
        r"/messenger/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Requested-With", "X-CSRFToken"],
            "supports_credentials": True
        }
    })

    @login_manager.user_loader
    def load_user(user_id):
        """
        Новая функция загрузки пользователей, поддерживающая как администраторов,
        так и пользователей организаций
        """
        from app.models.models_app import Admin
        print(f"Flask-Login: Loading user with ID: {user_id}")
        
        try:
            # Используем новый метод из модели Admin
            user = Admin.load_user_by_id(user_id)
            if user:
                print(f"Flask-Login: Successfully loaded user: {user.username} (Type: {'org_user' if getattr(user, 'is_org_user', False) else 'admin'})")
            else:
                print(f"Flask-Login: User not found for ID: {user_id}")
            return user
        except Exception as e:
            print(f"Flask-Login: Error loading user {user_id}: {e}")
            return None

    @app.teardown_appcontext
    def teardown_db(exception=None):
        from app.db_manager import close_all_sessions
        close_all_sessions()

    @app.before_request
    def before_request():
        from flask_login import current_user
        from app.db_manager import get_db_session
        from flask import session
        import os
        
        print(f"Global middleware: Processing request")
        
        # Сбрасываем БД организации по умолчанию
        g.org_db = None
        g.css_path = 'css'  # По умолчанию используем стандартные стили
        
        # Если пользователь аутентифицирован
        if current_user.is_authenticated:
            print(f"Global middleware: User authenticated: {current_user.username}")
            print(f"Global middleware: is_org_user={getattr(current_user, 'is_org_user', False)}")
            print(f"Global middleware: is_secondary_admin={getattr(current_user, 'is_secondary_admin', False)}")
            
            # Определяем путь к CSS в зависимости от настроек стиля
            style_type = getattr(current_user, 'style_type', 'default')
            if style_type == 'custom' and hasattr(current_user, 'org_username'):
                # Проверяем наличие файла стиля для конкретной роли пользователя
                org_css_path = f"css/{current_user.org_username}"
                role_css_file = f"{current_user.role}.css"
                full_path = os.path.join(app.static_folder, org_css_path, role_css_file)
                
                if os.path.exists(full_path):
                    g.css_path = org_css_path
                    print(f"Global middleware: Using custom CSS path: {g.css_path}")
                else:
                    # Если файл не найден, используем стандартный стиль
                    g.css_path = 'css'
                    print(f"Global middleware: Custom CSS file not found, using default")
            else:
                g.css_path = 'css'
                print(f"Global middleware: Using default CSS path")
            
            # Проверяем, является ли пользователь пользователем организации
            if getattr(current_user, 'is_org_user', False):
                # Получаем ID администратора организации
                admin_id = getattr(current_user, 'organization_id', None)
                if admin_id:
                    print(f"Global middleware: Setting org_db for org user, admin_id: {admin_id}")
                    g.org_db = get_db_session(admin_id)
                    # Убеждаемся, что сессия содержит корректные данные
                    if 'org_admin_id' not in session:
                        session['org_admin_id'] = admin_id
                        session['is_org_user'] = True
                elif 'org_admin_id' in session:
                    # Резервный вариант - берем из сессии
                    admin_id = session['org_admin_id']
                    print(f"Global middleware: Using admin_id from session: {admin_id}")
                    g.org_db = get_db_session(admin_id)
            
            # Проверяем, является ли пользователь администратором организации
            elif getattr(current_user, 'is_secondary_admin', False):
                print(f"Global middleware: Setting org_db for secondary admin: {current_user.id}")
                # Устанавливаем БД организации как текущую
                g.org_db = get_db_session(current_user.id)
                # Очищаем данные пользователей организации из сессии
                session.pop('org_admin_id', None)
                session.pop('is_org_user', None)
            
            # В противном случае - главный администратор
            else:
                print("Global middleware: User is main admin, clearing org session data")
                g.org_db = None
                # Очищаем данные организации из сессии
                session.pop('org_admin_id', None)
                session.pop('is_org_user', None)
        else:
            print("Global middleware: User not authenticated")
            g.org_db = None

    with app.app_context():
        from app.setup import setup_main_database, setup_db_folders
        setup_db_folders()
        setup_main_database()
        logger.info("Application initialization completed")

    return app, socketio