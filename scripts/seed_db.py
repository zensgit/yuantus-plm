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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("yuantus.seeder")

def main():
    parser = argparse.ArgumentParser(description="Seed database with initial data.")
    parser.add_argument("--tenant", help="Tenant ID (for multi-tenant modes)", default="default")
    parser.add_argument("--org", help="Organization ID (for db-per-tenant-org mode)", default="default")
    args = parser.parse_args()

    settings = get_settings()
    logger.info(f"Running seeder in mode: {settings.TENANCY_MODE}")

    # Set context vars if needed
    if settings.TENANCY_MODE in ("db-per-tenant", "db-per-tenant-org"):
        tenant_id_var.set(args.tenant)
        if settings.TENANCY_MODE == "db-per-tenant-org":
            org_id_var.set(args.org)

        logger.info(f"Targeting Tenant: {args.tenant}, Org: {args.org}")

        try:
            session_factory = get_sessionmaker_for_scope(args.tenant, args.org)
            # Ensure DB is initialized (tables created)
            # We need to get the engine to init_db
            target_engine = session_factory.kw['bind']
            init_db(create_tables=True, bind_engine=target_engine)
            session = session_factory()
        except Exception as e:
            logger.error(f"Failed to initialize tenant DB: {e}")
            sys.exit(1)

    else:
        # Single DB mode
        init_db(create_tables=True)
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
