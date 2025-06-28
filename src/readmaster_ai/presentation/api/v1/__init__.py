from fastapi import APIRouter
from .user_router import router as user_api_router
from .auth_router import router as auth_api_router
from .admin_router import router as admin_api_router
from .reading_router import router as student_reading_api_router
from .assessment_router import router as assessment_api_router
from .teacher_router import router as teacher_api_router # Keep one
from .parent_router import router as parent_api_router
from .websocket_router import router as websocket_api_router
from .notification_router import router as notification_api_router # New import
from .student import router as student_api_router # Corrected import path

# This router can aggregate all v1 routers
api_v1_router = APIRouter(prefix="/api/v1")

# Placeholder for a health check endpoint
@api_v1_router.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

api_v1_router.include_router(user_api_router)
api_v1_router.include_router(auth_api_router)
api_v1_router.include_router(admin_api_router)
api_v1_router.include_router(student_reading_api_router)
api_v1_router.include_router(assessment_api_router)
api_v1_router.include_router(teacher_api_router)
api_v1_router.include_router(parent_api_router)
api_v1_router.include_router(websocket_api_router)
api_v1_router.include_router(notification_api_router) # Include the notification router
api_v1_router.include_router(student_api_router) # Include the student router
# Add other routers here as they are created
