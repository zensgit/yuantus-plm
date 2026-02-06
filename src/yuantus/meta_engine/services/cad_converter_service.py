"""
CAD Converter Service for Meta-Engine
Based on patterns from DocDoku-PLM (FreeCAD) and Odoo PLM (cad_excenge).

Provides:
- STEP/IGES → OBJ/glTF conversion for 3D viewer
- Thumbnail/preview generation
- Async job queue processing
"""

import logging
import os
import uuid
import hashlib
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Try cadquery import
try:
    import cadquery as cq

    CADQUERY_AVAILABLE = True
except ImportError:
    CADQUERY_AVAILABLE = False
    logger.warning(
        "cadquery not installed. STEP/IGES conversion will rely on FreeCAD/Trimesh."
    )

from yuantus.meta_engine.models.file import (
    FileContainer,
    ConversionJob,
    ConversionStatus,
    DocumentType,
    Vault,
)


# Supported input formats (from Odoo PLM cad_excenge.py pattern)
SUPPORTED_CAD_FORMATS = {
    # Standard exchange formats
    "step",
    "stp",
    "iges",
    "igs",
    # Native formats (require specific converters)
    "sldprt",
    "sldasm",  # SolidWorks
    "ipt",
    "iam",  # Inventor
    "prt",
    "asm",  # NX/Pro-E
    "catpart",
    "catproduct",  # CATIA
    "par",
    "psm",  # Solid Edge
    "3dm",  # Rhino
    "dwg",
    "dxf",  # AutoCAD
    # Mesh formats (already viewable)
    "stl",
    "obj",
    "3ds",
    "gltf",
    "glb",
    # Other
    "jt",
    "x_t",
    "x_b",
    "wrl",
    "vrml",
}

# Output formats for web viewer
OUTPUT_FORMATS = {"obj", "gltf", "glb", "stl"}

# Preview formats
PREVIEW_FORMATS = {"png", "jpg", "jpeg"}


class CADConverterService:
    """
    Service for converting CAD files to viewable formats.

    Based on patterns from:
    - DocDoku-PLM: FreeCAD script-based conversion
    - Odoo PLM: Conversion stack with job queue
    """

    def __init__(self, session: Session, vault_base_path: str = "./vault"):
        self.session = session
        self.vault_base_path = vault_base_path
        self._freecad_path = self._find_freecad()

    def _find_freecad(self) -> Optional[str]:
        """Locate FreeCAD installation."""
        # Common paths
        candidates = [
            "/usr/bin/freecadcmd",
            "/usr/local/bin/freecadcmd",
            "/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd",
            "C:\\Program Files\\FreeCAD\\bin\\FreeCADCmd.exe",
            shutil.which("freecadcmd"),
            shutil.which("FreeCADCmd"),
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    @property
    def freecad_available(self) -> bool:
        """Check if FreeCAD is available for conversion."""
        return self._freecad_path is not None

    @property
    def cadquery_available(self) -> bool:
        """Check if cadquery is available for conversion."""
        return CADQUERY_AVAILABLE

    def get_supported_conversions(self) -> Dict[str, List[str]]:
        """Return matrix of supported conversions."""
        return {
            "input_formats": sorted(SUPPORTED_CAD_FORMATS),
            "output_formats": sorted(OUTPUT_FORMATS),
            "preview_formats": sorted(PREVIEW_FORMATS),
            "freecad_available": self.freecad_available,
        }

    # =========================================================================
    # Job Queue Management (Odoo plm_convert_stack pattern)
    # =========================================================================

    def create_conversion_job(
        self,
        source_file_id: str,
        target_format: str,
        operation_type: str = "convert",
        priority: int = 100,
    ) -> ConversionJob:
        """
        Create a conversion job in the queue.

        Args:
            source_file_id: ID of FileContainer to convert
            target_format: Target format (obj, gltf, png, etc.)
            operation_type: Type of operation (convert, preview, printout)
            priority: Job priority (lower = higher priority)
        """
        job = ConversionJob(
            id=str(uuid.uuid4()),
            source_file_id=source_file_id,
            target_format=target_format.lower(),
            operation_type=operation_type,
            status=ConversionStatus.PENDING.value,
            priority=priority,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get_pending_jobs(self, batch_size: int = 10) -> List[ConversionJob]:
        """Get pending jobs ordered by priority and creation time."""
        return (
            self.session.query(ConversionJob)
            .filter(
                ConversionJob.status.in_(
                    [
                        ConversionStatus.PENDING.value,
                        ConversionStatus.FAILED.value,
                    ]
                )
            )
            .filter(ConversionJob.retry_count < ConversionJob.max_retries)
            .order_by(ConversionJob.priority.asc(), ConversionJob.created_at.asc())
            .limit(batch_size)
            .all()
        )

    def process_job(self, job: ConversionJob) -> bool:
        """
        Process a single conversion job.
        Returns True if successful, False otherwise.
        """
        job.status = ConversionStatus.PROCESSING.value
        job.started_at = datetime.utcnow()
        self.session.flush()

        try:
            source_file = self.session.get(FileContainer, job.source_file_id)
            if not source_file:
                raise ValueError(f"Source file {job.source_file_id} not found")

            # Get full path to source file
            source_path = self._get_file_path(source_file)

            if job.operation_type == "preview":
                result_path = self._generate_preview(source_path, source_file)
            elif job.operation_type == "convert":
                result_path = self._convert_to_geometry(
                    source_path, source_file, job.target_format
                )
            else:
                raise ValueError(f"Unknown operation: {job.operation_type}")

            # Create result file record
            result_file = self._create_result_file(
                source_file, result_path, job.target_format, job.operation_type
            )

            # Update job as completed
            job.result_file_id = result_file.id
            job.status = ConversionStatus.COMPLETED.value
            job.completed_at = datetime.utcnow()

            # Update source file with generated paths
            if job.operation_type == "preview":
                source_file.preview_path = result_file.system_path
                source_file.conversion_status = ConversionStatus.COMPLETED.value
            elif job.operation_type == "convert":
                source_file.geometry_path = result_file.system_path
                source_file.conversion_status = ConversionStatus.COMPLETED.value

            self.session.flush()
            return True

        except Exception as e:
            job.status = ConversionStatus.FAILED.value
            job.error_message = str(e)
            job.retry_count += 1
            self.session.flush()
            return False

    def process_batch(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Process a batch of pending jobs.
        Returns counts of processed, succeeded, and failed jobs.
        """
        jobs = self.get_pending_jobs(batch_size)
        results = {"processed": 0, "succeeded": 0, "failed": 0}

        for job in jobs:
            results["processed"] += 1
            if self.process_job(job):
                results["succeeded"] += 1
            else:
                results["failed"] += 1

        return results

    # =========================================================================
    # Direct Conversion Methods
    # =========================================================================

    def convert_file(
        self,
        file_container: FileContainer,
        target_format: str = "obj",
        generate_preview: bool = True,
    ) -> Dict[str, Any]:
        """
        Synchronously convert a CAD file.

        Args:
            file_container: FileContainer to convert
            target_format: Target format for geometry (obj, gltf, etc.)
            generate_preview: Whether to generate a preview thumbnail

        Returns:
            Dict with paths to generated files
        """
        source_path = self._get_file_path(file_container)
        result = {"source_id": file_container.id}

        # Generate geometry
        if target_format in OUTPUT_FORMATS:
            geometry_path = self._convert_to_geometry(
                source_path, file_container, target_format
            )
            result["geometry_path"] = geometry_path
            file_container.geometry_path = geometry_path

        # Generate preview
        if generate_preview:
            preview_path = self._generate_preview(source_path, file_container)
            result["preview_path"] = preview_path
            file_container.preview_path = preview_path

        file_container.conversion_status = ConversionStatus.COMPLETED.value
        self.session.flush()

        return result

    # =========================================================================
    # Internal Conversion Logic
    # =========================================================================

    def _get_file_path(self, file_container: FileContainer) -> str:
        """Get full filesystem path to a file."""
        if file_container.vault_id:
            vault = self.session.get(Vault, file_container.vault_id)
            if vault and vault.base_path:
                return os.path.join(vault.base_path, file_container.system_path)
        return os.path.join(self.vault_base_path, file_container.system_path)

    def _convert_to_geometry(
        self,
        source_path: str,
        source_file: FileContainer,
        target_format: str,
    ) -> str:
        """
        Convert CAD file to viewable geometry format.
        Uses FreeCAD for STEP/IGES, direct copy for already-viewable formats.
        """
        ext = source_file.get_extension()

        # Already in viewable format
        if ext in OUTPUT_FORMATS:
            return source_path

        # STEP/IGES conversion via Cadquery or FreeCAD
        if ext in {"step", "stp", "iges", "igs"}:
            if self.cadquery_available:
                return self._cadquery_convert(source_path, source_file, target_format)
            elif self.freecad_available:
                return self._freecad_convert(source_path, source_file, target_format)
            else:
                raise RuntimeError(
                    "No suitable converter (cadquery or FreeCAD) available for STEP/IGES."
                )

        # Fallback: try trimesh (for mesh formats)
        return self._trimesh_convert(source_path, source_file, target_format)

    def _freecad_convert(
        self,
        source_path: str,
        source_file: FileContainer,
        target_format: str,
    ) -> str:
        """
        Convert using FreeCAD (DocDoku-PLM pattern).

        Based on DocDoku convert_step_obj.py script.
        """
        if not self.freecad_available:
            raise RuntimeError("FreeCAD not available for conversion")

        # Create output path in generated files subfolder (DocDoku pattern)
        output_dir = self._get_generated_dir(source_file)
        output_filename = f"{Path(source_file.filename).stem}.{target_format}"
        output_path = os.path.join(output_dir, output_filename)

        # Write FreeCAD conversion script
        script_content = self._generate_freecad_script(
            source_path, output_path, target_format
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        try:
            # Execute FreeCAD script
            result = subprocess.run(
                [self._freecad_path, "-c", script_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"FreeCAD conversion failed: {result.stderr}")

            if not os.path.exists(output_path):
                raise RuntimeError("Output file not created")

            return output_path

        finally:
            os.unlink(script_path)

    def _generate_freecad_script(
        self,
        input_path: str,
        output_path: str,
        target_format: str,
    ) -> str:
        """
        Generate FreeCAD Python script for conversion.
        Based on DocDoku-PLM convert_step_obj.py pattern.
        """
        return f"""
# FreeCAD conversion script (auto-generated)
# Based on DocDoku-PLM pattern

import sys
import os

# Ensure output directory exists
os.makedirs(os.path.dirname("{output_path}"), exist_ok=True)

try:
    import FreeCAD
    import Part
    import Mesh

    # Load STEP/IGES file
    shape = Part.Shape()
    shape.read("{input_path}")

    # Create mesh from shape
    # Use deviation 0.1 for balance of quality/performance
    mesh = Mesh.Mesh()
    for face in shape.Faces:
        mesh.addMesh(face.tessellate(0.1))

    # Export to target format
    if "{target_format}" == "obj":
        mesh.write("{output_path}")
    elif "{target_format}" in ("gltf", "glb"):
        # For glTF, we need additional processing
        mesh.write("{output_path.replace('.gltf', '.obj').replace('.glb', '.obj')}")
    elif "{target_format}" == "stl":
        mesh.write("{output_path}")
    else:
        mesh.write("{output_path}")

    print("CONVERSION_SUCCESS")

except Exception as e:
    print(f"CONVERSION_ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

    def _trimesh_convert(
        self,
        source_path: str,
        source_file: FileContainer,
        target_format: str,
    ) -> str:
        """
        Fallback conversion using trimesh library.
        """
        try:
            import trimesh
        except ImportError:
            raise RuntimeError("trimesh not installed for conversion fallback")

        # Load mesh
        mesh = trimesh.load(source_path)

        # Create output path
        output_dir = self._get_generated_dir(source_file)
        output_filename = f"{Path(source_file.filename).stem}.{target_format}"
        output_path = os.path.join(output_dir, output_filename)

        # Export
        mesh.export(output_path, file_type=target_format)

        return output_path

    def _cadquery_convert(
        self,
        source_path: str,
        source_file: FileContainer,
        target_format: str,
    ) -> str:
        """
        Convert using cadquery (Odoo PLM pattern).
        """
        if not self.cadquery_available:
            raise RuntimeError("cadquery not available for conversion")

        # Create output path
        output_dir = self._get_generated_dir(source_file)
        output_filename = f"{Path(source_file.filename).stem}.{target_format}"
        output_path = os.path.join(output_dir, output_filename)

        try:
            # Import STEP/IGES
            result = cq.importers.importStep(source_path)

            # Export to STL, then chain to trimesh for OBJ/gltf
            stl_output_path = output_path.replace(f".{target_format}", ".stl")
            cq.exporters.export(
                result, stl_output_path, format=cq.exporters.ExportTypes.STL
            )

            if target_format == "stl":
                return stl_output_path
            elif target_format in {"obj", "gltf", "glb"}:
                # If target is OBJ/gltf/glb, convert STL further using trimesh
                return self._trimesh_convert(
                    stl_output_path, source_file, target_format
                )
            else:
                raise ValueError(
                    f"Unsupported target format for cadquery: {target_format}"
                )

        except Exception as e:
            raise RuntimeError(f"cadquery conversion failed: {e}")

    def _generate_preview(
        self,
        source_path: str,
        source_file: FileContainer,
    ) -> str:
        """
        Generate preview thumbnail for CAD file.

        Based on Odoo PLM pattern: preview stored alongside original.
        """
        output_dir = self._get_generated_dir(source_file)
        preview_filename = f"{Path(source_file.filename).stem}_preview.png"
        preview_path = os.path.join(output_dir, preview_filename)

        ext = source_file.get_extension()

        # For mesh formats, try to render with trimesh
        if ext in {"stl", "obj", "gltf", "glb", "3ds"}:
            return self._trimesh_preview(source_path, preview_path)

        # For STEP/IGES, use FreeCAD
        if ext in {"step", "stp", "iges", "igs"} and self.freecad_available:
            return self._freecad_preview(source_path, preview_path)

        # Fallback: create placeholder preview
        return self._create_placeholder_preview(preview_path, source_file)

    def _trimesh_preview(self, source_path: str, output_path: str) -> str:
        """Generate preview using trimesh scene rendering."""
        try:
            import trimesh

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            mesh = trimesh.load(source_path)

            # Try to render a preview image
            scene = trimesh.Scene(mesh)

            # Use pyrender if available for better rendering
            try:
                png_data = scene.save_image(resolution=(256, 256))
                with open(output_path, "wb") as f:
                    f.write(png_data)
                return output_path
            except Exception:
                # Fallback to simple bounds-based preview
                return self._create_placeholder_preview(
                    output_path, info=f"Mesh: {len(mesh.vertices)} vertices"
                )

        except Exception as e:
            return self._create_placeholder_preview(
                output_path, info=f"Error: {str(e)[:50]}"
            )

    def _freecad_preview(self, source_path: str, output_path: str) -> str:
        """Generate preview using FreeCAD."""
        if not self.freecad_available:
            return self._create_placeholder_preview(output_path)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        script_content = f"""
import sys
import os

os.makedirs(os.path.dirname("{output_path}"), exist_ok=True)

try:
    import FreeCAD
    import FreeCADGui
    import Part

    FreeCADGui.showMainWindow()
    doc = FreeCAD.newDocument()

    shape = Part.Shape()
    shape.read("{source_path}")
    Part.show(shape)

    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    FreeCADGui.ActiveDocument.ActiveView.saveImage("{output_path}", 256, 256)

    print("PREVIEW_SUCCESS")

except Exception as e:
    print(f"PREVIEW_ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as script_file:
            script_file.write(script_content)
            script_path = script_file.name

        try:
            subprocess.run(
                [self._freecad_path, script_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if os.path.exists(output_path):
                return output_path

            return self._create_placeholder_preview(output_path)

        finally:
            os.unlink(script_path)

    def _create_placeholder_preview(
        self,
        output_path: str,
        source_file: Optional[FileContainer] = None,
        info: Optional[str] = None,
    ) -> str:
        """Create a simple placeholder preview image."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            from PIL import Image, ImageDraw

            size = 256
            if source_file:
                ext = source_file.get_extension().lower()
                if ext == "dxf":
                    size = 512

            # Create simple placeholder image
            img = Image.new("RGB", (size, size), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)

            # Draw border
            draw.rectangle([0, 0, size - 1, size - 1], outline=(200, 200, 200), width=2)

            # Add text
            text = "CAD Preview"
            if source_file:
                text = source_file.get_extension().upper()
            if info:
                text = f"{text}\n{info}"

            # Center text
            draw.text((size / 2, size / 2), text, fill=(100, 100, 100), anchor="mm")

            img.save(output_path, "PNG")

        except ImportError:
            # No PIL, create minimal PNG
            size = 256
            if source_file and source_file.get_extension().lower() == "dxf":
                size = 512
            self._create_minimal_png(output_path, width=size, height=size)

        return output_path

    def _create_minimal_png(self, output_path: str, width: int = 1, height: int = 1):
        """Create minimal valid PNG file without PIL."""
        import struct
        import zlib

        width = max(1, int(width))
        height = max(1, int(height))

        # Build raw RGB data (gray) with filter byte per row
        row = b"\x00" + (b"\x80\x80\x80" * width)
        raw = row * height
        compressed = zlib.compress(raw)

        def _chunk(tag: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            return length + tag + data + crc

        ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        png_data = b"".join(
            [
                b"\x89PNG\r\n\x1a\n",
                _chunk(b"IHDR", ihdr),
                _chunk(b"IDAT", compressed),
                _chunk(b"IEND", b""),
            ]
        )

        with open(output_path, "wb") as handle:
            handle.write(png_data)

    def _get_generated_dir(self, source_file: FileContainer) -> str:
        """
        Get directory for generated files (DocDoku pattern: _{filename}/).
        """
        base_dir = os.path.dirname(self._get_file_path(source_file))
        generated_dir = os.path.join(base_dir, f"_{Path(source_file.filename).stem}")
        os.makedirs(generated_dir, exist_ok=True)
        return generated_dir

    def _create_result_file(
        self,
        source_file: FileContainer,
        result_path: str,
        target_format: str,
        operation_type: str,
    ) -> FileContainer:
        """Create FileContainer record for conversion result."""
        stat = os.stat(result_path)

        # Calculate checksum
        with open(result_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        result_file = FileContainer(
            id=str(uuid.uuid4()),
            filename=os.path.basename(result_path),
            file_type=target_format,
            mime_type=self._get_mime_type(target_format),
            file_size=stat.st_size,
            checksum=checksum,
            vault_id=source_file.vault_id,
            system_path=os.path.relpath(result_path, self.vault_base_path),
            document_type=(
                DocumentType.OTHER.value
                if operation_type == "preview"
                else source_file.document_type
            ),
            is_native_cad=False,
            source_file_id=source_file.id,
            conversion_status=ConversionStatus.COMPLETED.value,
        )

        self.session.add(result_file)
        return result_file

    def _get_mime_type(self, format: str) -> str:
        """Get MIME type for file format."""
        mime_types = {
            "obj": "model/obj",
            "gltf": "model/gltf+json",
            "glb": "model/gltf-binary",
            "stl": "model/stl",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "pdf": "application/pdf",
        }
        return mime_types.get(format.lower(), "application/octet-stream")


# Convenience function for background worker
def process_conversion_queue(session: Session, batch_size: int = 10) -> Dict[str, int]:
    """Process pending conversion jobs. Call from background worker."""
    service = CADConverterService(session)
    return service.process_batch(batch_size)
