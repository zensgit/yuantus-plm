from yuantus.models.user import User
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class UserSeeder(BaseSeeder):
    """Seeds initial system users."""
    priority = 10  # Very high priority

    def run(self):
        # 1. Admin User
        self._ensure_user(
            username="admin",
            email="admin@yuantus.com",
            is_active=True
        )

        # 2. System Bot (for internal ops)
        self._ensure_user(
            username="system-bot",
            email="bot@yuantus.com",
            is_active=True
        )

    def _ensure_user(self, username: str, email: str, is_active: bool = True):
        existing = self.session.query(User).filter_by(username=username).first()
        if existing:
            self.log(f"User '{username}' already exists. Skipping.")
            return existing

        user = User(
            username=username,
            email=email,
            is_active=is_active
        )
        self.session.add(user)
        self.log(f"Created user '{username}'.")
        return user
