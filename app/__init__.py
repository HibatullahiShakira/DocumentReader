from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import os
import redis
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

from app.celery_config import make_celery

celery = None


def create_app():
    print("Starting create_app()", flush=True)
    app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')))

    print(f"FLASK_ENV: {os.getenv('FLASK_ENV')}", flush=True)
    if os.getenv('FLASK_ENV') == 'development':
        print("Loading DevelopmentConfig", flush=True)
        app.config.from_object('app.config.DevelopmentConfig')
    else:
        print("Loading ProductionConfig", flush=True)
        app.config.from_object('app.config.ProductionConfig')

    # Debug: Print SQLALCHEMY_DATABASE_URI
    print("SQLALCHEMY_DATABASE_URI:", app.config.get('SQLALCHEMY_DATABASE_URI'), flush=True)

    # Ensure upload folder exists
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        print(f"Upload folder created at: {upload_folder}", flush=True)

    # Initialize extensions
    print("Initializing SQLAlchemy", flush=True)
    db.init_app(app)

    # Test database connection
    print("Testing database connection", flush=True)
    with app.app_context():
        try:
            db.session.execute(text('SELECT 1'))  # Wrap the query in text()
            print("Successfully connected to the database", flush=True)
        except Exception as e:
            print(f"Failed to connect to the database: {e}", flush=True)
            raise e

    # Test Redis connection
    print("Testing Redis connection", flush=True)
    try:
        r = redis.Redis.from_url(app.config['REDIS_URL'])
        r.ping()
        print("Successfully connected to Redis", flush=True)
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {e}", flush=True)
        raise e

    # Initialize Celery
    print("Initializing Celery", flush=True)
    global celery
    celery = make_celery(app)
    app.celery = celery  # Still attach to app for compatibility

    print(f"Upload folder created at: {upload_folder}", flush=True)
    print("Routes blueprint registered", flush=True)

    # Import models before creating tables
    print("Importing models", flush=True)
    from app.models import File, Slide

    # Create database tables
    print("Creating database tables", flush=True)
    with app.app_context():
        try:
            db.create_all()
            print("Database tables created successfully", flush=True)
        except Exception as e:
            print(f"Failed to create database tables: {e}", flush=True)
            raise e

    # Register blueprints after everything is initialized
    print("Registering blueprints", flush=True)
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    print("create_app() completed", flush=True)
    return app
