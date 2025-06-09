import os
import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine # Changed from sqlalchemy.engine import Connection

from alembic import context

# Import Base metadata and DATABASE_URL from application's config
# Ensure the path is correct relative to where alembic is run (project root)
from src.readmaster_ai.infrastructure.database.models import Base as target_metadata
from src.readmaster_ai.infrastructure.database.config import DATABASE_URL

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the sqlalchemy.url from our application's DATABASE_URL
# This overrides the commented-out one in alembic.ini
config.set_main_option('sqlalchemy.url', DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # url = config.get_main_option("sqlalchemy.url") # Already set to DATABASE_URL
    context.configure(
        url=DATABASE_URL, # Use DATABASE_URL directly
        target_metadata=target_metadata,
        literal_binds=True, # Render SQL parameters directly in migration scripts
        dialect_opts={"paramstyle": "named"}, # Standard paramstyle for SQLAlchemy
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection): # connection is a synchronous SQLAlchemy connection
    """
    Helper function to run migrations with a given synchronous connection.
    This is called by run_migrations_online via await connection.run_sync().
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Include other options like compare_type=True if needed for autogenerate
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Create an async engine from DATABASE_URL
    connectable = create_async_engine(
        DATABASE_URL,
        echo=False, # Set to True to see SQL queries, or get from env var
    )

    async with connectable.connect() as connection: # Use async connection
        # Run migrations within the run_sync callback
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine when done
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
