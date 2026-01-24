# Data Seeder Framework

A modular, registry-based data seeding framework for Yuantus PLM.
This tool allows developers to populate the database with initial configuration (Meta) and large-scale test data (Demo).

## 🚀 Quick Start

Run the seeding script from the project root:

```bash
# Default (Local/Dev)
python scripts/seed_db.py

# Multi-Tenant Environment
python scripts/seed_db.py --tenant tenant-1 --org engineering
```

## 📂 Architecture

The framework uses a **Registry + Factory** pattern.
Seeders are registered via decorator and executed in priority order.

### Directory Structure

```text
src/yuantus/seeder/
├── base.py              # BaseSeeder class (Faker integration)
├── registry.py          # Execution engine
├── core/                # Priority 0-100: Critical system data (Users, Roles)
├── meta/                # Priority 100-500: Configuration (Schema, Lifecycle, Workflow)
└── demo/                # Priority 500+: Test data (Items, BOMs, ECOs)
```

## 🛠️ How to Add a New Seeder

1. Create a new file in the appropriate subdirectory (e.g., `src/yuantus/seeder/demo/projects.py`).
2. Inherit from `BaseSeeder` and use the `@SeederRegistry.register` decorator.
3. Import your module in `src/yuantus/seeder/__init__.py`.

### Example

```python
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class ProjectDemoSeeder(BaseSeeder):
    """Seeds demo projects."""
    priority = 600  # Run after core data

    def run(self):
        self.log("Generating projects...")
        # Access self.session (SQLAlchemy) and self.fake (Faker)
        # ... logic here ...
```

## 🔢 Execution Priorities

| Range | Layer | Examples |
|-------|-------|----------|
| 0-99 | Core | Users, Tenants, RBAC Roles |
| 100-199 | Schema | ItemTypes (RelationshipTypes optional) |
| 200-299 | Config | Lifecycles, Workflows, Views |
| 500+ | Demo | Items, BOMs, ECOs, Files |

## ⚠️ Notes

- **Idempotency**: All seeders should be idempotent. Use `_ensure_exists` patterns to avoid duplicates on re-runs.
- **Foreign Keys**: Be careful with execution order. Ensure dependencies (e.g., ItemTypes) are seeded before dependents (e.g., Items).
- **Legacy RelationshipTypes**: Seed only when needed by legacy integrations via `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED=true`.
