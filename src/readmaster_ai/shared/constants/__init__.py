# Application-wide constants.

# Example:
# DEFAULT_LANGUAGE = "en"
# MAX_AUDIO_DURATION_SECONDS = 600 # 10 minutes
# SUPPORTED_AUDIO_FORMATS = ["mp3", "wav", "m4a"]

class UserRoles: # Using a class for enum-like grouping
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"

    @classmethod
    def all(cls):
        return [cls.STUDENT, cls.PARENT, cls.TEACHER, cls.ADMIN]

class AssessmentStatuses:
    PENDING_AUDIO = "pending_audio"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

    @classmethod
    def all(cls):
        return [cls.PENDING_AUDIO, cls.PROCESSING, cls.COMPLETED, cls.ERROR]

# Add other constants as defined in the document or as they become necessary.
