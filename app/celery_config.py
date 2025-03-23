# app/celery_config.py
from celery import Celery


def make_celery(app):
    celery = Celery(app.import_name)

    # Use old-style configuration keys to match app.config
    celery_config = {
        'BROKER_URL': app.config['BROKER_URL'],
        'RESULT_BACKEND': app.config['RESULT_BACKEND'],
        'CELERY_ACCEPT_CONTENT': app.config['CELERY_ACCEPT_CONTENT'],
        'CELERY_TASK_SERIALIZER': app.config['CELERY_TASK_SERIALIZER'],
        'CELERY_RESULT_SERIALIZER': app.config['CELERY_RESULT_SERIALIZER'],
        'CELERY_TIMEZONE': app.config['CELERY_TIMEZONE'],
        'BROKER_CONNECTION_RETRY_ON_STARTUP': True,
    }
    celery.conf.update(celery_config)
    celery.conf.update(app.config)

    # Debug the Celery configuration
    print("make_celery: Celery broker after config:", celery.conf.get('BROKER_URL'))
    print("make_celery: Celery backend after config:", celery.conf.get('RESULT_BACKEND'))

    # Ensure the configuration is applied when the worker starts
    celery.config_from_object(celery_config, force=True)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
