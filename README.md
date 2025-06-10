# Readmaster.ai

Readmaster.ai is a web-based reading assessment and development platform that uses artificial intelligence to analyze and help improve students' reading performance. The system consists of a frontend web application and a backend service that handles AI processing and database operations.

## Key Features
* AI-powered reading fluency analysis
* Pronunciation assessment
* Reading comprehension evaluation
* Multi-language support
* Real-time progress tracking
* Role-based access control (Students, Parents, Teachers, Admins)

## Technical Overview
This repository contains the backend service for Readmaster.ai.
- **Framework:** FastAPI
- **Database:** PostgreSQL (with SQLAlchemy and Alembic)
- **Architecture:** Clean Architecture
- **Authentication:** JWT
- **Async Operations:** Celery for background tasks, FastAPI async for I/O

## Setup and Installation

(TODO: Add instructions for setting up the project without Docker, e.g., using Poetry or pip with a virtual environment, once the project is more mature.)

## Local Development

This project uses Docker and Docker Compose to simplify local development and ensure a consistent environment.

### Prerequisites

* Docker: [Install Docker](https://docs.docker.com/get-docker/)
* Docker Compose: [Install Docker Compose](https://docs.docker.com/compose/install/)

### Building and Running with Docker Compose

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/readmaster.ai.git
    cd readmaster.ai
    ```

2.  **Environment Variables:**
    Copy the example environment file and update it with your specific configurations:
    ```bash
    cp .env.example .env
    ```
    *Note: Ensure the `.env` file has the correct database credentials, API keys, etc.*

3.  **Build and run the application:**
    This command will build the Docker images (if they don't exist) and start all the services defined in `docker-compose.yml` in detached mode.
    ```bash
    docker-compose up -d
    ```

4.  **Accessing the application:**
    Once the containers are up and running:
    *   The FastAPI backend will typically be available at `http://localhost:8000`.
    *   The Celery worker will be running in the background.
    *   The PostgreSQL database will be accessible on its default port (usually 5432), but typically you'll interact with it through the application.

### Basic Docker Compose Commands

*   **Start services in detached mode:**
    ```bash
    docker-compose up -d
    ```

*   **Stop services:**
    ```bash
    docker-compose down
    ```

*   **View logs for all services:**
    ```bash
    docker-compose logs
    ```

*   **View logs for a specific service (e.g., `backend`):**
    ```bash
    docker-compose logs backend
    ```

*   **Follow logs in real-time:**
    ```bash
    docker-compose logs -f
    ```
    or for a specific service:
    ```bash
    docker-compose logs -f backend
    ```

*   **Rebuild images and restart services:**
    ```bash
    docker-compose up -d --build
    ```

*   **Execute a command inside a running container (e.g., run Alembic migrations):**
    ```bash
    docker-compose exec backend alembic upgrade head
    ```
    (Assuming your backend service is named `backend` in `docker-compose.yml`)

## Database Migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) to manage database schema migrations, integrated with SQLAlchemy. Migration scripts are located in the `alembic/versions/` directory.

### Running Migrations

To apply the latest database migrations:

*   **If using Docker Compose:**
    ```bash
    docker-compose exec backend alembic upgrade head
    ```
    (Ensure your services are running: `docker-compose up -d`)

*   **If running locally with Poetry:**
    First, ensure your Poetry shell is activated (`poetry shell`) and your database server is running and accessible.
    ```bash
    alembic upgrade head
    ```

This command applies all pending migrations to your database, bringing it up to the latest version. It's crucial to run this after pulling new changes that include database schema modifications or when setting up the project for the first time.

### Creating New Migrations

When you make changes to your SQLAlchemy models (e.g., in `src/infrastructure/data/models/`) that require a database schema alteration, you need to generate a new migration script.

1.  **Ensure your models are updated.**

2.  **Generate the migration script:**
    *   **If using Docker Compose:**
        ```bash
        docker-compose exec backend alembic revision -m "your_migration_message_here"
        ```
        Replace `"your_migration_message_here"` with a short, descriptive message about the changes (e.g., "add_user_email_column").

    *   **If running locally with Poetry:**
        (Ensure Poetry shell is activated)
        ```bash
        alembic revision -m "your_migration_message_here"
        ```

3.  **Review and edit the generated script:**
    A new Python file will be created in `alembic/versions/`. Open this file and review the `upgrade()` and `downgrade()` functions. Alembic attempts to auto-generate the changes, but you **must** review and adjust them as needed to ensure they accurately reflect your intended schema modifications. Pay close attention to data migrations if required.

4.  **Apply the new migration:**
    After confirming the script is correct, run `alembic upgrade head` as described above.

5.  **Commit the migration script** along with your model changes to version control.

## Running Unit Tests

This project uses [Pytest](https://pytest.org/) for unit testing. Tests are located in the `tests/` directory.

### Prerequisites

*   Python (version compatible with the project, e.g., 3.9+)
*   Poetry: [Install Poetry](https://python-poetry.org/docs/#installation)

### Setup

1.  **Install project dependencies (including dev dependencies):**
    Navigate to the project root directory (where `pyproject.toml` is located).
    ```bash
    poetry install
    ```
    This command creates a virtual environment if one doesn't exist and installs all dependencies specified in `poetry.lock` (or `pyproject.toml` if `poetry.lock` is not present).

2.  **Activate the virtual environment:**
    To run commands within the project's isolated environment, activate the Poetry shell:
    ```bash
    poetry shell
    ```
    You should see your shell prompt change to indicate that you are now inside the virtual environment.

### Running Tests

Once the virtual environment is activated and dependencies are installed, you can run the unit tests using Pytest:

```bash
pytest
```
Or, to run with more verbose output:
```bash
pytest -vv
```

Pytest will automatically discover and run tests in the `tests/` directory.