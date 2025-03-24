import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'my_secret_key_here'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))

    # Redis configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

    # Celery configuration
    broker_url = os.getenv('broker_url', 'amqp://guest:guest@rabbitmq:5672//')
    result_backend = os.getenv('result_backend', 'redis://redis:6379/0')
    accept_content = ['json']
    task_serializer = 'json'
    result_serializer = 'json'
    timezone = 'UTC'
    enable_utc = True
    broker_connection_retry_on_startup = True


class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')


class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
