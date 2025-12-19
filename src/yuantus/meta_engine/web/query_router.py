"""
AML Query Router (ADR-007)
增强的 AML 查询 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from yuantus.database import get_db
from yuantus.meta_engine.schemas.aml import AMLQueryRequest, AMLQueryResponse
from yuantus.meta_engine.services.query_service import AMLQueryService

query_router = APIRouter(prefix="/api/aml", tags=["AML Query"])


@query_router.post("/query", response_model=AMLQueryResponse)
def aml_query(
    request: AMLQueryRequest,
    db: Session = Depends(get_db),
):
    """
    增强的 AML 查询接口

    支持:
    - select: 字段选择
    - expand: 关系展开
    - depth: 展开深度
    - where: 条件过滤
    - order_by: 排序
    - 分页

    Example:
    ```json
    {
        "type": "Part",
        "where": {"state": "Released"},
        "select": ["id", "number", "name", "properties.weight"],
        "expand": ["bom_lines", "bom_lines.component"],
        "depth": 3,
        "page": 1,
        "page_size": 50
    }
    ```
    """
    service = AMLQueryService(db)
    return service.query(request)


@query_router.get("/{item_type}/{item_id}")
def get_item(
    item_type: str,
    item_id: str,
    select: Optional[str] = None,
    expand: Optional[str] = None,
    depth: int = 1,
    db: Session = Depends(get_db),
):
    """
    获取单个 Item

    Query Params:
    - select: 逗号分隔的字段列表
    - expand: 逗号分隔的关系列表
    - depth: 展开深度 (默认 1)

    Example: GET /api/aml/Part/123?select=id,number,name&expand=bom_lines,files&depth=2
    """
    service = AMLQueryService(db)

    select_list = select.split(",") if select else None
    expand_list = expand.split(",") if expand else None

    result = service.get_by_id(
        item_type=item_type,
        item_id=item_id,
        select=select_list,
        expand=expand_list,
        depth=depth,
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"{item_type} {item_id} not found")

    return result


@query_router.post("/bom/explode")
def explode_bom(
    item_id: str,
    max_level: int = 10,
    include_properties: bool = False,
    db: Session = Depends(get_db),
):
    """
    BOM 完全展开 (多级)

    返回扁平化的 BOM 结构，包含层级信息
    """
    service = AMLQueryService(db)

    # 使用递归展开
    result = service.get_by_id(
        item_type="Part",
        item_id=item_id,
        expand=["bom_lines.component.bom_lines"],
        depth=max_level,
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    # 扁平化 BOM
    exploded = []
    _flatten_bom(
        result, exploded, level=0, path=[], include_properties=include_properties
    )

    return {
        "root": {
            "id": result["id"],
            "number": result.get("number"),
            "name": result.get("name"),
        },
        "exploded": exploded,
        "total_items": len(exploded),
    }


def _flatten_bom(
    item: Dict[str, Any],
    result: List[Dict[str, Any]],
    level: int,
    path: List[str],
    include_properties: bool,
):
    """递归扁平化 BOM"""
    bom_lines = item.get("bom_lines", [])

    for bl in bom_lines:
        component = bl.get("component")
        if not component:
            continue

        comp_id = component.get("id")
        current_path = path + [comp_id]

        entry = {
            "level": level + 1,
            "path": "/".join(current_path),
            "component_id": comp_id,
            "component_number": component.get("number"),
            "component_name": component.get("name"),
            "quantity": bl.get("quantity"),
            "unit": bl.get("unit"),
            "find_number": bl.get("find_number"),
        }

        if include_properties:
            entry["properties"] = component.get("properties", {})

        result.append(entry)

        # 递归
        _flatten_bom(component, result, level + 1, current_path, include_properties)


@query_router.post("/where-used")
def where_used(
    item_id: str,
    max_level: int = 10,
    db: Session = Depends(get_db),
):
    """
    反向 BOM 查询 (Where Used)

    查找指定零件被哪些父组件使用
    """
    from yuantus.models.bom import BOMLine
    from yuantus.meta_engine.models.item import Item

    result = []
    visited = set()

    def _trace_parents(child_id: str, level: int, path: List[str]):
        if level > max_level or child_id in visited:
            return
        visited.add(child_id)

        # 查找使用此零件的父组件
        parent_lines = (
            db.query(BOMLine).filter(BOMLine.child_product_id == child_id).all()
        )

        for pl in parent_lines:
            parent = db.query(Item).filter(Item.id == pl.parent_product_id).first()
            if not parent:
                continue

            current_path = [parent.id] + path

            result.append(
                {
                    "level": level,
                    "path": "/".join(current_path),
                    "parent_id": parent.id,
                    "parent_number": parent.number,
                    "parent_name": parent.name,
                    "quantity": pl.quantity,
                    "unit": pl.unit,
                }
            )

            # 递归向上
            _trace_parents(parent.id, level + 1, current_path)

    _trace_parents(item_id, 1, [item_id])

    return {
        "item_id": item_id,
        "used_in": result,
        "total_usages": len(result),
    }
