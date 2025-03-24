from app import create_app
from app.celery_config import celery

app = create_app()

if __name__ == '__main__':
    celery.start(argv=['celery', 'worker', '--loglevel=info'])