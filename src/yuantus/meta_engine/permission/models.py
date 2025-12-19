from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from yuantus.models.base import Base


class Permission(Base):
    """
    权限集定义 (Permission Set)
    e.g. "Part Engineering Access", "World Read Only"
    """

    __tablename__ = "meta_permissions"
    id = Column(String, primary_key=True)
    name = Column(String)

    accesses = relationship(
        "Access", back_populates="permission", cascade="all, delete-orphan"
    )


class Access(Base):
    """
    访问控制条目 (Access Control Entry)
    定义 "谁" 在 "这个权限集" 下能 "做什么"
    """

    __tablename__ = "meta_access"
    id = Column(String, primary_key=True)
    permission_id = Column(String, ForeignKey("meta_permissions.id"))

    identity_id = Column(String)  # User ID or Group ID (Alias Identity)

    can_create = Column(Boolean, default=False)
    can_get = Column(Boolean, default=False)
    can_update = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_discover = Column(Boolean, default=False)  # 能看到 ID 但看不到属性 (No Read)

    permission = relationship("Permission", back_populates="accesses")
