from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session
from faker import Faker
import logging

logger = logging.getLogger(__name__)

class BaseSeeder(ABC):
    """
    Abstract base class for all data seeders.

    Attributes:
        priority (int): Execution order priority (lower runs first).
                        Core data should use 0-100.
                        Meta/Config data should use 100-500.
                        Demo/Test data should use 500+.
    """
    priority: int = 100

    def __init__(self, session: Session, fake: Optional[Faker] = None):
        self.session = session
        self.fake = fake or Faker()

    @abstractmethod
    def run(self):
        """Execute the seeding logic."""
        pass

    def log(self, message: str):
        """Helper to log seeding progress."""
        logger.info(f"[{self.__class__.__name__}] {message}")
