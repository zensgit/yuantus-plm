from unittest.mock import MagicMock

from yuantus.meta_engine.services.report_service import ReportService


def _child(rel_id, child_id, qty, *, uom=None, name=None, children=None):
    props = {"quantity": qty}
    if uom is not None:
        props["uom"] = uom
    return {
        "relationship": {"id": rel_id, "properties": props},
        "child": {
            "id": child_id,
            "properties": {"name": name or child_id},
            "children": children or [],
        },
    }


def test_flatten_bom_keeps_same_child_different_uom_separate():
    service = ReportService(MagicMock())
    tree = {
        "id": "root",
        "children": [
            _child("rel-ea", "child-1", 2, uom="ea", name="Bolt"),
            _child("rel-mm", "child-1", 100, uom="mm", name="Bolt"),
        ],
    }

    result = service._flatten_bom(tree)

    assert result["child-1::EA"] == {
        "id": "child-1",
        "name": "Bolt",
        "qty": 2.0,
        "uom": "EA",
    }
    assert result["child-1::MM"] == {
        "id": "child-1",
        "name": "Bolt",
        "qty": 100.0,
        "uom": "MM",
    }


def test_flatten_bom_merges_same_normalized_uom_bucket():
    service = ReportService(MagicMock())
    tree = {
        "id": "root",
        "children": [
            _child("rel-1", "child-1", 2, uom=" ea ", name="Bolt"),
            _child("rel-2", "child-1", 3, uom="EA", name="Bolt"),
        ],
    }

    result = service._flatten_bom(tree)

    assert list(result) == ["child-1::EA"]
    assert result["child-1::EA"]["qty"] == 5.0
    assert result["child-1::EA"]["uom"] == "EA"


def test_flatten_bom_defaults_missing_uom_to_ea():
    service = ReportService(MagicMock())
    tree = {"id": "root", "children": [_child("rel-1", "child-1", 2, name="Bolt")]}

    result = service._flatten_bom(tree)

    assert result["child-1::EA"]["uom"] == "EA"


def test_get_flattened_bom_returns_uom_without_changing_legacy_fields():
    service = ReportService(MagicMock())
    service.bom_service = MagicMock()
    service.bom_service.get_bom_structure.return_value = {
        "id": "root",
        "children": [
            _child("rel-ea", "child-1", 2, uom="EA", name="Bolt"),
            _child("rel-mm", "child-1", 100, uom="MM", name="Bolt"),
        ],
    }

    result = service.get_flattened_bom("root")

    assert result == [
        {"id": "child-1", "name": "Bolt", "total_quantity": 2.0, "uom": "EA"},
        {"id": "child-1", "name": "Bolt", "total_quantity": 100.0, "uom": "MM"},
    ]


def test_generate_bom_comparison_reports_uom_buckets_separately():
    service = ReportService(MagicMock())
    service.bom_service = MagicMock()
    service.bom_service.get_bom_structure.side_effect = [
        {
            "id": "bom-a",
            "children": [
                _child("a-ea", "child-1", 2, uom="EA", name="Bolt"),
                _child("a-mm", "child-1", 100, uom="MM", name="Bolt"),
            ],
        },
        {
            "id": "bom-b",
            "children": [
                _child("b-ea", "child-1", 3, uom="EA", name="Bolt"),
                _child("b-kg", "child-1", 1, uom="KG", name="Bolt"),
            ],
        },
    ]

    result = service.generate_bom_comparison("bom-a", "bom-b")

    differences = sorted(result["differences"], key=lambda row: row["bucket_key"])
    assert result["stats"] == {"added": 1, "removed": 1, "modified": 1, "unchanged": 0}
    assert differences == [
        {
            "id": "child-1",
            "bucket_key": "child-1::EA",
            "name": "Bolt",
            "uom": "EA",
            "status": "modified",
            "old_qty": 2.0,
            "new_qty": 3.0,
            "delta": 1.0,
        },
        {
            "id": "child-1",
            "bucket_key": "child-1::KG",
            "name": "Bolt",
            "uom": "KG",
            "status": "added",
            "new_qty": 1.0,
        },
        {
            "id": "child-1",
            "bucket_key": "child-1::MM",
            "name": "Bolt",
            "uom": "MM",
            "status": "removed",
            "old_qty": 100.0,
        },
    ]
