from __future__ import annotations
from .user import User, UserRole

class Admin(User):
    def __init__(self, *args, **kwargs):
        kwargs['role'] = UserRole.ADMIN
        super().__init__(*args, **kwargs)

    def manage_users(self):
        print(f"Admin {self.email} is managing users.")
        # Logic to add, remove, update users - typically via application services
        pass

    def manage_readings(self):
        print(f"Admin {self.email} is managing readings.")
        # Logic to add, remove, update readings - typically via application services
        pass

    def view_system_analytics(self):
        print(f"Admin {self.email} is viewing system analytics.")
        # Logic to view system-wide analytics - typically via application services
        pass
