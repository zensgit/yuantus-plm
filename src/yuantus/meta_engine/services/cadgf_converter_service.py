from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from yuantus.config import get_settings
from yuantus.config.settings import Settings


ASSET_URI_PREFIX = "asset/"


@dataclass
class CadgfArtifacts:
    manifest_path: Path
    document_path: Optional[Path]
    mesh_gltf_path: Optional[Path]
    mesh_bin_path: Optional[Path]
    mesh_metadata_path: Optional[Path]


class CadgfConversionError(RuntimeError):
    pass


class CADGFConverterService:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def convert(self, input_path: str, output_dir: str, extension: str) -> CadgfArtifacts:
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        extension = extension.lower().lstrip(".")
        convert_script = self._resolve_convert_script()
        plugin_path = self._resolve_plugin(extension)
        convert_cli = self._resolve_convert_cli()
        python_bin = (
            Path(self.settings.CADGF_PYTHON_BIN)
            if self.settings.CADGF_PYTHON_BIN
            else Path(sys.executable)
        )

        if not convert_script:
            raise CadgfConversionError(
                "CADGF convert script not found. Set YUANTUS_CADGF_CONVERT_SCRIPT or YUANTUS_CADGF_ROOT."
            )
        if not plugin_path:
            raise CadgfConversionError(
                f"CADGF importer plugin not found for .{extension}. Set YUANTUS_CADGF_DXF_PLUGIN_PATH."
            )
        if not python_bin.exists():
            raise CadgfConversionError(f"CADGF python executable missing: {python_bin}")

        cmd = [
            str(python_bin),
            str(convert_script),
            "--plugin",
            str(plugin_path),
            "--input",
            str(input_path),
            "--out",
            str(output_dir),
            "--json",
            "--gltf",
        ]
        if convert_cli:
            cmd.extend(["--convert-cli", str(convert_cli)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise CadgfConversionError(
                f"CADGF conversion failed ({result.returncode}): {detail}"
            )

        manifest_path = output_dir / "manifest.json"
        if not manifest_path.exists():
            raise CadgfConversionError("CADGF conversion did not produce manifest.json")

        document_path = output_dir / "document.json"
        mesh_gltf_path = output_dir / "mesh.gltf"
        mesh_bin_path = output_dir / "mesh.bin"
        mesh_metadata_path = output_dir / "mesh_metadata.json"

        if mesh_gltf_path.exists():
            self._rewrite_gltf_buffer_uris(mesh_gltf_path)

        return CadgfArtifacts(
            manifest_path=manifest_path,
            document_path=document_path if document_path.exists() else None,
            mesh_gltf_path=mesh_gltf_path if mesh_gltf_path.exists() else None,
            mesh_bin_path=mesh_bin_path if mesh_bin_path.exists() else None,
            mesh_metadata_path=(
                mesh_metadata_path if mesh_metadata_path.exists() else None
            ),
        )

    def _resolve_root(self) -> Optional[Path]:
        if self.settings.CADGF_ROOT:
            root = Path(self.settings.CADGF_ROOT)
            if root.exists():
                return root

        here = Path(__file__).resolve()
        parents = here.parents
        if len(parents) >= 5:
            yuantus_root = parents[4]
            candidate = yuantus_root.parent / "CADGameFusion"
            if candidate.exists():
                return candidate
        return None

    def _resolve_convert_script(self) -> Optional[Path]:
        if self.settings.CADGF_CONVERT_SCRIPT:
            path = Path(self.settings.CADGF_CONVERT_SCRIPT)
            if path.exists():
                return path
        root = self._resolve_root()
        if root:
            candidate = root / "tools" / "plm_convert.py"
            if candidate.exists():
                return candidate
        return None

    def _resolve_convert_cli(self) -> Optional[Path]:
        if self.settings.CADGF_CONVERT_CLI:
            path = Path(self.settings.CADGF_CONVERT_CLI)
            if path.exists():
                return path
        root = self._resolve_root()
        if not root:
            return None
        candidates = [
            root / "build_vcpkg" / "tools" / "convert_cli",
            root / "build" / "tools" / "convert_cli",
            root / "build_vcpkg" / "tools" / "convert_cli.exe",
            root / "build" / "tools" / "convert_cli.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _resolve_plugin(self, extension: str) -> Optional[Path]:
        ext = extension.lower().lstrip(".")
        if ext != "dxf":
            return None

        if self.settings.CADGF_DXF_PLUGIN_PATH:
            path = Path(self.settings.CADGF_DXF_PLUGIN_PATH)
            if path.exists():
                return path

        root = self._resolve_root()
        if not root:
            return None
        search_dirs = [
            root / "build_vcpkg" / "plugins",
            root / "build" / "plugins",
        ]
        base_names = ["cadgf_dxf_importer_plugin", "libcadgf_dxf_importer_plugin"]
        extensions = [".so", ".dylib", ".dll"]
        for directory in search_dirs:
            for base in base_names:
                for ext in extensions:
                    candidate = directory / f"{base}{ext}"
                    if candidate.exists():
                        return candidate
            if directory.exists():
                matches = sorted(directory.glob("*cadgf_dxf_importer_plugin*"))
                if matches:
                    return matches[0]
        return None

    def _rewrite_gltf_buffer_uris(self, gltf_path: Path) -> None:
        try:
            with gltf_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return

        buffers = data.get("buffers")
        if not isinstance(buffers, list):
            return

        changed = False
        for buffer in buffers:
            if not isinstance(buffer, dict):
                continue
            uri = buffer.get("uri")
            if not uri or uri.startswith("data:"):
                continue
            if "://" in uri or uri.startswith(ASSET_URI_PREFIX):
                continue
            buffer["uri"] = f"{ASSET_URI_PREFIX}{uri}"
            changed = True

        if changed:
            with gltf_path.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
                handle.write("\n")
