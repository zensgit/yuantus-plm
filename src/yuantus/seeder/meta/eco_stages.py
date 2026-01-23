import uuid
from yuantus.meta_engine.models.eco import ECOStage
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class MetaECOStageSeeder(BaseSeeder):
    """Seeds standard ECO workflow stages."""
    priority = 250  # After standard Lifecycle (200)

    def run(self):
        # 1. Draft
        self._ensure_stage("stage_eco_draft", "Draft", seq=10)

        # 2. In Review (Requires Approval)
        self._ensure_stage(
            "stage_eco_review",
            "In Review",
            seq=20,
            approval_type="mandatory",
            min_approvals=1
        )

        # 3. CCB Review (Blocking)
        self._ensure_stage(
            "stage_eco_ccb",
            "CCB Review",
            seq=30,
            approval_type="mandatory",
            is_blocking=True,
            description="Change Control Board Review"
        )

        # 4. Completed
        self._ensure_stage(
            "stage_eco_done",
            "Completed",
            seq=40,
            fold=True
        )

    def _ensure_stage(self, id, name, seq, **kwargs):
        stage = self.session.query(ECOStage).filter_by(id=id).first()
        if not stage:
            stage = ECOStage(
                id=id,
                name=name,
                sequence=seq,
                **kwargs
            )
            self.session.add(stage)
            self.log(f"Created ECO Stage: {name}")
        return stage
