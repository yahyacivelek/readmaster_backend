from fastapi import APIRouter

# This router can aggregate all v1 routers
api_v1_router = APIRouter(prefix="/api/v1")

# Example: Import and include other routers
# from .user_router import router as user_router
# api_v1_router.include_router(user_router, tags=["Users"])

# Placeholder for a health check endpoint
@api_v1_router.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
