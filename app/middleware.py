# app/middleware.py
from flask import g, session
from flask_login import current_user
from app.db_manager import get_db_session
import logging
import os
from flask import current_app

logger = logging.getLogger(__name__)

def setup_db_middleware(blueprint):
    """
    Устанавливает middleware для определения текущей БД в blueprint.
    
    Args:
        blueprint: Flask Blueprint, для которого устанавливается middleware
    """
    @blueprint.before_request
    def before_request():
        print(f"Middleware: Processing request for {blueprint.name}")
        
        # Сбрасываем БД организации по умолчанию
        g.org_db = None
        g.css_path = 'css'  # По умолчанию используем стандартные стили
        
        # Если пользователь аутентифицирован
        if current_user.is_authenticated:
            print(f"Middleware: User is authenticated: {current_user.username}")
            print(f"Middleware: User type - is_org_user: {getattr(current_user, 'is_org_user', False)}")
            print(f"Middleware: User type - is_secondary_admin: {getattr(current_user, 'is_secondary_admin', False)}")
            print(f"Middleware: User type - is_main_admin: {getattr(current_user, 'is_main_admin', False)}")
            
            # Определяем путь к CSS в зависимости от настроек стиля
            style_type = getattr(current_user, 'style_type', 'default')
            if style_type == 'custom' and hasattr(current_user, 'org_username'):
                # Проверяем наличие файла стиля для конкретной роли пользователя
                org_css_path = f"css/{current_user.org_username}"
                role_css_file = f"{current_user.role}.css"
                full_path = os.path.join(current_app.static_folder, org_css_path, role_css_file)
                
                if os.path.exists(full_path):
                    g.css_path = org_css_path
                    print(f"Middleware: Using custom CSS path: {g.css_path}")
                else:
                    # Если файл не найден, используем стандартный стиль
                    g.css_path = 'css'
                    print(f"Middleware: Custom CSS file not found, using default")
            else:
                g.css_path = 'css'
                print(f"Middleware: Using default CSS path")
            
            # Проверяем, является ли пользователь пользователем организации
            if getattr(current_user, 'is_org_user', False):
                print(f"Middleware: User is org user, org_id: {getattr(current_user, 'organization_id', None)}")
                # Получаем ID администратора организации из атрибута пользователя
                admin_id = getattr(current_user, 'organization_id', None)
                
                # Если ID администратора есть в атрибутах пользователя или в сессии
                if admin_id or 'org_admin_id' in session:
                    if not admin_id and 'org_admin_id' in session:
                        admin_id = session['org_admin_id']
                        print(f"Middleware: Got admin_id from session: {admin_id}")
                    
                    if admin_id:
                        g.org_db = get_db_session(admin_id)
                        print(f"Middleware: Set g.org_db from org user: {g.org_db is not None}")
                        
                        # Убеждаемся, что сессия содержит корректные данные
                        if 'org_admin_id' not in session:
                            session['org_admin_id'] = admin_id
                            session['is_org_user'] = True
            
            # Проверяем, является ли пользователь администратором организации
            elif getattr(current_user, 'is_secondary_admin', False):
                print(f"Middleware: User is secondary admin: {current_user.id}")
                # Устанавливаем БД организации как текущую
                g.org_db = get_db_session(current_user.id)
                print(f"Middleware: Set g.org_db from secondary admin: {g.org_db is not None}")
                
                # Очищаем данные пользователей организации из сессии
                session.pop('org_admin_id', None)
                session.pop('is_org_user', None)
            
            # В противном случае - главный администратор
            else:
                print("Middleware: User is main admin")
                g.org_db = None
                # Очищаем данные организации из сессии
                session.pop('org_admin_id', None)
                session.pop('is_org_user', None)
        else:
            print("Middleware: User is not authenticated")
            g.org_db = None