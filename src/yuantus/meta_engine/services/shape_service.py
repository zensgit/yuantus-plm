import math
import random
import hashlib
import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.index import GeometricIndex


class ShapeService:
    """
    Mock Service for Geometric Search.

    Real Implementation would:
    1. Parse CAD file (step/iges) with Kernel.
    2. Extract geometric features (Volume, Area, Moments, Point Cloud).
    3. Generate Descriptor Vector (e.g. PointNet++, MVCNN).

    Stub Implementation:
    1. Deterministic Hash of file content -> Seed.
    2. Generate random 128-d vector based on seed.
    """

    DIMENSIONS = 128

    def __init__(self, session: Session):
        self.session = session

    def _generate_vector(self, seed_bytes: bytes) -> List[float]:
        """Generate deterministic vector from seed."""
        # Use sha256 of content to get a stable integer seed
        hex_digest = hashlib.sha256(seed_bytes).hexdigest()
        seed_int = int(hex_digest, 16)

        rnd = random.Random(seed_int)

        # Generate normalized vector
        vector = [rnd.uniform(-1.0, 1.0) for _ in range(self.DIMENSIONS)]
        magnitude = math.sqrt(sum(x * x for x in vector))
        return [x / magnitude for x in vector]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate dot product (vectors are normalized)."""
        return sum(a * b for a, b in zip(v1, v2))

    def index_item(self, item_id: str, file_path_or_bytes: Any) -> GeometricIndex:
        """
        Extract features and store index.
        """
        # If input is bytes
        if isinstance(file_path_or_bytes, bytes):
            content = file_path_or_bytes
        else:
            # Assume path
            with open(file_path_or_bytes, "rb") as f:
                content = f.read()

        vector = self._generate_vector(content)

        # Check if index exists
        idx = self.session.query(GeometricIndex).filter_by(item_id=item_id).first()
        if not idx:
            idx = GeometricIndex(
                id=str(uuid.uuid4()), item_id=item_id, algorithm_version="stub-v1"
            )
            self.session.add(idx)

        idx.vector = vector
        idx.signature_hash = hashlib.md5(content).hexdigest()
        self.session.flush()
        return idx

    def find_similar(
        self, query_vector: List[float], limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for items with similar vectors.
        Returns list of {item_id, score}.
        """
        # 1. Fetch all indices
        # Optimization: In real system, use pgvector or FAISS.
        all_indices = self.session.query(GeometricIndex).all()

        results = []
        for idx in all_indices:
            score = self._cosine_similarity(query_vector, idx.vector)
            results.append(
                {"item_id": idx.item_id, "score": score, "vector": idx.vector}  # Debug
            )

        # 2. Sort by score desc
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_vector_from_file_bytes(self, content: bytes) -> List[float]:
        return self._generate_vector(content)
