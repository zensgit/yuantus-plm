from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from yuantus.meta_engine.services.cad_converter_service import (
    CADConverterService,
    _FREECAD_PARAMS_ENV_VAR,
)


def _make_service(tmp_path: Path) -> CADConverterService:
    with patch.object(
        CADConverterService, "_find_freecad", return_value="/usr/bin/FreeCADCmd"
    ):
        return CADConverterService(MagicMock(), vault_base_path=str(tmp_path / "vault"))


def _make_source_file(filename: str) -> SimpleNamespace:
    return SimpleNamespace(
        id="src-1",
        filename=filename,
        system_path="inputs/source.step",
        vault_id=None,
        get_extension=lambda: "step",
    )


def test_freecad_convert_uses_params_file_and_sanitized_output_names(tmp_path):
    service = _make_service(tmp_path)
    dangerous_filename = 'danger"\nname.step'
    dangerous_source_path = str(tmp_path / 'vault/input"\nname.step')
    source_file = _make_source_file(dangerous_filename)

    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        script_path = Path(cmd[-1])
        captured["script"] = script_path.read_text(encoding="utf-8")
        params_path = Path(kwargs["env"][_FREECAD_PARAMS_ENV_VAR])
        captured["params"] = json.loads(params_path.read_text(encoding="utf-8"))

        output_path = Path(captured["params"]["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("generated", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="CONVERSION_SUCCESS\n", stderr="")

    with patch(
        "yuantus.meta_engine.services.cad_converter_service.subprocess.run",
        side_effect=fake_run,
    ):
        result = service._freecad_convert(dangerous_source_path, source_file, "obj")

    expected = tmp_path / "vault" / "inputs" / "_danger_name" / "danger_name.obj"
    assert result == str(expected)
    assert Path(result).parent.name == "_danger_name"
    assert Path(result).name == "danger_name.obj"
    assert dangerous_filename not in captured["script"]
    assert dangerous_source_path not in captured["script"]
    assert str(expected) not in captured["script"]
    assert captured["params"] == {
        "input_path": dangerous_source_path,
        "output_path": str(expected),
        "target_format": "obj",
    }


def test_freecad_preview_uses_params_file_and_sanitized_preview_path(tmp_path):
    service = _make_service(tmp_path)
    dangerous_filename = 'danger"\nname.step'
    dangerous_source_path = str(tmp_path / 'vault/input"\nname.step')
    source_file = _make_source_file(dangerous_filename)

    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):
        script_path = Path(cmd[-1])
        captured["script"] = script_path.read_text(encoding="utf-8")
        params_path = Path(kwargs["env"][_FREECAD_PARAMS_ENV_VAR])
        captured["params"] = json.loads(params_path.read_text(encoding="utf-8"))

        output_path = Path(captured["params"]["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("preview", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="PREVIEW_SUCCESS\n", stderr="")

    with patch(
        "yuantus.meta_engine.services.cad_converter_service.subprocess.run",
        side_effect=fake_run,
    ):
        result = service._generate_preview(dangerous_source_path, source_file)

    expected = (
        tmp_path / "vault" / "inputs" / "_danger_name" / "danger_name_preview.png"
    )
    assert result == str(expected)
    assert Path(result).parent.name == "_danger_name"
    assert Path(result).name == "danger_name_preview.png"
    assert dangerous_filename not in captured["script"]
    assert dangerous_source_path not in captured["script"]
    assert str(expected) not in captured["script"]
    assert captured["params"] == {
        "input_path": dangerous_source_path,
        "output_path": str(expected),
    }
