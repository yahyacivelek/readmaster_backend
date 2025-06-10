from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os # For environment variables

# It's good practice to get sensitive info from environment variables
DB_USER = os.getenv("DB_USER", "user") # Default user for local dev
DB_PASSWORD = os.getenv("DB_PASSWORD", "password") # Default pass for local dev
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432") # Default PostgreSQL port
DB_NAME = os.getenv("DB_NAME", "postgres")

DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
print(f"DATABASE_URL: {DATABASE_URL}")

# echo=True is useful for development to see SQL queries, consider turning off for production
engine = create_async_engine(DATABASE_URL, echo=os.getenv("SQL_ECHO", "True").lower() == "true")

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit() # Commit session if no exceptions
        except Exception:
            await session.rollback() # Rollback on error
            raise
        finally:
            await session.close() # Ensure session is closed
