from celery import Celery

celery = Celery('app')

def init_celery(app):
    celery.conf.update(
        broker_url=app.config['BROKER_URL'],
        result_backend=app.config['RESULT_BACKEND'],
        accept_content=app.config['ACCEPT_CONTENT'],
        task_serializer=app.config['TASK_SERIALIZER'],
        result_serializer=app.config['RESULT_SERIALIZER'],
        timezone=app.config['TIMEZONE'],
        enable_utc=app.config.get('ENABLE_UTC', True),
        broker_connection_retry_on_startup=app.config.get('BROKER_CONNECTION_RETRY_ON_STARTUP', True),
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery