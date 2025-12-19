from sqlalchemy import Column, String, Integer, ForeignKey
from yuantus.models.base import Base


class ViewMapping(Base):
    """
    视图映射表：连接 ItemType 和 Form/Grid
    决定 "什么角色" 在 "什么设备" 上看 "什么类型的对象" 用 "哪个表单"
    Aras 的核心 View 逻辑
    """

    __tablename__ = "meta_view_mappings"
    id = Column(String, primary_key=True)

    item_type_id = Column(String, ForeignKey("meta_item_types.id"))

    # 映射目标
    form_id = Column(String, ForeignKey("meta_forms.id"), nullable=True)
    grid_view_id = Column(String, ForeignKey("meta_grid_views.id"), nullable=True)

    # 过滤条件 (Context)
    identity_id = Column(
        String, nullable=True
    )  # 特定角色看特定表单 (Vendor vs Engineer)
    device_type = Column(String, default="desktop")  # desktop, mobile

    # 优先级
    sort_order = Column(Integer, default=0)
