from unittest.mock import MagicMock, patch

from yuantus.meta_engine.services.product_service import ProductDetailService


def _make_item():
    item = MagicMock()
    item.id = "ITEM-1"
    item.item_type_id = "Part"
    item.state = "released"
    item.owner_id = None
    item.created_by_id = 1
    item.modified_by_id = None
    item.properties = {"item_number": "P-100", "name": "Widget"}
    item.config_id = "CFG-1"
    item.generation = 1
    item.is_current = True
    item.current_version_id = None
    item.created_at = None
    item.updated_at = None
    return item


def test_release_readiness_summary_non_admin_marks_unauthorized():
    session = MagicMock()
    session.get.return_value = _make_item()

    service = ProductDetailService(session, user_id="1", roles=["user"])
    service.permission_service = MagicMock()
    service.permission_service.check_permission.return_value = True

    with patch(
        "yuantus.meta_engine.services.product_service.ReleaseReadinessService.get_item_release_readiness"
    ) as mocked:
        payload = service.get_detail(
            "ITEM-1",
            include_versions=False,
            include_files=False,
            include_release_readiness_summary=True,
            cockpit_links_only=False,
        )

    assert payload["release_readiness_summary"]["authorized"] is False
    mocked.assert_not_called()


def test_impact_summary_bom_denied_marks_unauthorized():
    session = MagicMock()
    session.get.return_value = _make_item()

    service = ProductDetailService(session, user_id="1", roles=["admin"])
    service.permission_service = MagicMock()
    # First call: item get permission; second call: Part BOM permission.
    service.permission_service.check_permission.side_effect = [True, False]

    with patch(
        "yuantus.meta_engine.services.product_service.ImpactAnalysisService.where_used_summary"
    ) as where_used, patch(
        "yuantus.meta_engine.services.product_service.ImpactAnalysisService.baselines_summary"
    ) as baselines, patch(
        "yuantus.meta_engine.services.product_service.ImpactAnalysisService.esign_summary"
    ) as esign:
        payload = service.get_detail(
            "ITEM-1",
            include_versions=False,
            include_files=False,
            include_impact_summary=True,
        )

    assert payload["impact_summary"]["authorized"] is False
    where_used.assert_not_called()
    baselines.assert_not_called()
    esign.assert_not_called()


def test_links_only_skips_heavy_services_for_impact_and_readiness():
    session = MagicMock()
    session.get.return_value = _make_item()

    service = ProductDetailService(session, user_id="1", roles=["admin"])
    service.permission_service = MagicMock()
    # Item get permission + Part BOM permission.
    service.permission_service.check_permission.side_effect = [True, True]

    with patch(
        "yuantus.meta_engine.services.product_service.ImpactAnalysisService.where_used_summary"
    ) as where_used, patch(
        "yuantus.meta_engine.services.product_service.ImpactAnalysisService.baselines_summary"
    ) as baselines, patch(
        "yuantus.meta_engine.services.product_service.ImpactAnalysisService.esign_summary"
    ) as esign, patch(
        "yuantus.meta_engine.services.product_service.ReleaseReadinessService.get_item_release_readiness"
    ) as readiness:
        payload = service.get_detail(
            "ITEM-1",
            include_versions=False,
            include_files=False,
            include_impact_summary=True,
            include_release_readiness_summary=True,
            release_readiness_ruleset_id="readiness",
            cockpit_links_only=True,
        )

    assert payload["cockpit_links"]["cockpit"].endswith("ruleset_id=readiness")
    assert payload["impact_summary"]["authorized"] is True
    assert payload["release_readiness_summary"]["authorized"] is True

    where_used.assert_not_called()
    baselines.assert_not_called()
    esign.assert_not_called()
    readiness.assert_not_called()


def test_where_used_summary_sample_exposes_relationship_quantity_and_uom():
    service = ProductDetailService(MagicMock(), user_id="1", roles=["admin"])

    with patch("yuantus.meta_engine.services.product_service.BOMService") as bom_cls:
        bom_cls.return_value.get_where_used.return_value = [
            {
                "relationship": {"id": "rel-ea"},
                "parent": {
                    "id": "parent-1",
                    "properties": {"item_number": "P-1", "name": "Parent 1"},
                },
                "level": 1,
                "line": {"quantity": 2, "uom": "ea"},
                "line_normalized": {"quantity": 2.0, "uom": "EA"},
            },
            {
                "relationship": {"id": "rel-mm"},
                "parent": {
                    "id": "parent-1",
                    "properties": {"item_number": "P-1", "name": "Parent 1"},
                },
                "level": 1,
                "line": {"quantity": 3, "uom": "mm"},
                "line_normalized": {"quantity": 3.0, "uom": "MM"},
            },
        ]

        result = service._get_where_used_summary(
            "child-1",
            recursive=False,
            max_levels=10,
        )

    assert result["count"] == 2
    assert result["sample"][0]["relationship_id"] == "rel-ea"
    assert result["sample"][0]["quantity"] == 2
    assert result["sample"][0]["uom"] == "EA"
    assert result["sample"][0]["line"] == {"quantity": 2, "uom": "ea"}
    assert result["sample"][1]["relationship_id"] == "rel-mm"
    assert result["sample"][1]["quantity"] == 3
    assert result["sample"][1]["uom"] == "MM"
