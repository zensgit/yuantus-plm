"""
Bridge between typed tables (PartBOM) and generic relationships.

Deprecated: relationships are now stored as Items (meta_items).
This bridge is intentionally disabled to prevent legacy writes.
"""




class PartBOMBridge:
    """
    PartBOM表与通用关系的桥接
    写入part_bom时自动同步到Relationship表
    """

    @staticmethod
    def setup_listeners():
        """Deprecated: intentionally disabled."""
        raise RuntimeError(
            "PartBOMBridge is deprecated; relationships are stored as Items."
        )
