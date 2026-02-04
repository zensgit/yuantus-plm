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


def test_get_detail_includes_bom_obsolete_and_weight_rollup_summaries():
    session = MagicMock()
    session.get.return_value = _make_item()

    service = ProductDetailService(session, user_id="1", roles=["admin"])
    service.permission_service = MagicMock()
    service.permission_service.check_permission.return_value = True

    obsolete_summary = {"count": 1, "sample": [{"child_id": "C-1"}]}
    weight_summary = {"total_weight": 12.5}

    with patch.object(
        service, "_get_bom_obsolete_summary", return_value=obsolete_summary
    ) as mock_obsolete, patch.object(
        service, "_get_bom_weight_rollup_summary", return_value=weight_summary
    ) as mock_weight:
        payload = service.get_detail(
            "ITEM-1",
            include_versions=False,
            include_files=False,
            include_bom_obsolete_summary=True,
            bom_obsolete_recursive=False,
            bom_obsolete_levels=7,
            include_bom_weight_rollup=True,
            bom_weight_levels=4,
            bom_weight_effective_at=None,
            bom_weight_rounding=2,
        )

    assert payload["bom_obsolete_summary"] == obsolete_summary
    assert payload["bom_weight_rollup_summary"] == weight_summary
    mock_obsolete.assert_called_once_with(
        "ITEM-1", recursive=False, max_levels=7
    )
    mock_weight.assert_called_once_with(
        "ITEM-1", levels=4, effective_at=None, rounding=2
    )


def test_get_detail_bom_summaries_mark_unauthorized_when_bom_denied():
    session = MagicMock()
    session.get.return_value = _make_item()

    service = ProductDetailService(session, user_id="1", roles=["admin"])
    service.permission_service = MagicMock()
    service.permission_service.check_permission.side_effect = [True, False]

    with patch.object(service, "_get_bom_obsolete_summary") as mock_obsolete, patch.object(
        service, "_get_bom_weight_rollup_summary"
    ) as mock_weight:
        payload = service.get_detail(
            "ITEM-1",
            include_versions=False,
            include_files=False,
            include_bom_obsolete_summary=True,
            include_bom_weight_rollup=True,
        )

    assert payload["bom_obsolete_summary"]["authorized"] is False
    assert payload["bom_weight_rollup_summary"]["authorized"] is False
    mock_obsolete.assert_not_called()
    mock_weight.assert_not_called()
