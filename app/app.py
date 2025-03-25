from flask import Flask
import os
import redis
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

nltk.download('vader_lexicon')

load_dotenv()

from app.routes import init_routes
from app.models import PitchDeckParser, db
from app.config import get_config


def create_app():
    app = Flask(__name__, static_folder='/app/app/static')

    print(f"Static folder path: {app.static_folder}")

    config = get_config()
    app.config.from_object(config)

    try:
        redis_client = redis.Redis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=app.config['REDIS_DB'],
            decode_responses=True
        )
        redis_client.ping()
        print("Successfully connected to Redis")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {e}")
        raise

    sia = SentimentIntensityAnalyzer()
    parser = PitchDeckParser(sia=sia)

    print("Starting Flask application")

    db.init_app(app)

    with app.app_context():
        print("Creating database tables")
        db.create_all()
        print("Database tables created successfully")

    init_routes(app, redis_client, parser)

    print("Creating upload folder")
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app
