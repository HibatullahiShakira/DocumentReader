# app/__init__.py
import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import redis
from app.config import DevelopmentConfig
from app.celery_config import make_celery

db = SQLAlchemy()
redis_client = None

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
celery = make_celery(app)


def create_app():
    global redis_client

    db.init_app(app)

    try:
        redis_client = redis.Redis.from_url(app.config.get('REDIS_URL', 'redis://localhost:6379/0'))

        redis_client.ping()
        print("Successfully connected to Redis")
    except Exception as e:
        print(f"Warning: Could not connect to Redis: {e}")
        print("Continuing without Redis. Some features (e.g., Celery tasks) may not work.")
        redis_client = None

    try:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        print(f"Upload folder created at: {app.config['UPLOAD_FOLDER']}")
    except Exception as e:
        print(f"Error creating upload folder: {e}")
        raise e

    try:
        from app.routes import main
        app.register_blueprint(main)
        print("Routes blueprint registered")
    except ImportError:
        print("No routes blueprint found. Skipping blueprint registration.")

    return app
