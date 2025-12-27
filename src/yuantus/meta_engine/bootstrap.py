from __future__ import annotations

"""
Meta Engine bootstrap helpers.

SQLAlchemy only creates tables for models that have been imported (registered) in the
metadata. In early-stage/dev workflows we use `create_all()`, so we need an explicit
import surface to ensure all core models are registered consistently for API + CLI.
"""


def import_all_models() -> None:
    # Core
    from yuantus.meta_engine.models import eco as _eco  # noqa: F401
    from yuantus.meta_engine.models import effectivity as _effectivity  # noqa: F401
    from yuantus.meta_engine.models import file as _file  # noqa: F401
    from yuantus.meta_engine.models import index as _index  # noqa: F401
    from yuantus.meta_engine.models import item as _item  # noqa: F401
    from yuantus.meta_engine.models import job as _job  # noqa: F401
    from yuantus.meta_engine.models import meta_schema as _meta_schema  # noqa: F401
    from yuantus.meta_engine.models import baseline as _baseline  # noqa: F401

    # Subsystems
    from yuantus.meta_engine.app_framework import models as _app_framework  # noqa: F401
    from yuantus.meta_engine.business_logic import models as _business_logic  # noqa: F401
    from yuantus.meta_engine.lifecycle import models as _lifecycle  # noqa: F401
    from yuantus.meta_engine.permission import models as _permission  # noqa: F401
    from yuantus.meta_engine.relationship import models as _relationship  # noqa: F401
    from yuantus.meta_engine.version import models as _version  # noqa: F401
    from yuantus.meta_engine.workflow import models as _workflow  # noqa: F401

    # UI / Views
    from yuantus.meta_engine.views import mapping as _view_mapping  # noqa: F401
    from yuantus.meta_engine.views import models as _views  # noqa: F401
