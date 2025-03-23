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
    redis_client = redis.Redis.from_url(app.config.get('REDIS_URL', 'redis://redis:6379/0'))

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    try:
        from app.routes import main
        app.register_blueprint(main)
    except ImportError:
        print("No routes blueprint found. Skipping blueprint registration.")
