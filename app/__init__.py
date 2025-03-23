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


# print("app.__init__.py: Celery broker at module level:", celery.conf.get('BROKER_URL'))
# print("app.__init__.py: Celery backend at module level:", celery.conf.get('RESULT_BACKEND'))

def create_app():
    global redis_client
    print("app.config keys:", app.config.keys())
    print("BROKER_URL:", app.config.get('BROKER_URL'))
    print("RESULT_BACKEND:", app.config.get('RESULT_BACKEND'))
    print("Celery broker:", celery.conf.get('BROKER_URL'))
    print("Celery backend:", celery.conf.get('RESULT_BACKEND'))

    db.init_app(app)
    redis_client = redis.Redis.from_url(app.config.get('REDIS_URL', 'redis://redis:6379/0'))

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    try:
        from app.routes import main
        app.register_blueprint(main)
    except ImportError:
        print("No routes blueprint found. Skipping blueprint registration.")

    @app.route('/')
    def hello():
        return "Hello World from Flask!"

    @app.route('/test-celery', methods=['GET'])
    def test_celery():
        task = celery.send_task('tasks.hello_world')
        return jsonify({"status": "success", "message": "Task triggered", "task_id": task.id})

    @app.route('/test-redis', methods=['GET'])
    def test_redis():
        try:
            redis_client.set('test_key', 'Hello from Redis!')
            value = redis_client.get('test_key')
            return jsonify({"status": "success", "message": value.decode('utf-8')})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    with app.app_context():
        db.create_all()

    return app