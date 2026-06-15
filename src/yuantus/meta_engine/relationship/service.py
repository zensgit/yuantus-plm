"""
Relationship Service
关系管理服务
Phase 3.2
"""

from collections import deque
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item  # Item model for relationship edges.
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.item_number_keys import get_item_number

# WP1.2 traversal cost bound. The path-based cycle guard stops cycles but NOT
# shared-part (diamond) path explosion -- a part reachable via K ancestor paths is
# expanded K times, which stacks multiplicatively and can blow up memory/latency
# on heavily-shared BOMs. max_depth caps depth only, not breadth, so we also cap
# the total expanded node count and fail loud (-> 422) rather than OOM. Flat
# projection is computed directly below so it no longer materializes this
# duplicate-preserving tree first.
MAX_TRAVERSAL_NODES = 50_000


class TraversalBudgetError(Exception):
    """Raised when relationship-tree expansion exceeds MAX_TRAVERSAL_NODES."""


class RelationshipService:
    """关系管理服务"""

    def __init__(self, session: Session):
        self.session = session
        self._relationship_item_type_cache: Dict[str, ItemType] = {}

    def _resolve_relationship_type(
        self, name: str
    ) -> tuple[None, ItemType]:
        item_type = (
            self.session.query(ItemType)
            .filter((ItemType.id == name) | (ItemType.label == name))
            .first()
        )
        if item_type and item_type.is_relationship:
            cached = self._relationship_item_type_cache.get(item_type.id)
            if cached is not None:
                return None, cached
            self._relationship_item_type_cache[item_type.id] = item_type
            return None, item_type

        if item_type:
            raise ValueError(f"{name} is not a relationship ItemType")
        raise ValueError(
            f"Unknown relationship type: {name}. "
            "Only ItemType.is_relationship relationships are supported."
        )

    def create_relationship(
        self,
        source_id: str,  # Item IDs are string
        related_id: str,  # Item IDs are string
        relationship_type_name: str,  # Changed from relationship_type to relationship_type_name to avoid confusion
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Item:
        """
        创建关系

        Args:
            source_id: 源Item ID
            related_id: 目标Item ID
            relationship_type_name: 关系类型名称
            properties: 关系属性
            user_id: 创建者

        Returns:
            创建的关系实例
        """
        rel_type, rel_item_type = self._resolve_relationship_type(relationship_type_name)

        source_type_id = (
            rel_type.source_item_type
            if rel_type
            else rel_item_type.source_item_type_id
        )
        related_type_id = (
            rel_type.related_item_type
            if rel_type
            else rel_item_type.related_item_type_id
        )
        is_polymorphic = rel_type.is_polymorphic if rel_type else False
        max_quantity = rel_type.max_quantity if rel_type else None

        # 验证源和目标类型
        source = self.session.get(Item, source_id)
        related = self.session.get(Item, related_id)

        if not source or not related:
            raise ValueError("Source or related item not found")

        if source_type_id and source.item_type_id != source_type_id:
            raise ValueError(
                f"Source type mismatch: expected {source_type_id}, "
                f"got {source.item_type_id}"
            )

        # Handle polymorphic relationships
        if not is_polymorphic and related_type_id:
            if related.item_type_id != related_type_id:
                raise ValueError(
                    f"Related type mismatch: expected {related_type_id}, "
                    f"got {related.item_type_id}"
                )
        # If polymorphic, we might need a more complex check here,
        # e.g., checking inheritance tree, but for now strict type or no check.

        # 检查数量限制
        if max_quantity is not None:
            existing_count = (
                self.session.query(Item)
                .filter(
                    Item.source_id == source_id,
                    Item.item_type_id == rel_item_type.id,
                    Item.is_current.is_(True),
                )
                .count()
            )

            if existing_count >= max_quantity:
                raise ValueError(
                    f"Max relationship quantity ({max_quantity}) exceeded"
                )

        # 创建关系 (关系即 Item)
        import uuid

        relationship = Item(
            id=str(uuid.uuid4()),
            item_type_id=rel_item_type.id,
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            source_id=source_id,
            related_id=related_id,
            properties=properties or {},
            created_by_id=user_id,
            permission_id=source.permission_id,
        )

        self.session.add(relationship)
        self.session.flush()  # Flush to get ID for newly created relationship (Item)

        return relationship

    def get_relationships(
        self,
        item_id: str,  # Item IDs are string
        direction: str = "outgoing",  # outgoing|incoming|both
        relationship_type_name: Optional[
            str
        ] = None,  # Changed to relationship_type_name
    ) -> List[Item]:
        """
        获取Item的关系

        Args:
            item_id: Item ID
            direction: 关系方向
            relationship_type_name: 可选的关系类型过滤

        Returns:
            关系列表
        """
        query = self.session.query(Item).filter(Item.is_current.is_(True))

        if direction == "outgoing":
            query = query.filter(Item.source_id == item_id)
        elif direction == "incoming":
            query = query.filter(Item.related_id == item_id)
        else:  # both
            query = query.filter(
                (Item.source_id == item_id) | (Item.related_id == item_id)
            )

        if relationship_type_name:
            _, rel_item_type = self._resolve_relationship_type(relationship_type_name)
            query = query.filter(Item.item_type_id == rel_item_type.id)

        return query.order_by(Item.created_at.asc()).all()

    def get_bom_tree(
        self, part_id: str, max_depth: int = 10  # Item IDs are string
    ) -> Dict[str, Any]:
        """
        获取BOM树结构

        Args:
            part_id: Part Item ID
            max_depth: 最大递归深度

        Returns:
            树形结构字典
        """
        return self._build_tree(part_id, "Part BOM", max_depth, 0)

    def _build_tree(
        self,
        item_id: str,  # Item IDs are string
        rel_type_name: str,  # Changed to rel_type_name
        max_depth: int,
        current_depth: int,
    ) -> Dict[str, Any]:
        """递归构建树"""
        item = self.session.get(Item, item_id)
        if not item:
            return {}

        node = {
            "id": item.id,
            "item_type": item.item_type_id,  # Use item_type_id
            "name": item.to_dict().get("name"),  # Use to_dict to get properties
            "children": [],
        }

        if current_depth >= max_depth:
            return node

        # 获取子关系
        relationships = self.get_relationships(
            item_id, direction="outgoing", relationship_type_name=rel_type_name
        )

        for rel in relationships:
            child_node = self._build_tree(
                rel.related_id, rel_type_name, max_depth, current_depth + 1
            )
            # Access properties directly from relationship.properties
            child_node["quantity"] = (
                rel.properties.get("quantity", 1) if rel.properties else 1
            )
            child_node["relationship_id"] = rel.id
            node["children"].append(child_node)

        return node

    # ------------------------------------------------------------------
    # WP1.2 PDM traversal (ASSEMBLY/REFERENCE, Part<->Part).
    # Locked contract: DEVELOPMENT_WP1_2_PDM_TRAVERSAL_AND_STALE_DRAWINGS_TASKBOOK.
    # The traversal returns rows/nodes that explicitly distinguish the edge
    # (relationship_id) from the counterpart item (item_id) -- the edge IS an Item.
    # ------------------------------------------------------------------
    ASSEMBLY = "ASSEMBLY"
    REFERENCE = "REFERENCE"
    MAX_DEPTH_CAP = 50

    def _item_summary(self, item_id: str) -> Dict[str, Any]:
        item = self.session.get(Item, item_id)
        if not item:
            return {
                "item_id": item_id,
                "item_type_id": None,
                "item_number": None,
                "name": None,
            }
        props = item.properties or {}
        return {
            "item_id": item.id,
            "item_type_id": item.item_type_id,
            "item_number": get_item_number(props),
            "name": props.get("name"),
        }

    def get_item_relationships(
        self,
        item_id: str,
        kind: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List[Dict[str, Any]]:
        """One-level relationships. Each row keeps the edge id (relationship_id)
        distinct from the counterpart item id. ``kind=None`` returns only the PDM
        kinds (ASSEMBLY + REFERENCE) -- not every is_relationship type (e.g. it
        excludes ``Part BOM``), since this is a /pdm surface."""
        kinds = [kind] if kind else [self.ASSEMBLY, self.REFERENCE]
        edges: List[Item] = []
        seen_edges: set = set()
        for k in kinds:
            for edge in self.get_relationships(
                item_id, direction=direction, relationship_type_name=k
            ):
                if edge.id not in seen_edges:
                    seen_edges.add(edge.id)
                    edges.append(edge)
        rows: List[Dict[str, Any]] = []
        for edge in edges:
            # Per-edge counterpart (correct even when direction == "both").
            if edge.source_id == item_id:
                counterpart_id = edge.related_id
                counterpart_direction = "outgoing"
            else:
                counterpart_id = edge.source_id
                counterpart_direction = "incoming"
            cp = self._item_summary(counterpart_id)
            rows.append(
                {
                    "relationship_id": edge.id,
                    "relationship_kind": edge.item_type_id,
                    "source_id": edge.source_id,
                    "related_id": edge.related_id,
                    "counterpart_item_id": cp["item_id"],
                    "counterpart_direction": counterpart_direction,
                    "counterpart_item_type_id": cp["item_type_id"],
                    "counterpart_item_number": cp["item_number"],
                    "counterpart_name": cp["name"],
                    "properties": edge.properties or {},
                }
            )
        return rows

    def get_relationship_tree(
        self,
        root_id: str,
        kinds: Optional[List[str]] = None,
        max_depth: int = 10,
        projection: str = "tree",
        max_nodes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Recursive containment tree (default ASSEMBLY). Path-based cycle guard;
        root is included. projection='flat' dedupes by item (occurrence_count).
        Raises TraversalBudgetError if tree expansion exceeds ``max_nodes``
        (shared-part explosion bound; default MAX_TRAVERSAL_NODES, resolved at
        call time). Flat projection does not build the duplicate tree and does not
        consume this tree-node budget."""
        kinds = tuple(kinds) if kinds else (self.ASSEMBLY,)
        if projection == "flat":
            return self._build_flat_projection(root_id, kinds, max_depth)
        budget = max_nodes if max_nodes is not None else MAX_TRAVERSAL_NODES
        state = {"count": 0, "max": budget}
        root_node = self._build_node(
            root_id, kinds, max_depth, state=state, depth=0, path=[], rel_path=[], via=None
        )
        return {
            "root_id": root_id,
            "max_depth": max_depth,
            "projection": "tree",
            "tree": root_node,
        }

    def _build_flat_projection(
        self,
        root_id: str,
        kinds,
        max_depth: int,
    ) -> Dict[str, Any]:
        """Direct, **bounded** flat projection -- no duplicate-tree materialization
        and (unlike the prior version) no per-path enumeration.

        ``occurrence_count`` is the number of distinct non-cycle relationship-edge
        paths from the root to an item with length ``<= max_depth``. It is computed by
        a memoized topological dynamic program (``count(v) += count(u)`` per edge
        ``u -> v``, depth-stratified), NOT by materializing each path. A heavily-shared
        diamond whose *path count* is exponential (e.g. a 20-deep stacked diamond has
        2**20 paths) is therefore still ``O(V * max_depth + E)`` in time and memory.
        This is why flat -- unlike the duplicate-preserving tree -- neither needs nor
        consumes the ``max_nodes`` tree-node budget: it returns the deduped item set
        even where the tree projection would raise ``TraversalBudgetError``.

        Three linear passes:
        1. shortest-first BFS -> reachable set, ``min_depth`` / ``first_path`` /
           ``first_relationship_path`` (first discovery wins), and recorded adjacency;
        2. a DFS that drops back-edges (an edge to an ancestor still on the current
           DFS path -- the path-based cycle rule) to yield a DAG + finish order;
        3. depth-stratified DP over that DAG in topological order, capping path length
           at ``max_depth``. Parallel edges between the same pair are counted as
           distinct occurrences (the DP iterates edges, not unique parents).
        """
        edge_cache: Dict[str, List[Item]] = {}

        def _edges(item_id: str) -> List[Item]:
            cached = edge_cache.get(item_id)
            if cached is not None:
                return cached
            edges: List[Item] = []
            for kind in kinds:
                edges.extend(
                    self.get_relationships(
                        item_id,
                        direction="outgoing",
                        relationship_type_name=kind,
                    )
                )
            edge_cache[item_id] = edges
            return edges

        # --- Pass 1: shortest-first BFS -> metadata + reachable set + adjacency. ---
        meta: Dict[str, Dict[str, Any]] = {
            root_id: {
                "min_depth": 0,
                "first_path": [root_id],
                "first_relationship_path": [],
            }
        }
        order: List[str] = [root_id]
        adjacency: Dict[str, List[tuple]] = {}
        expanded: set = set()
        queue = deque([(root_id, 0)])
        while queue:
            item_id, depth = queue.popleft()
            if item_id in expanded:
                continue
            expanded.add(item_id)
            if depth >= max_depth:
                adjacency[item_id] = []
                continue
            parent_meta = meta[item_id]
            out_edges: List[tuple] = []
            for edge in _edges(item_id):
                child_id = edge.related_id
                out_edges.append((child_id, edge.id))
                if child_id not in meta:
                    meta[child_id] = {
                        "min_depth": depth + 1,
                        "first_path": parent_meta["first_path"] + [child_id],
                        "first_relationship_path": (
                            parent_meta["first_relationship_path"] + [edge.id]
                        ),
                    }
                    order.append(child_id)
                if child_id not in expanded:
                    queue.append((child_id, depth + 1))
            adjacency[item_id] = out_edges

        # --- Pass 2: DFS dropping back-edges (to a GRAY ancestor) -> DAG + finish order. ---
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {node: WHITE for node in meta}
        dag: Dict[str, List[tuple]] = {node: [] for node in meta}
        finish: List[str] = []
        color[root_id] = GRAY
        dfs_stack = [(root_id, iter(adjacency.get(root_id, [])))]
        while dfs_stack:
            node, edge_iter = dfs_stack[-1]
            descended = False
            for child_id, edge_id in edge_iter:
                if color[child_id] == GRAY:
                    continue  # back-edge to an ancestor -> path-based cycle, drop it
                dag[node].append((child_id, edge_id))
                if color[child_id] == WHITE:
                    color[child_id] = GRAY
                    dfs_stack.append((child_id, iter(adjacency.get(child_id, []))))
                    descended = True
                    break
                # BLACK: a finished node reached by a cross/forward edge -> keep, no descent.
            if not descended:
                color[node] = BLACK
                finish.append(node)
                dfs_stack.pop()

        # --- Pass 3: depth-stratified DP over the DAG (reverse finish == topological). ---
        # counts[v][d] = number of length-d non-cycle paths root -> v (capped <= max_depth).
        counts: Dict[str, Dict[int, int]] = {node: {} for node in meta}
        counts[root_id] = {0: 1}
        for node in reversed(finish):
            node_counts = counts[node]
            if not node_counts:
                continue
            for child_id, _edge_id in dag[node]:
                child_counts = counts[child_id]
                for length, paths in node_counts.items():
                    nxt = length + 1
                    if nxt > max_depth:
                        continue
                    child_counts[nxt] = child_counts.get(nxt, 0) + paths

        items: List[Dict[str, Any]] = []
        for item_id in order:
            occurrence = sum(counts[item_id].values())
            if occurrence == 0:
                continue  # only reachable via paths longer than max_depth
            info = meta[item_id]
            summary = self._item_summary(item_id)
            items.append(
                {
                    "item_id": summary["item_id"],
                    "item_type_id": summary["item_type_id"],
                    "item_number": summary["item_number"],
                    "name": summary["name"],
                    "occurrence_count": occurrence,
                    "min_depth": info["min_depth"],
                    "first_path": info["first_path"],
                    "first_relationship_path": info["first_relationship_path"],
                }
            )

        return {
            "root_id": root_id,
            "max_depth": max_depth,
            "projection": "flat",
            "items": items,
        }

    def _build_node(
        self,
        item_id: str,
        kinds,
        max_depth: int,
        *,
        state: Dict[str, int],
        depth: int,
        path: List[str],
        rel_path: List[str],
        via: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        state["count"] += 1
        if state["count"] > state["max"]:
            raise TraversalBudgetError(
                f"relationship-tree expansion exceeded {state['max']} nodes; "
                f"narrow max_depth (heavy part-sharing expands multiplicatively)"
            )
        node = {
            **self._item_summary(item_id),
            "depth": depth,
            "path": path + [item_id],
            "relationship_path": list(rel_path),
            "cycle": False,
            "via_relationship": via,
            "children": [],
        }
        # Path-based cycle guard: only an ANCESTOR reappearing is a cycle (a shared
        # part in two different branches is legitimate and kept).
        if item_id in path:
            node["cycle"] = True
            return node
        if depth >= max_depth:
            return node
        for kind in kinds:
            for edge in self.get_relationships(
                item_id, direction="outgoing", relationship_type_name=kind
            ):
                props = edge.properties or {}
                child_via = {
                    "relationship_id": edge.id,
                    "relationship_kind": edge.item_type_id,
                    "source_id": edge.source_id,
                    "related_id": edge.related_id,
                    "quantity": props.get("quantity"),
                    "uom": props.get("uom"),
                    "position": props.get("position") or props.get("find_num"),
                    "properties": props,
                }
                node["children"].append(
                    self._build_node(
                        edge.related_id,
                        kinds,
                        max_depth,
                        state=state,
                        depth=depth + 1,
                        path=path + [item_id],
                        rel_path=rel_path + [edge.id],
                        via=child_via,
                    )
                )
        return node

    def _flatten_node(
        self, node: Dict[str, Any], agg: Dict[str, Dict[str, Any]], order: List[str]
    ) -> None:
        # Cycle nodes are not counted (their item already has a non-cycle occurrence).
        if not node.get("cycle"):
            iid = node["item_id"]
            entry = agg.get(iid)
            if entry is None:
                agg[iid] = {
                    "item_id": iid,
                    "item_type_id": node["item_type_id"],
                    "item_number": node["item_number"],
                    "name": node["name"],
                    "occurrence_count": 1,
                    "min_depth": node["depth"],
                    "first_path": list(node["path"]),
                    "first_relationship_path": list(node["relationship_path"]),
                }
                order.append(iid)
            else:
                entry["occurrence_count"] += 1
                entry["min_depth"] = min(entry["min_depth"], node["depth"])
        for child in node.get("children", []):
            self._flatten_node(child, agg, order)

    def get_reachable_items(
        self,
        root_id: str,
        kinds: Optional[List[str]] = None,
        max_depth: int = 10,
    ) -> List[Dict[str, Any]]:
        """Bounded O(V+E) unique-item reachability from ``root_id`` via the given
        containment kinds within ``max_depth`` (root included). Uses a visited-set
        BFS, so -- unlike ``get_relationship_tree`` -- it does NOT re-expand shared
        parts and cannot blow up on diamond-heavy assemblies. First discovery is
        shortest-path (BFS), so ``min_depth``/``first_path`` are the shortest. This
        is the safe basis for whole-assembly scans (e.g. stale-drawings)."""
        from collections import deque

        kinds = tuple(kinds) if kinds else (self.ASSEMBLY,)
        result: Dict[str, Dict[str, Any]] = {}
        enqueued = {root_id}
        queue = deque([(root_id, 0, [root_id], [])])
        while queue:
            item_id, depth, path, rel_path = queue.popleft()
            result[item_id] = {
                **self._item_summary(item_id),
                "min_depth": depth,
                "first_path": list(path),
                "first_relationship_path": list(rel_path),
            }
            if depth >= max_depth:
                continue
            for kind in kinds:
                for edge in self.get_relationships(
                    item_id, direction="outgoing", relationship_type_name=kind
                ):
                    child = edge.related_id
                    if child not in enqueued:  # visited-set: each item once (cycle/shared-safe)
                        enqueued.add(child)
                        queue.append(
                            (child, depth + 1, path + [child], rel_path + [edge.id])
                        )
        return list(result.values())
