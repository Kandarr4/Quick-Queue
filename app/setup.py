import os
import logging
from app import db
from app.models.models_app import Admin
from app.models.secondary_admin import Base, User, Service, Ticket, Terminal, Display, ServiceAssignment, ServiceSchedule, TicketStatistics
from app.db_manager import get_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import inspect, text
from flask import current_app

logger = logging.getLogger(__name__)

def setup_main_database():
    """Проверяет существование главной базы данных и создает её при необходимости."""
    db.create_all()
    logger.info("Main database tables created")

    main_admin = Admin.query.filter_by(role='main_admin').first()
    if not main_admin:
        main_admin = Admin(
            username='admin',
            role='main_admin',
            organization_name='Главный администратор',
            database_name='main'
        )
        main_admin.set_password('040100Somnium2')
        db.session.add(main_admin)
        db.session.commit()
        logger.info("Main administrator created with username 'admin'")
        print("\n" + "="*80)
        print("ВНИМАНИЕ! Создан главный администратор с логином 'admin' и паролем 'Ntcnjdsqgfhjkm@123'.")
        print("="*80 + "\n")
    else:
        logger.info(f"Main administrator already exists: {main_admin.username}")

def setup_db_folders():
    """Создает каталог для хранения баз данных организаций."""
    db_folder = current_app.config.get('DB_FOLDER')
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
        logger.info(f"Created database folder: {db_folder}")
    else:
        logger.info(f"Database folder already exists: {db_folder}")
        
    # Создаем директорию для стилей, если она не существует
    css_folder = os.path.join(current_app.static_folder, 'css')
    if not os.path.exists(css_folder):
        os.makedirs(css_folder)
        logger.info(f"Created CSS folder: {css_folder}")
    else:
        logger.info(f"CSS folder already exists: {css_folder}")

def initialize_org_database(db_name):
    """Инициализирует базу данных для новой организации."""
    engine = get_engine(db_name)
    
    # Явно создаем все таблицы, чтобы гарантировать их наличие
    Base.metadata.create_all(engine)
    
    # Проверяем наличие всех необходимых таблиц и создаем их, если они отсутствуют
    existing_tables = set(engine.dialect.get_table_names(engine.connect()))
    logger.info(f"Existing tables in {db_name}: {existing_tables}")
    
    # Перечень всех моделей, таблицы которых должны быть созданы
    models = [User, Service, Ticket, Terminal, Display, ServiceAssignment, ServiceSchedule, TicketStatistics]
    
    # Создаем отсутствующие таблицы
    for model in models:
        table_name = model.__tablename__
        if table_name not in existing_tables:
            model.__table__.create(engine)
            logger.info(f"Created missing table: {table_name} in database {db_name}")
    
    # Проверяем наличие новых полей в таблицах
    connection = engine.connect()
    for model in models:
        table_name = model.__tablename__
        if table_name in existing_tables:
            inspector = inspect(engine)
            existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
            
            # Проверяем новые поля для модели User
            if model == User and 'style_type' not in existing_columns:
                try:
                    logger.info(f"Adding missing column 'style_type' to table 'users' in database {db_name}")
                    connection.execute(text("ALTER TABLE users ADD COLUMN style_type VARCHAR(50) DEFAULT 'default'"))
                    logger.info(f"Successfully added column 'style_type' to table 'users'")
                except Exception as e:
                    logger.error(f"Error adding column 'style_type' to table 'users': {e}")
    
    connection.close()
    
    # Создаем начального администратора, если он ещё не существует
    session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    
    admin_user = session.query(User).filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(username='admin', role='admin')
        admin_user.set_password('admin')
        session.add(admin_user)
        session.commit()
        logger.info(f"Created initial admin user in database: {db_name}")
    else:
        logger.info(f"Admin user already exists in database: {db_name}")
        
    session.remove()