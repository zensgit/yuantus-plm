# DEV_AND_VERIFICATION_NUMBERING_FLOOR_DB_PUSHDOWN_20260421

## 1. 目标

把 `NumberingService._floor_allocated_value()` 从 Python 侧整表扫描下推到数据库聚合，解决当前实现的 O(N) floor 计算问题。

本轮范围只覆盖：

- `src/yuantus/meta_engine/services/numbering_service.py`
- `src/yuantus/meta_engine/tests/test_numbering_service.py`
- 文档索引和本 MD

不改：

- auto-numbering 对外接口
- 编号规则 schema
- 其他 router / service

## 2. 现状问题

旧实现：

```python
rows = (
    self.session.query(Item)
    .filter(Item.item_type_id == item_type_id)
    .all()
)
for row in rows:
    ...
```

问题：

- floor 计算会把同类型所有 `Item` 拉回 Python
- item 数量上来后，生成编号的热路径会随数据量线性变慢
- 对 SQLite/PostgreSQL 这类主路径方言，没有利用数据库原生 `MAX(...)`

## 3. 实现

### 3.1 方言策略

`_floor_allocated_value()` 现在按方言分支：

- `postgresql` / `sqlite`：走 DB 聚合下推
- 其他方言：保留 Python fallback（不扩大本轮风险面）

### 3.2 DB 聚合逻辑

新增 helper：

- `_max_allocated_value_from_db(...)`
- `_numeric_item_number_expr(...)`
- `_json_text(...)`
- `_floor_allocated_value_python(...)`

核心思路：

1. 对 `ITEM_NUMBER_READ_KEYS = ("item_number", "number")` 两个 key 分别做聚合
2. 先把 JSON 字段抽成文本并 `trim`
3. 通过 `substr(...)` 拿到 prefix 后缀
4. 对合法纯数字后缀做 `cast(... as Integer)`
5. 每个 key 做 `MAX(...)`
6. 最后在 Python 侧取两个 key 的最大值

这样仍然保留：

- canonical `item_number`
- legacy `number`

的兼容读取语义，不会把老数据抛掉。

### 3.3 兼容性

SQLite：

- 用 `GLOB '*[^0-9]*'` 的否定条件排除非数字后缀

PostgreSQL：

- 用 regex `^[0-9]+$` 限定合法数字后缀

其他方言：

- 暂不强行推广，仍走原 Python fallback

这保证本轮是“性能增量”，不是“跨所有方言的行为重写”。

## 4. 测试

### 4.1 新增覆盖

在 `test_numbering_service.py` 新增：

1. 非主方言仍走 Python fallback
2. SQLite floor 计算走 DB 聚合，不走 Python scan
3. SQLite generate 路径能利用 DB floor 直接生成下一号

### 4.2 保留覆盖

原有测试继续覆盖：

- apply / generate / rule resolution
- SQLite 并发唯一性
- generic allocation retry
- legacy `number` floor 兼容

## 5. 验证

### 5.1 Focused service + mainline-adjacent regression

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_numbering_service.py \
  src/yuantus/meta_engine/operations/tests/test_add_op.py \
  src/yuantus/meta_engine/operations/tests/test_update_op.py
```

结果：`21 passed in 0.27s`

### 5.2 Doc-index contracts

```bash
/Users/chouhua/Downloads/Github/Yuantus/.venv/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py \
  src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_sorting_contracts.py \
  src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py
```

结果：待本轮执行回填。
结果：`3 passed in 0.02s`

## 6. 结论

本轮把 numbering floor 的主路径从：

- “查出全部 `Item` 再 Python 解析”

收敛成：

- “数据库先做 `MAX(...)`，Python 只负责两路 key 汇总”

收益：

- SQLite / PostgreSQL 主路径不再做整表 scan 回 Python
- `item_number/number` 兼容层保持不变
- 非主方言风险被限制在原有 fallback 内

## 7. 下一步

如果继续沿 Line A 小增量推进，下一条更合理的是：

1. 把这次 PostgreSQL/SQLite 下推再扩到更多方言
2. 或回到更高 ROI 的功能线，而不是继续在 numbering 上做微优化

本轮已经足够作为独立 bounded increment 提交。
