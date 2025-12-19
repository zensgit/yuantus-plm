from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class AMLAction(str, Enum):
    add = "add"
    delete = "delete"
    update = "update"
    get = "get"
    promote = "promote"  # 推进生命周期
    dummy = "dummy"


class GenericItem(BaseModel):
    """
    AML (Adaptive Markup Language) 核心交互对象
    类似于 Aras 的 XML，但用 JSON。
    """

    type: str = Field(..., description="ItemType Name, e.g. 'Part'")
    action: AMLAction = Field(default=AMLAction.get)
    id: Optional[str] = None

    # 动态属性 (Properties)
    properties: Optional[Dict[str, Any]] = {}

    # 嵌套关系 (Deep Insert/Update)
    # e.g. Creating a Part with its BOM in one request
    relationships: Optional[List["GenericItem"]] = []

    class Config:
        populate_by_name = True


class AMLQueryRequest(BaseModel):
    """
    增强的 AML 查询请求 (ADR-007)
    支持 select/expand/depth 能力
    """

    type: str = Field(..., description="ItemType Name, e.g. 'Part'")
    action: AMLAction = Field(default=AMLAction.get)
    id: Optional[str] = None

    # 查询条件
    where: Optional[Dict[str, Any]] = Field(
        default=None, description="Query conditions, e.g. {'state': 'Released'}"
    )

    # 字段选择 (解决 over-fetching)
    select: Optional[List[str]] = Field(
        default=None,
        description="Fields to return, e.g. ['id', 'number', 'properties.weight']",
    )

    # 关系展开 (解决 N+1)
    expand: Optional[List[str]] = Field(
        default=None,
        description="Relations to expand, e.g. ['bom_lines', 'bom_lines.component']",
    )

    # 展开深度控制
    depth: Optional[int] = Field(
        default=1, ge=1, le=10, description="Max expansion depth for relations"
    )

    # 分页
    page: Optional[int] = Field(default=1, ge=1, description="Page number")
    page_size: Optional[int] = Field(
        default=50, ge=1, le=1000, description="Items per page"
    )

    # 排序
    order_by: Optional[List[str]] = Field(
        default=None, description="Sort fields, e.g. ['created_at:desc', 'name:asc']"
    )

    class Config:
        populate_by_name = True


class AMLQueryResponse(BaseModel):
    """AML 查询响应"""

    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count without pagination")
    page: int = Field(default=1)
    page_size: int = Field(default=50)
    has_more: bool = Field(default=False)
