import os
from flask import g, current_app, session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import logging

logger = logging.getLogger(__name__)

_engines = {}
_sessions = {}

def get_engine(db_name):
    """Получает или создает движок SQLAlchemy для указанной базы данных."""
    if db_name not in _engines:
        db_path = os.path.join(current_app.config['DB_FOLDER'], f"{db_name}.db")
        _engines[db_name] = create_engine(f"sqlite:///{db_path}")
        logger.info(f"Created engine for database: {db_name}")
    return _engines[db_name]

def get_db_session(admin_id):
    """Возвращает сессию SQLAlchemy для базы данных администратора."""
    from app.models.models_app import Admin
    admin = Admin.query.get(admin_id)
    if not admin:
        logger.warning(f"Admin with ID {admin_id} not found")
        return None
    if not admin.is_active:
        logger.warning(f"Admin {admin.username} (ID: {admin_id}) is inactive")
        return None
    db_name = admin.database_name
    if db_name not in _sessions:
        engine = get_engine(db_name)
        _sessions[db_name] = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        logger.info(f"Created session for database: {db_name}")
    return _sessions[db_name]

def get_db_session_by_username(username):
    """Возвращает сессию SQLAlchemy для базы данных администратора по имени пользователя."""
    from app.models.models_app import Admin
    admin = Admin.query.filter_by(username=username).first()
    if not admin:
        logger.warning(f"Admin with username {username} not found")
        return None
    return get_db_session(admin.id)

def get_org_db_from_user_login(username):
    """
    Возвращает сессию SQLAlchemy для базы данных организации,
    основываясь на логине пользователя формата "логин_админа@имя_пользователя".
    
    Args:
        username (str): Логин в формате "логин_админа@имя_пользователя"
        
    Returns:
        tuple: (org_db_session, username_without_prefix) или (None, None) если не удалось найти БД
    """
    if '@' not in username:
        return None, None
        
    admin_username, user_username = username.split('@', 1)
    
    # Находим администратора организации
    from app.models.models_app import Admin
    admin = Admin.query.filter_by(username=admin_username).first()
    
    if not admin or not admin.is_active:
        return None, None
        
    # Получаем сессию для работы с БД организации
    org_db = get_db_session(admin.id)
    
    if not org_db:
        return None, None
        
    return org_db, user_username

def get_current_db():
    """Возвращает сессию SQLAlchemy для текущего администратора или из сессии."""
    from flask_login import current_user
    
    # Если уже есть БД в g, возвращаем её
    if hasattr(g, 'org_db') and g.org_db is not None:
        return g.org_db
        
    # Пробуем получить ID администратора из сессии
    if 'org_admin_id' in session and current_user.is_authenticated:
        g.org_db = get_db_session(session['org_admin_id'])
        if g.org_db:
            logger.info(f"Using database from session org_admin_id: {session['org_admin_id']}")
            return g.org_db
    
    # Если текущий пользователь - администратор организации, используем его БД
    if current_user.is_authenticated and hasattr(current_user, 'is_secondary_admin') and current_user.is_secondary_admin:
        g.org_db = get_db_session(current_user.id)
        logger.info(f"Using database of admin {current_user.username} (ID: {current_user.id})")
        return g.org_db
    
    # В противном случае, БД не найдена
    g.org_db = None
    return None

def close_all_sessions():
    """Закрывает все сессии SQLAlchemy"""
    for db_name, session in _sessions.items():
        session.remove()
        logger.debug(f"Closed session for database: {db_name}")