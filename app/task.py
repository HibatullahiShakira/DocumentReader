
from app import celery


@celery.task
def hello_world():
    return "Hello World from Celery!"

