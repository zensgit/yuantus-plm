"""
File Storage Models
Based on patterns from DocDoku-PLM, Odoo18-PLM, and ERPNext.
"""

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    BigInteger,
    Integer,
    Boolean,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from yuantus.models.base import Base


class DocumentType(str, enum.Enum):
    """Document type classification (from Odoo PLM pattern)."""

    CAD_3D = "3d"
    CAD_2D = "2d"
    PRESENTATION = "pr"
    OTHER = "other"


class FileRole(str, enum.Enum):
    """Role of file in relation to an item."""

    NATIVE_CAD = "native_cad"  # Primary CAD file
    PREVIEW = "preview"  # Preview/thumbnail
    ATTACHMENT = "attachment"  # General attachment
    PRINTOUT = "printout"  # PDF printout
    GEOMETRY = "geometry"  # Converted geometry (OBJ, glTF)
    DRAWING = "drawing"  # 2D drawing


class ConversionStatus(str, enum.Enum):
    """Status of CAD conversion job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Vault(Base):
    """
    文件柜 (Vault) 配置
    定义文件存储的位置 (Local, S3, FTP...)
    Based on DocDoku-PLM vault pattern.
    """

    __tablename__ = "meta_vaults"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)

    # Type: "local", "s3"
    storage_type = Column(String, default="local")

    # Path (for local) or Bucket (for S3)
    base_path = Column(String)

    # URL template for downloading (e.g. http://file-server/vault/{id})
    url_template = Column(String)

    # Active flag
    is_active = Column(Boolean, default=True)

    # Priority for selection (lower = higher priority)
    priority = Column(Integer, default=100)


class FileContainer(Base):
    """
    文件物理记录 (Enhanced)
    对应真实存储在磁盘上的文件

    Enhanced with CAD-specific fields based on:
    - DocDoku-PLM: BinaryResource, Geometry
    - Odoo18-PLM: ir.attachment with preview, printout
    """

    __tablename__ = "meta_files"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Original file info
    filename = Column(String, nullable=False)  # original name "screw.step"
    file_type = Column(String, index=True)  # extension: "step", "stp", "iges"
    mime_type = Column(String)  # MIME type: "model/step"
    file_size = Column(BigInteger)  # bytes

    # Checksum for integrity (SHA256)
    checksum = Column(String, index=True)

    # Storage details
    vault_id = Column(String, ForeignKey("meta_vaults.id"))

    # Physical path relative to vault base
    # Pattern from DocDoku: {workspace}/{type}/{id}/{version}/{filename}
    system_path = Column(String, nullable=False)

    # CAD-specific fields (from Odoo PLM pattern)
    document_type = Column(
        String, default=DocumentType.OTHER.value
    )  # 3d, 2d, pr, other
    is_native_cad = Column(Boolean, default=False)
    cad_format = Column(String)  # "STEP", "IGES", "SOLIDWORKS", etc.

    # Generated content paths (stored in _{filename}/ subfolder per DocDoku pattern)
    preview_path = Column(String)  # thumbnail PNG path
    preview_data = Column(Text)  # base64 encoded preview (for quick access)
    geometry_path = Column(String)  # converted OBJ/glTF path for 3D viewer
    printout_path = Column(String)  # PDF printout path

    # Conversion status
    conversion_status = Column(String, default=ConversionStatus.PENDING.value)
    conversion_error = Column(Text)

    # Audit fields
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    vault = relationship("Vault")
    created_by = relationship("RBACUser", foreign_keys=[created_by_id])

    # Link to source file (for converted files)
    source_file_id = Column(String, ForeignKey("meta_files.id"), nullable=True)
    source_file = relationship("FileContainer", remote_side=[id])

    def get_extension(self) -> str:
        """Get file extension without dot."""
        if self.file_type:
            return self.file_type.lower().lstrip(".")
        if self.filename and "." in self.filename:
            return self.filename.rsplit(".", 1)[1].lower()
        return ""

    def is_cad_file(self) -> bool:
        """Check if this is a CAD file based on extension."""
        cad_extensions = {
            "step",
            "stp",
            "iges",
            "igs",  # Standard exchange
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
            "stl",
            "obj",
            "3ds",  # Mesh formats
            "gltf",
            "glb",  # Web 3D
            "jt",
            "x_t",
            "x_b",  # Other formats
        }
        return self.get_extension() in cad_extensions


class ItemFile(Base):
    """
    Association table for Item-File relationships.
    Allows multiple files per item with different roles.
    Based on DocDoku-PLM PartIteration pattern (nativeCADFile, attachedFiles, geometries).
    """

    __tablename__ = "meta_item_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    file_id = Column(String, ForeignKey("meta_files.id"), nullable=False, index=True)

    # Role of file (from FileRole enum)
    file_role = Column(String, default=FileRole.ATTACHMENT.value)

    # Display order
    sequence = Column(Integer, default=0)

    # Optional description
    description = Column(String)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("Item", backref="item_files")
    file = relationship("FileContainer")


class ConversionJob(Base):
    """
    Track CAD conversion jobs (async processing).
    Based on Odoo PLM plm.convert.stack pattern.
    """

    __tablename__ = "cad_conversion_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Source file to convert
    source_file_id = Column(String, ForeignKey("meta_files.id"), nullable=False)

    # Target format (obj, gltf, png, pdf)
    target_format = Column(String, nullable=False)

    # Operation type (from Odoo pattern)
    operation_type = Column(String, default="convert")  # convert, preview, printout

    # Status tracking
    status = Column(String, default=ConversionStatus.PENDING.value, index=True)
    error_message = Column(Text, nullable=True)

    # Result
    result_file_id = Column(String, ForeignKey("meta_files.id"), nullable=True)

    # Priority (for queue ordering)
    priority = Column(Integer, default=100)

    # Retry tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    source_file = relationship("FileContainer", foreign_keys=[source_file_id])
    result_file = relationship("FileContainer", foreign_keys=[result_file_id])
