from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from yuantus.models.base import Base

# --- Workflow Templates (Definitions) ---


class WorkflowMap(Base):
    """
    Workflow Process Definition (Template)
    e.g. "ECO Approval Process", "New Product Introduction"
    """

    __tablename__ = "meta_workflow_maps"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)

    activities = relationship(
        "WorkflowActivity", back_populates="workflow_map", cascade="all, delete-orphan"
    )
    transitions = relationship(
        "WorkflowTransition",
        back_populates="workflow_map",
        cascade="all, delete-orphan",
    )


class WorkflowActivity(Base):
    """
    Workflow Activity (Node)
    e.g. "Start", "Manager Review", "End"
    """

    __tablename__ = "meta_workflow_activities"

    id = Column(String, primary_key=True)
    workflow_map_id = Column(String, ForeignKey("meta_workflow_maps.id"))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    # Activity Type
    # start, end, activity, auto
    type = Column(String, default="activity")

    # Voting Configuration
    is_voting = Column(Boolean, default=False)

    # Assignment Strategy
    # assignee_type: "role", "user", "dynamic"
    assignee_type = Column(String, default="role")

    # Default Assignment (Role ID)
    role_id = Column(Integer, ForeignKey("rbac_roles.id"), nullable=True)
    # Direct User Assignment
    user_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    # Dynamic: "Owner", "Creator", "Manager"
    dynamic_identity = Column(String, nullable=True)

    # Layout info for UI (JSON)
    ui_data = Column(Text, nullable=True)

    workflow_map = relationship("WorkflowMap", back_populates="activities")

    # Transitions
    transitions_from = relationship(
        "WorkflowTransition",
        foreign_keys="[WorkflowTransition.from_activity_id]",
        back_populates="from_activity",
    )
    transitions_to = relationship(
        "WorkflowTransition",
        foreign_keys="[WorkflowTransition.to_activity_id]",
        back_populates="to_activity",
    )


class WorkflowTransition(Base):
    """
    Workflow Transition (Path)
    e.g. "Review" -> "End" (on "Approve")
    """

    __tablename__ = "meta_workflow_transitions"

    id = Column(String, primary_key=True)
    workflow_map_id = Column(String, ForeignKey("meta_workflow_maps.id"))

    from_activity_id = Column(String, ForeignKey("meta_workflow_activities.id"))
    to_activity_id = Column(String, ForeignKey("meta_workflow_activities.id"))

    # The condition/outcome required to take this path
    # e.g. "Approve", "Reject", "Default"
    condition = Column(String, default="Default")

    # Order for evaluation
    priority = Column(Integer, default=0)

    workflow_map = relationship("WorkflowMap", back_populates="transitions")
    from_activity = relationship(
        "WorkflowActivity",
        foreign_keys=[from_activity_id],
        back_populates="transitions_from",
    )
    to_activity = relationship(
        "WorkflowActivity",
        foreign_keys=[to_activity_id],
        back_populates="transitions_to",
    )


# --- Workflow Runtime (instances) ---


class WorkflowProcess(Base):
    """
    A running instance of a Workflow Map
    """

    __tablename__ = "meta_workflow_processes"

    id = Column(String, primary_key=True)  # UUID
    workflow_map_id = Column(String, ForeignKey("meta_workflow_maps.id"))

    # The Item this process is governing
    item_id = Column(String, ForeignKey("meta_items.id"))

    state = Column(String, default="Active")  # Active, Completed, Cancelled, Error

    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    workflow_map = relationship("WorkflowMap")
    activity_instances = relationship(
        "WorkflowActivityInstance",
        back_populates="process",
        cascade="all, delete-orphan",
    )


class WorkflowActivityInstance(Base):
    """
    An active instance of an activity (Node)
    """

    __tablename__ = "meta_workflow_activity_instances"

    id = Column(String, primary_key=True)  # UUID
    process_id = Column(String, ForeignKey("meta_workflow_processes.id"))
    activity_id = Column(String, ForeignKey("meta_workflow_activities.id"))

    state = Column(String, default="Active")  # Pending, Active, Completed, Closed

    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    process = relationship("WorkflowProcess", back_populates="activity_instances")
    activity = relationship("WorkflowActivity")

    tasks = relationship(
        "WorkflowTask", back_populates="activity_instance", cascade="all, delete-orphan"
    )


class WorkflowTask(Base):
    """
    A generated assignment for a user
    """

    __tablename__ = "meta_workflow_tasks"

    id = Column(String, primary_key=True)  # UUID
    activity_instance_id = Column(
        String, ForeignKey("meta_workflow_activity_instances.id")
    )

    # Assignment Type: "user", "role", "dynamic"
    assignee_type = Column(String, default="user")

    # The specific targets
    assigned_to_user_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    assigned_to_role_id = Column(Integer, ForeignKey("rbac_roles.id"), nullable=True)

    # Snapshot of dynamic rule used (e.g. "Owner")
    dynamic_identity = Column(String, nullable=True)

    status = Column(String, default="Pending")  # Pending, Completed

    # User Vote
    outcome = Column(String, nullable=True)  # "Approve", "Reject"
    comment = Column(Text, nullable=True)

    completed_at = Column(DateTime, nullable=True)

    activity_instance = relationship("WorkflowActivityInstance", back_populates="tasks")
    assigned_user = relationship("yuantus.security.rbac.models.RBACUser")
    assigned_role = relationship("yuantus.security.rbac.models.RBACRole")
