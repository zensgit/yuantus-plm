from sqlalchemy import JSON, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


class GeometricIndex(Base):
    """
    Stores geometric feature vectors for Items (Shape Search).
    """

    __tablename__ = "meta_geometric_indices"

    id = Column(String, primary_key=True)  # UUID

    # Link to the Item (which has the File)
    item_id = Column(
        String,
        ForeignKey("meta_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # The Vector (High Dimensional Point)
    # Stored as JSONB on Postgres, plain JSON elsewhere (e.g., SQLite tests).
    vector = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)

    # Metadata for the algorithm used
    # e.g. "random-stub-v1" or "pointnet-v2"
    algorithm_version = Column(String, default="stub-v1")

    # Hash of the source file to detect staleness?
    signature_hash = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "vector": self.vector,  # serialized
            "algorithm": self.algorithm_version,
        }
