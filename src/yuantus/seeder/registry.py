import logging
from typing import List, Type
from sqlalchemy.orm import Session
from faker import Faker

from .base import BaseSeeder

logger = logging.getLogger(__name__)

class SeederRegistry:
    """Registry to manage and execute registered seeders."""

    _seeders: List[Type[BaseSeeder]] = []

    @classmethod
    def register(cls, seeder_cls: Type[BaseSeeder]):
        """Decorator to register a seeder class."""
        cls._seeders.append(seeder_cls)
        return seeder_cls

    @classmethod
    def run_all(cls, session: Session):
        """Run all registered seeders in priority order."""
        fake = Faker()

        # Sort seeders by priority (ascending)
        sorted_seeders = sorted(cls._seeders, key=lambda x: x.priority)

        total = len(sorted_seeders)
        logger.info(f"Starting seeding process. {total} seeders registered.")

        for index, seeder_cls in enumerate(sorted_seeders, 1):
            seeder = seeder_cls(session, fake)
            try:
                seeder.log(f"Running ({index}/{total})...")
                seeder.run()
                session.commit()
                seeder.log("Completed.")
            except Exception as e:
                session.rollback()
                logger.error(f"Seeder {seeder_cls.__name__} failed: {e}")
                raise
