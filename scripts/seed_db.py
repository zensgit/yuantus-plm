import sys
import os
import argparse
import logging

# Add src to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from yuantus.database import get_sessionmaker_for_scope, SessionLocal, init_db, engine
from yuantus.config import get_settings
from yuantus.context import tenant_id_var, org_id_var
from yuantus.seeder import SeederRegistry
from yuantus.models.base import Base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("yuantus.seeder")

def drop_all_tables(target_engine, force=False):
    """Drops all tables with safety check."""
    if not force:
        print("⚠️  WARNING: You are about to DROP ALL DATA from the database.")
        response = input("Type 'yes' to confirm: ")
        if response.lower() != 'yes':
            logger.info("Operation cancelled.")
            sys.exit(0)

    logger.warning("Dropping all tables...")
    # This drops all tables defined in Base.metadata
    Base.metadata.drop_all(bind=target_engine)
    logger.info("All tables dropped.")

def main():
    parser = argparse.ArgumentParser(description="Seed database with initial data.")
    parser.add_argument("--tenant", help="Tenant ID (for multi-tenant modes)", default="default")
    parser.add_argument("--org", help="Organization ID (for db-per-tenant-org mode)", default="default")
    parser.add_argument("--drop-all", action="store_true", help="Drop all tables before seeding (Dangerous!)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt for --drop-all")
    args = parser.parse_args()

    settings = get_settings()
    logger.info(f"Running seeder in mode: {settings.TENANCY_MODE}")

    # Variables to hold session and engine
    session = None
    target_engine = None

    # Set context vars if needed
    if settings.TENANCY_MODE in ("db-per-tenant", "db-per-tenant-org"):
        tenant_id_var.set(args.tenant)
        if settings.TENANCY_MODE == "db-per-tenant-org":
            org_id_var.set(args.org)

        logger.info(f"Targeting Tenant: {args.tenant}, Org: {args.org}")

        try:
            session_factory = get_sessionmaker_for_scope(args.tenant, args.org)
            target_engine = session_factory.kw['bind']
        except Exception as e:
            logger.error(f"Failed to initialize tenant DB context: {e}")
            sys.exit(1)
    else:
        # Single DB mode
        target_engine = engine

    # Handle Drop All
    if args.drop_all:
        if not target_engine:
             logger.error("Database engine not initialized, cannot drop tables.")
             sys.exit(1)
        drop_all_tables(target_engine, force=args.force)

    # Initialize Tables (Create if not exist, or Re-create after drop)
    init_db(create_tables=True, bind_engine=target_engine)

    # Create Session
    if settings.TENANCY_MODE in ("db-per-tenant", "db-per-tenant-org"):
        session_factory = get_sessionmaker_for_scope(args.tenant, args.org)
        session = session_factory()
    else:
        session = SessionLocal()

    try:
        SeederRegistry.run_all(session)
        logger.info("✅ Seeding completed successfully!")
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()
