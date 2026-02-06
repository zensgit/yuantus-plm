from yuantus.meta_engine.tasks import cad_pipeline_tasks as cpt


def test_preview_meets_min_size_false_for_small_png() -> None:
    small = cpt._create_minimal_png_bytes(256, 256)
    assert cpt._preview_meets_min_size(small, min_size=512) is False


def test_preview_meets_min_size_true_for_large_png() -> None:
    large = cpt._create_minimal_png_bytes(512, 512)
    assert cpt._preview_meets_min_size(large, min_size=512) is True


def test_ensure_preview_min_size_upscales_small_png() -> None:
    small = cpt._create_minimal_png_bytes(256, 256)
    resized = cpt._ensure_preview_min_size(small, min_size=512, label="test")
    width, height = cpt._parse_png_size(resized)
    assert width is not None and height is not None
    assert width >= 512 and height >= 512
