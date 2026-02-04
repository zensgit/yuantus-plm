from yuantus.meta_engine.lifecycle.models import LifecycleMap, LifecycleState, LifecycleTransition
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class LifecycleSeeder(BaseSeeder):
    """Seeds standard lifecycle maps."""
    priority = 200  # Meta priority

    def run(self):
        # 1. Standard Part Lifecycle
        lc_map = self._ensure_lifecycle(
            id="lc_part_std",
            name="Standard Part Lifecycle",
            description="Default lifecycle for parts: Draft -> Review -> Released -> Suspended -> Obsolete"
        )

        # 2. States
        # Note: IDs are constructed as {lifecycle_id}_{state_name} for uniqueness
        s_draft = self._ensure_state(lc_map, "draft", "Draft", is_start=True, seq=10)
        s_review = self._ensure_state(lc_map, "review", "In Review", lock=True, seq=20)
        s_released = self._ensure_state(lc_map, "released", "Released", is_released=True, lock=True, seq=30)
        s_suspended = self._ensure_state(lc_map, "suspended", "Suspended", lock=True, seq=35)
        s_obsolete = self._ensure_state(lc_map, "obsolete", "Obsolete", is_end=True, lock=True, seq=40)

        # 3. Transitions
        self._ensure_transition(lc_map, s_draft, s_review, "submit")
        self._ensure_transition(lc_map, s_review, s_released, "approve")
        self._ensure_transition(lc_map, s_released, s_suspended, "suspend")
        self._ensure_transition(lc_map, s_suspended, s_released, "resume")
        self._ensure_transition(lc_map, s_suspended, s_obsolete, "obsolete")
        self._ensure_transition(lc_map, s_released, s_obsolete, "obsolete")

    def _ensure_lifecycle(self, id: str, name: str, description: str):
        lc = self.session.query(LifecycleMap).filter_by(id=id).first()
        if not lc:
            lc = LifecycleMap(id=id, name=name, description=description)
            self.session.add(lc)
            self.log(f"Created LifecycleMap: {name}")
        return lc

    def _ensure_state(self, lc_map, id_suffix, name, is_start=False, is_end=False, is_released=False, lock=False, seq=0):
        full_id = f"{lc_map.id}_{id_suffix}"
        state = self.session.query(LifecycleState).filter_by(id=full_id).first()
        if not state:
            state = LifecycleState(
                id=full_id,
                lifecycle_map_id=lc_map.id,
                name=name,       # Use display name as internal name for now, or split if needed
                label=name,      # Display label
                sequence=seq,
                is_start_state=is_start,
                is_end_state=is_end,
                is_released=is_released,
                version_lock=lock
            )
            self.session.add(state)
            self.log(f"Created State: {name}")
        return state

    def _ensure_transition(self, lc_map, from_state, to_state, action):
        trans_id = f"{from_state.id}_to_{to_state.id}"
        trans = self.session.query(LifecycleTransition).filter_by(id=trans_id).first()
        if not trans:
            trans = LifecycleTransition(
                id=trans_id,
                lifecycle_map_id=lc_map.id,
                from_state_id=from_state.id,
                to_state_id=to_state.id,
                action_name=action
            )
            self.session.add(trans)
            self.log(f"Created Transition: {from_state.label} -> {to_state.label}")
