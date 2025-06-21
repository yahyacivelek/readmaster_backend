"""
API v1 Router - Combines all v1 API routers.
"""
from fastapi import APIRouter

# Import all v1 routers
from .user_router import router as user_router
from .auth_router import router as auth_router
from .admin_router import router as admin_router
from .assessment_router import router as assessment_router
from .parent_router import router as parent_router
from .teacher_router import router as teacher_router
from .reading_router import router as reading_router
from .notification_router import router as notification_router
from .websocket_router import router as websocket_router
from .student_router import router as student_router

# Create main v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Include all v1 routers
api_v1_router.include_router(user_router.router)
api_v1_router.include_router(auth_router.router)
api_v1_router.include_router(admin_router.router)
api_v1_router.include_router(assessment_router.router)
api_v1_router.include_router(parent_router.router)
api_v1_router.include_router(teacher_router.router)
api_v1_router.include_router(reading_router.router)
api_v1_router.include_router(notification_router.router)
api_v1_router.include_router(websocket_router.router)
api_v1_router.include_router(student_router.router)  # Add student router
