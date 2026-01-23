from .base import BaseSeeder
from .registry import SeederRegistry

# Import sub-modules to ensure they register themselves when 'seeder' is imported
# Order here doesn't determine execution order (priority does), but importing is required.

# Core (Priority 0-100)
from .core import users

# Meta (Priority 100-500)
from .meta import lifecycles
from .meta import schemas

# Demo (Priority 500+)
from .demo import items
