"""
Celery application instance for Readmaster.ai.

This module initializes the Celery application, loads its configuration,
and discovers tasks defined within the project.

To run a Celery worker for this application (from the project root):
  poetry run celery -A src.readmaster_ai.core.celery_app worker -l INFO

If you have specific queues (e.g., 'ai_processing'):
  poetry run celery -A src.readmaster_ai.core.celery_app worker -l INFO -Q ai_processing,default

Ensure your message broker (e.g., Redis) is running.
"""
from celery import Celery

# The first argument to Celery is the name of the current module.
# This is important so that names can be generated automatically when tasks
# are defined in other modules (e.g., using the @celery_app.task decorator).
# Using a descriptive name like 'readmaster_ai_worker' is good practice.
celery_app = Celery("readmaster_ai_worker")

# Load configuration from the celery_config.py module.
# The namespace 'CELERY' means all configuration keys in celery_config.py
# that start with 'CELERY_' will be loaded (e.g., CELERY_BROKER_URL becomes broker_url).
celery_app.config_from_object('readmaster_ai.core.celery_config', namespace='CELERY')

# Autodiscover tasks from packages listed.
# Celery will look for a `tasks.py` module within each package specified.
# For example, if 'readmaster_ai.infrastructure.ai' is listed, Celery will
# look for 'readmaster_ai.infrastructure.ai.tasks.py'.
# The `related_name='tasks'` argument ensures that Celery specifically looks for 'tasks.py'.
# If you use a different file name (e.g., 'celery_tasks.py'), adjust `related_name` accordingly.
celery_app.autodiscover_tasks(
    packages=[
        'readmaster_ai.infrastructure.ai', # For AI processing tasks
        # Add other packages here if they contain Celery tasks, e.g.:
        # 'readmaster_ai.application.services', # If services define tasks
    ],
    related_name='tasks' # Looks for tasks.py in the listed packages
)

# Optional: Set this Celery app instance as the default for the current process.
# This can be useful if you are working with Celery in a way that relies on a
# default app instance being available, though explicit app instances are often preferred.
# celery_app.set_default()

# Example simple task defined directly in the app module (less common for larger apps)
# @celery_app.task(name="debug_task")
# def debug_task(message: str):
#     print(f"Debug task received: {message}")
#     return f"Message processed: {message}"

if __name__ == '__main__':
    # This block allows running the worker directly using `python -m src.readmaster_ai.core.celery_app worker ...`
    # However, `poetry run celery -A ...` is the more standard way with Poetry projects.
    celery_app.start()
