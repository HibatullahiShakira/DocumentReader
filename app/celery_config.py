from celery import Celery

def make_celery(app):
    celery = Celery(app.import_name)

    celery_config = {
        'broker_url': app.config['broker_url'],
        'result_backend': app.config['result_backend'],
        'accept_content': app.config['accept_content'],
        'task_serializer': app.config['task_serializer'],
        'result_serializer': app.config['result_serializer'],
        'timezone': app.config['timezone'],
        'enable_utc': app.config['enable_utc'],
        'broker_connection_retry_on_startup': app.config['broker_connection_retry_on_startup'],
    }
    celery.conf.update(celery_config)

    # Debugging (uncomment if needed)
    # print("make_celery: Celery broker after config:", celery.conf.get('broker_url'), flush=True)
    # print("make_celery: Celery backend after config:", celery.conf.get('result_backend'), flush=True)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery