# app/secondary_admin/__init__.py
from flask import Blueprint, g
from flask_login import current_user
from app.db_manager import get_db_session

secondary_admin = Blueprint('secondary_admin', __name__, template_folder='templates')

# Добавляем middleware для определения текущей БД
@secondary_admin.before_request
def before_request():
    # Если пользователь аутентифицирован и является администратором организации
    if current_user.is_authenticated and hasattr(current_user, 'is_secondary_admin') and current_user.is_secondary_admin:
        # Устанавливаем БД организации как текущую
        g.org_db = get_db_session(current_user.id)
    else:
        g.org_db = None

from . import routes
from . import groups
from . import services
from . import statistics
from . import users
from . import video