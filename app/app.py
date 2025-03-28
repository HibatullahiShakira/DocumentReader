from flask import Flask
import os
import redis
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse
from sqlalchemy import create_engine

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

    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')
    if not db_uri:
        raise ValueError("DATABASE_URL or SQLALCHEMY_DATABASE_URI must be set")

    db_url = urlparse(db_uri)
    db_name = db_url.path[1:]  # Remove the leading '/'
    db_user = db_url.username
    db_pass = db_url.password
    db_host = db_url.hostname
    db_port = db_url.port

    # Connect to PostgreSQL server (without specifying a database) to create the database
    try:
        conn = psycopg2.connect(
            dbname='postgres',  # Connect to the default 'postgres' database
            user=db_user,
            password=db_pass,
            host=db_host,
            port=db_port
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if the database exists, and create it if it doesn't
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        if not exists:
            print(f"Creating database {db_name}")
            cursor.execute(f"CREATE DATABASE {db_name}")
        else:
            print(f"Database {db_name} already exists")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to create database: {e}")
        raise

    # Initialize Flask-SQLAlchemy
    db.init_app(app)

    with app.app_context():
        print("Creating database tables")
        db.create_all()
        print("Database tables created successfully")

    init_routes(app, redis_client, parser)

    print("Creating upload folder")
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app