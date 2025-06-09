from enum import Enum

class Permission(Enum):
    CREATE_USER = "create_user"
    VIEW_USER = "view_user" # Added as an example, document doesn't list all
    UPDATE_USER = "update_user" # Added
    DELETE_USER = "delete_user" # Added

    CREATE_READING = "create_reading"
    VIEW_READING = "view_reading" # Added
    UPDATE_READING = "update_reading" # Added
    DELETE_READING = "delete_reading" # Added

    ASSIGN_ASSESSMENT = "assign_assessment"
    TAKE_ASSESSMENT = "take_assessment" # Added
    VIEW_ASSESSMENT_RESULTS = "view_assessment_results" # Added

    MANAGE_CLASSES = "manage_classes" # Added
    ENROLL_STUDENTS = "enroll_students" # Added

    VIEW_OWN_PROGRESS = "view_own_progress"
    VIEW_STUDENT_PROGRESS = "view_student_progress" # For teachers/parents

    VIEW_REPORTS = "view_reports" # Added
    MANAGE_SYSTEM_CONFIG = "manage_system_config" # Added
    VIEW_SYSTEM_ANALYTICS = "view_system_analytics" # Added
    # ... more permissions based on system features

ROLE_PERMISSIONS = {
    "student": {
        Permission.TAKE_ASSESSMENT,
        Permission.VIEW_OWN_PROGRESS,
        Permission.VIEW_READING, # Students should be able to view readings
        Permission.VIEW_ASSESSMENT_RESULTS, # Students should see their own results
    },
    "parent": {
        Permission.VIEW_STUDENT_PROGRESS, # Assuming this means their children's progress
        Permission.VIEW_ASSESSMENT_RESULTS, # Their children's results
        Permission.VIEW_READING, # Parents might want to see what their children are reading
    },
    "teacher": {
        Permission.ASSIGN_ASSESSMENT,
        Permission.VIEW_STUDENT_PROGRESS,
        Permission.MANAGE_CLASSES,
        Permission.ENROLL_STUDENTS,
        Permission.CREATE_READING, # Teachers might add readings
        Permission.VIEW_READING,
        Permission.UPDATE_READING, # If they created it
        Permission.VIEW_REPORTS,
        Permission.VIEW_ASSESSMENT_RESULTS, # For their students
    },
    "admin": {p for p in Permission} # Admin gets all permissions
}
