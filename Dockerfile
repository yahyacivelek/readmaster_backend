# 1. Set base image
FROM python:3.9-slim

# 2. Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="$POETRY_HOME/bin:$PATH" \
    PYTHONPATH=/app

# 3. Install OS dependencies
# Install curl for downloading Poetry, and build-essential for any C extensions.
# Add other OS dependencies if your project needs them (e.g., libpq-dev for psycopg2)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Install Poetry
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# 5. Set working directory
WORKDIR /app

# 6. Copy dependency definition files
COPY poetry.lock pyproject.toml ./

# 7. Install project dependencies
RUN poetry install --no-root

# 8. Copy application code
# This will copy everything from the build context (your project root) into /app in the image.
# Ensure you have a .dockerignore file to exclude unnecessary files/folders (like .git, .venv, __pycache__, etc.)
COPY . .

# 9. Install the package in development mode
RUN poetry install

# 10. Expose port (for the API service)
# This is documentation; the actual port mapping is done in docker-compose.yml or via `docker run -p`
EXPOSE 8000

# 11. Set default command (optional, can be overridden in docker-compose.yml)
# The command to run the application will be specified in docker-compose.yml
# For example: CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Or for a worker: CMD ["poetry", "run", "celery", "-A", "src.core.celery_app.celery_app", "worker", "-l", "info"]
# Leaving it empty here as docker-compose.yml will define the CMD for api and worker services.
CMD []
