import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Каталог для хранения баз данных организаций
    DB_FOLDER = os.environ.get('DB_FOLDER') or os.path.join(os.path.abspath(os.path.dirname(__file__)), 'org_databases')

    # Настройки JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # Настройки логирования
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
