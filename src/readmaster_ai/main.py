from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from readmaster_ai.presentation.api.v1 import api_v1_router
# from readmaster_ai.shared.exceptions import ApplicationException # For global exception handling
# from fastapi.responses import JSONResponse # For global exception handling
# from readmaster_ai.infrastructure.database.config import engine, Base # If using Alembic and initial schema setup

app = FastAPI(
    title="Readmaster.ai API",
    version="0.1.0",
    description="API for Readmaster.ai, a web-based reading assessment platform."
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include v1 router
app.include_router(api_v1_router)

# Placeholder for global exception handler
# @app.exception_handler(ApplicationException)
# async def application_exception_handler(request, exc: ApplicationException):
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"detail": exc.message},
#     )

@app.on_event("startup")
async def startup_event():
    # Placeholder for startup logic, e.g., initial database connection check
    # May not be needed if using Alembic for schema creation
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all) # Example: create tables, use with caution
    print("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    # Placeholder for shutdown logic
    print("Application shutdown complete.")

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to Readmaster.ai API"}

# To run this app (from the project root directory):
# poetry run uvicorn src.readmaster_ai.main:app --reload
