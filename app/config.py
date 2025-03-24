# app/config.py
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
    BROKER_URL = 'amqp://guest:guest@rabbitmq:5672//'
    RESULT_BACKEND = 'redis://redis:6379/0'

    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'UTC'


class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    BROKER_URL = os.environ.get('broker_url', 'amqp://guest:guest@rabbitmq:5672//')
    RESULT_BACKEND = os.environ.get('result_backend', 'redis://redis:6379/0')


class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    # Celery settings
    broker_url = os.environ.get('broker_url', 'amqp://guest:guest@rabbitmq:5672//')
    result_backend = os.environ.get('result_backend', 'redis://redis:6379/0')
