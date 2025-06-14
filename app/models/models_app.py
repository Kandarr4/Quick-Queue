from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Admin(UserMixin, db.Model):
    """Модель администратора в главной базе данных."""
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='secondary_admin')
    organization_name = db.Column(db.String(128))
    organization_address = db.Column(db.String(200), nullable=True)
    additional_info = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    access_expiry_date = db.Column(db.DateTime, nullable=True)
    database_name = db.Column(db.String(128), unique=True)
    active = db.Column(db.Boolean, default=True)
    disk_space_limit = db.Column(db.BigInteger, default=1073741824)  # По умолчанию 1 ГБ (в байтах)
    
    # Дополнительные атрибуты для работы с пользователями организаций
    is_org_user = False  # Флаг, указывающий, что это пользователь организации
    organization_id = None  # ID администратора организации для пользователей

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_main_admin(self):
        return self.role == 'main_admin'

    @property
    def is_secondary_admin(self):
        return self.role == 'secondary_admin' and not self.is_org_user

    @property
    def is_active(self):
        if not self.active:
            return False
        if self.access_expiry_date and datetime.utcnow() > self.access_expiry_date:
            return False
        return True
    
    def get_id(self):
        """
        Переопределяем get_id для корректной работы Flask-Login с прокси-объектами
        """
        if self.is_org_user:
            # Для пользователей организации возвращаем составной ID
            return f"org_{self.organization_id}_{self.id}"
        else:
            # Для обычных администраторов возвращаем обычный ID
            return str(self.id)
        
    @classmethod
    def create_org_user_proxy(cls, user, organization_id):
        """
        Создает прокси-объект Admin для пользователя организации.
        
        Args:
            user: Объект User из базы данных организации
            organization_id: ID администратора организации
            
        Returns:
            Admin: Прокси-объект для Flask-Login
        """
        print(f"Creating proxy object for user: {user.username}, org_admin_id: {organization_id}")
        temp_admin = cls()
        temp_admin.id = user.id
        temp_admin.username = user.username
        temp_admin.role = user.role
        temp_admin.organization_id = organization_id
        temp_admin.is_org_user = True
        temp_admin.active = True  # Устанавливаем как активного
        
        # Дополнительные атрибуты из User
        if hasattr(user, 'cabinet'):
            temp_admin.cabinet = user.cabinet
        if hasattr(user, 'video'):
            temp_admin.video = user.video
        if hasattr(user, 'style_type'):
            temp_admin.style_type = user.style_type
            
        # Получаем данные об организации для доступа к стилям
        org_admin = cls.query.get(organization_id)
        if org_admin:
            temp_admin.org_username = org_admin.username
            
        print(f"Created proxy object: {temp_admin}")
        return temp_admin

    @classmethod
    def load_user_by_id(cls, user_id):
        """
        Загружает пользователя по ID для Flask-Login.
        Обрабатывает как обычных администраторов, так и пользователей организаций.
        """
        print(f"Loading user by ID: {user_id}")
        
        if user_id.startswith('org_'):
            # Это пользователь организации
            try:
                _, org_admin_id, user_id_in_org = user_id.split('_', 2)
                org_admin_id = int(org_admin_id)
                user_id_in_org = int(user_id_in_org)
                
                print(f"Loading org user: org_admin_id={org_admin_id}, user_id={user_id_in_org}")
                
                # Получаем администратора организации
                org_admin = cls.query.get(org_admin_id)
                if not org_admin or not org_admin.is_active:
                    print(f"Organization admin not found or inactive: {org_admin_id}")
                    return None
                
                # Получаем сессию БД организации
                from app.db_manager import get_db_session
                org_db = get_db_session(org_admin_id)
                if not org_db:
                    print(f"Could not get org database session for admin: {org_admin_id}")
                    return None
                
                # Ищем пользователя в БД организации
                from app.models.secondary_admin import User
                user = org_db.query(User).filter_by(id=user_id_in_org).first()
                if not user:
                    print(f"User not found in org database: {user_id_in_org}")
                    return None
                
                # Создаем прокси-объект
                proxy_user = cls.create_org_user_proxy(user, org_admin_id)
                print(f"Successfully loaded org user: {proxy_user.username}")
                return proxy_user
                
            except (ValueError, IndexError) as e:
                print(f"Error parsing org user ID: {e}")
                return None
        else:
            # Это обычный администратор
            try:
                admin_id = int(user_id)
                admin = cls.query.get(admin_id)
                if admin and admin.is_active:
                    print(f"Successfully loaded admin: {admin.username}")
                    return admin
                else:
                    print(f"Admin not found or inactive: {admin_id}")
                    return None
            except ValueError:
                print(f"Invalid admin ID format: {user_id}")
                return None

    def __repr__(self):
        if self.is_org_user:
            return f'<OrgUser {self.username} (Role: {self.role})>'
        return f'<Admin {self.username} ({self.organization_name})>'