"""
Celery configuration settings for Readmaster.ai.

These settings define how Celery connects to the message broker (Redis)
and result backend, as well as task serialization and other operational parameters.
It's recommended to use environment variables for sensitive or environment-specific
configurations like broker/backend URLs in production.
"""
import os

# --- Redis Configuration ---
# Default to localhost if environment variables are not set.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379")) # Ensure port is integer

# --- Celery Broker and Result Backend URLs ---
# Using different Redis databases for broker and backend is a common practice.
# Ensure your Redis server is configured to handle these databases if needed.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", f"redis://{REDIS_HOST}:{REDIS_PORT}/1")

# --- Task Serialization and Content Types ---
CELERY_TASK_SERIALIZER = 'json'       # Default serializer for task messages.
CELERY_RESULT_SERIALIZER = 'json'     # Default serializer for task results.
CELERY_ACCEPT_CONTENT = ['json']      # Allowed content types for messages.

# --- Timezone Settings ---
# It's good practice to use UTC for internal Celery operations.
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# --- Task Behavior Settings ---
CELERY_TASK_TRACK_STARTED = True      # If True, task status will be updated to 'STARTED' when executed by a worker.
CELERY_TASK_ACKS_LATE = True          # Tasks acknowledge messages after completion (or failure beyond retries).
                                      # This can help prevent message loss if a worker crashes mid-task.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1 # Often set to 1 for long-running I/O bound tasks to prevent workers
                                      # from holding onto too many tasks that they can't process quickly.

# --- Optional: Task Routing ---
# Example for routing specific tasks to specific queues.
# This is useful for prioritizing tasks or dedicating workers to certain types of jobs.
# CELERY_TASK_ROUTES = {
# 'readmaster_ai.infrastructure.ai.tasks.process_assessment_audio_task': {'queue': 'ai_processing'},
#     # 'module.submodule.task_name': {'queue': 'queue_name'},
# }

# --- Optional: Concurrency Settings (can also be set via CLI) ---
# CELERY_WORKER_CONCURRENCY = os.getenv("CELERY_WORKER_CONCURRENCY", None) # Defaults to number of CPUs

# --- Optional: Broker Connection Pool Limits (for Redis) ---
# BROKER_POOL_LIMIT = 10 # Default is 10

# --- Optional: Result Backend Settings ---
# CELERY_RESULT_EXPIRES = timedelta(days=7) # Default is 1 day. How long to keep task results.
# CELERY_MAX_CACHED_RESULTS = -1 # Default: -1 (unlimited). Max results to cache in memory.

print(f"Celery Broker URL: {CELERY_BROKER_URL}")
print(f"Celery Result Backend URL: {CELERY_RESULT_BACKEND}")
