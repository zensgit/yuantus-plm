"""
Version File Service
Manages file associations with versions.

Sprint 2 Enhancement: Version-File Integration
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from yuantus.meta_engine.version.models import (
    ItemVersion,
    VersionFile,
)
from yuantus.meta_engine.models.file import FileContainer


class VersionFileError(Exception):
    """Version file operation error."""

    pass


class VersionFileService:
    """
    Manages file associations with item versions.

    Key Features:
    - Attach/detach files to versions
    - Copy file associations when creating new versions
    - Compare files between versions
    - Track primary files
    """

    def __init__(self, session: Session):
        self.session = session

    def attach_file(
        self,
        version_id: str,
        file_id: str,
        file_role: str = "attachment",
        is_primary: bool = False,
        sequence: int = 0,
    ) -> VersionFile:
        """
        Attach a file to a version.

        Args:
            version_id: Target version ID
            file_id: File to attach
            file_role: Role of the file (native_cad, preview, attachment, etc.)
            is_primary: Whether this is the primary file
            sequence: Display order

        Returns:
            VersionFile association record
        """
        # Validate version exists
        version = self.session.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")

        # Validate file exists
        file = self.session.get(FileContainer, file_id)
        if not file:
            raise VersionFileError(f"File {file_id} not found")

        # Check if association already exists
        existing = (
            self.session.query(VersionFile)
            .filter_by(version_id=version_id, file_id=file_id, file_role=file_role)
            .first()
        )

        if existing:
            # Update existing
            existing.is_primary = is_primary
            existing.sequence = sequence
            self.session.add(existing)
            return existing

        # Create new association
        vf = VersionFile(
            id=str(uuid.uuid4()),
            version_id=version_id,
            file_id=file_id,
            file_role=file_role,
            sequence=sequence,
            snapshot_path=file.system_path,
            is_primary=is_primary,
            created_at=datetime.utcnow(),
        )
        self.session.add(vf)

        # Update version file count
        version.file_count = (version.file_count or 0) + 1

        # Set primary file on version if specified
        if is_primary:
            version.primary_file_id = file_id
            # Clear other primary flags
            self.session.query(VersionFile).filter(
                VersionFile.version_id == version_id, VersionFile.id != vf.id
            ).update({"is_primary": False})

        self.session.add(version)
        self.session.flush()

        return vf

    def detach_file(self, version_id: str, file_id: str, file_role: str = None) -> bool:
        """
        Detach a file from a version.

        Args:
            version_id: Target version ID
            file_id: File to detach
            file_role: If specified, only detach for this role

        Returns:
            True if file was detached
        """
        query = self.session.query(VersionFile).filter_by(
            version_id=version_id, file_id=file_id
        )
        if file_role:
            query = query.filter_by(file_role=file_role)

        vf = query.first()
        if not vf:
            return False

        was_primary = vf.is_primary
        self.session.delete(vf)

        # Update version
        version = self.session.get(ItemVersion, version_id)
        if version:
            version.file_count = max(0, (version.file_count or 1) - 1)
            if was_primary:
                version.primary_file_id = None
            self.session.add(version)

        self.session.flush()
        return True

    def get_version_files(self, version_id: str, role: str = None) -> List[VersionFile]:
        """
        Get all files attached to a version.

        Args:
            version_id: Target version ID
            role: Optional role filter

        Returns:
            List of VersionFile records with loaded File relationships
        """
        query = self.session.query(VersionFile).filter_by(version_id=version_id)
        if role:
            query = query.filter_by(file_role=role)
        return query.order_by(VersionFile.sequence).all()

    def set_primary_file(self, version_id: str, file_id: str) -> VersionFile:
        """
        Set a file as the primary file for a version.

        Args:
            version_id: Target version ID
            file_id: File to make primary

        Returns:
            Updated VersionFile record
        """
        # Clear existing primary
        self.session.query(VersionFile).filter_by(version_id=version_id).update(
            {"is_primary": False}
        )

        # Set new primary
        vf = (
            self.session.query(VersionFile)
            .filter_by(version_id=version_id, file_id=file_id)
            .first()
        )

        if not vf:
            raise VersionFileError(
                f"File {file_id} not attached to version {version_id}"
            )

        vf.is_primary = True
        self.session.add(vf)

        # Update version
        version = self.session.get(ItemVersion, version_id)
        if version:
            version.primary_file_id = file_id
            self.session.add(version)

        self.session.flush()
        return vf

    def sync_item_files_to_version(
        self,
        item_id: str,
        version_id: str,
        *,
        include_item_files: bool = True,
        extra_files: Optional[List[Dict[str, Any]]] = None,
        primary_file_id: Optional[str] = None,
        remove_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Sync ItemFile attachments to VersionFile records.

        This keeps version files aligned with current item attachments (and any
        extra files from version properties).
        """
        from yuantus.meta_engine.models.file import ItemFile
        from yuantus.meta_engine.models.item import Item

        version = self.session.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")

        item = self.session.get(Item, item_id)
        if not item:
            raise VersionFileError(f"Item {item_id} not found")

        item_files: List[ItemFile] = []
        if include_item_files:
            item_files = (
                self.session.query(ItemFile)
                .filter(ItemFile.item_id == item_id)
                .order_by(ItemFile.sequence.asc())
                .all()
            )

        desired: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for item_file in item_files:
            role = item_file.file_role or "attachment"
            desired[(item_file.file_id, role)] = {
                "file_id": item_file.file_id,
                "file_role": role,
                "sequence": item_file.sequence or 0,
                "source": "item",
            }

        if extra_files:
            for extra in extra_files:
                file_id = (extra or {}).get("file_id")
                if not file_id:
                    continue
                role = (extra or {}).get("file_role") or "attachment"
                key = (file_id, role)
                entry = desired.get(key, {})
                entry.update(
                    {
                        "file_id": file_id,
                        "file_role": role,
                        "sequence": (extra or {}).get("sequence", entry.get("sequence", 0)),
                        "is_primary": (extra or {}).get("is_primary", entry.get("is_primary", False)),
                        "source": entry.get("source") or "extra",
                    }
                )
                desired[key] = entry

        if not primary_file_id:
            for entry in desired.values():
                if entry.get("is_primary"):
                    primary_file_id = entry["file_id"]
                    break

        if not primary_file_id:
            preferred_roles = ["native_cad", "drawing", "geometry", "attachment"]
            for role in preferred_roles:
                for key, entry in desired.items():
                    if entry.get("file_role") == role:
                        primary_file_id = entry["file_id"]
                        break
                if primary_file_id:
                    break

        existing = (
            self.session.query(VersionFile).filter_by(version_id=version_id).all()
        )
        existing_map = {(vf.file_id, vf.file_role): vf for vf in existing}

        desired_keys = set(desired.keys())
        primary_set = False

        created = 0
        updated = 0
        removed = 0
        skipped = 0

        for key, entry in desired.items():
            file_id = entry["file_id"]
            file_role = entry["file_role"]
            file = self.session.get(FileContainer, file_id)
            if not file:
                if entry.get("source") == "item":
                    raise VersionFileError(f"File {file_id} not found")
                skipped += 1
                continue

            is_primary = False
            if primary_file_id and not primary_set and file_id == primary_file_id:
                is_primary = True
                primary_set = True

            existing_vf = existing_map.get(key)
            if existing_vf:
                existing_vf.sequence = entry.get("sequence", existing_vf.sequence)
                existing_vf.snapshot_path = file.system_path
                existing_vf.is_primary = is_primary
                self.session.add(existing_vf)
                updated += 1
            else:
                vf = VersionFile(
                    id=str(uuid.uuid4()),
                    version_id=version_id,
                    file_id=file_id,
                    file_role=file_role,
                    sequence=entry.get("sequence", 0),
                    snapshot_path=file.system_path,
                    is_primary=is_primary,
                    created_at=datetime.utcnow(),
                )
                self.session.add(vf)
                created += 1

        if remove_missing:
            for key, vf in existing_map.items():
                if key not in desired_keys:
                    self.session.delete(vf)
                    removed += 1

        # Update version summary fields
        current_count = (
            self.session.query(VersionFile).filter_by(version_id=version_id).count()
        )
        version.file_count = current_count
        version.primary_file_id = primary_file_id if primary_set else None
        self.session.add(version)
        self.session.flush()

        return {
            "version_id": version_id,
            "file_count": current_count,
            "created": created,
            "updated": updated,
            "removed": removed,
            "skipped": skipped,
            "primary_file_id": version.primary_file_id,
        }

    def sync_version_files_to_item(
        self,
        version_id: str,
        item_id: str,
        *,
        remove_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Sync VersionFile records back to ItemFile attachments.
        Useful when switching current version (e.g. ECO apply).
        """
        from yuantus.meta_engine.models.file import ItemFile
        from yuantus.meta_engine.models.item import Item

        version = self.session.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")

        item = self.session.get(Item, item_id)
        if not item:
            raise VersionFileError(f"Item {item_id} not found")

        if version.item_id != item_id:
            raise VersionFileError(
                f"Version {version_id} does not belong to item {item_id}"
            )

        version_files = (
            self.session.query(VersionFile)
            .filter_by(version_id=version_id)
            .order_by(VersionFile.sequence.asc())
            .all()
        )

        desired: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for vf in version_files:
            desired[(vf.file_id, vf.file_role)] = {
                "file_id": vf.file_id,
                "file_role": vf.file_role,
                "sequence": vf.sequence or 0,
            }

        existing = (
            self.session.query(ItemFile).filter_by(item_id=item_id).all()
        )
        existing_map = {(it.file_id, it.file_role): it for it in existing}

        desired_keys = set(desired.keys())
        created = 0
        updated = 0
        removed = 0

        for key, entry in desired.items():
            file_id = entry["file_id"]
            file = self.session.get(FileContainer, file_id)
            if not file:
                raise VersionFileError(f"File {file_id} not found")

            existing_item = existing_map.get(key)
            if existing_item:
                existing_item.sequence = entry.get("sequence", existing_item.sequence or 0)
                self.session.add(existing_item)
                updated += 1
            else:
                item_file = ItemFile(
                    id=str(uuid.uuid4()),
                    item_id=item_id,
                    file_id=file_id,
                    file_role=entry["file_role"],
                    sequence=entry.get("sequence", 0),
                )
                self.session.add(item_file)
                created += 1

        if remove_missing:
            for key, item_file in existing_map.items():
                if key not in desired_keys:
                    self.session.delete(item_file)
                    removed += 1

        self.session.flush()
        return {
            "item_id": item_id,
            "version_id": version_id,
            "created": created,
            "updated": updated,
            "removed": removed,
        }

    def copy_files_to_version(
        self,
        source_version_id: str,
        target_version_id: str,
        include_roles: List[str] = None,
    ) -> List[VersionFile]:
        """
        Copy all file associations from one version to another.
        Used when creating revisions or branches.

        Args:
            source_version_id: Source version to copy from
            target_version_id: Target version to copy to
            include_roles: Optional list of roles to include (default: all)

        Returns:
            List of newly created VersionFile records
        """
        query = self.session.query(VersionFile).filter_by(version_id=source_version_id)
        if include_roles:
            query = query.filter(VersionFile.file_role.in_(include_roles))

        source_files = query.all()
        new_files = []

        for sf in source_files:
            vf = VersionFile(
                id=str(uuid.uuid4()),
                version_id=target_version_id,
                file_id=sf.file_id,
                file_role=sf.file_role,
                sequence=sf.sequence,
                snapshot_path=sf.snapshot_path,
                is_primary=sf.is_primary,
                created_at=datetime.utcnow(),
            )
            self.session.add(vf)
            new_files.append(vf)

        # Update target version
        target_version = self.session.get(ItemVersion, target_version_id)
        if target_version and new_files:
            target_version.file_count = len(new_files)
            # Copy primary file reference
            primary = next((vf for vf in new_files if vf.is_primary), None)
            if primary:
                target_version.primary_file_id = primary.file_id
            self.session.add(target_version)

        self.session.flush()
        return new_files

    def compare_version_files(
        self, version_a_id: str, version_b_id: str
    ) -> Dict[str, Any]:
        """
        Compare files between two versions.

        Args:
            version_a_id: First version ID
            version_b_id: Second version ID

        Returns:
            Dictionary with added, removed, and modified files
        """
        files_a = {
            (vf.file_id, vf.file_role): vf
            for vf in self.get_version_files(version_a_id)
        }
        files_b = {
            (vf.file_id, vf.file_role): vf
            for vf in self.get_version_files(version_b_id)
        }

        keys_a = set(files_a.keys())
        keys_b = set(files_b.keys())

        added = []
        removed = []
        modified = []

        # Files only in B (added)
        for key in keys_b - keys_a:
            vf = files_b[key]
            added.append(
                {
                    "file_id": vf.file_id,
                    "file_role": vf.file_role,
                    "filename": vf.file.filename if vf.file else None,
                }
            )

        # Files only in A (removed)
        for key in keys_a - keys_b:
            vf = files_a[key]
            removed.append(
                {
                    "file_id": vf.file_id,
                    "file_role": vf.file_role,
                    "filename": vf.file.filename if vf.file else None,
                }
            )

        # Files in both - check for modifications
        for key in keys_a & keys_b:
            vf_a = files_a[key]
            vf_b = files_b[key]

            # Compare based on checksum or snapshot path
            file_a = self.session.get(FileContainer, vf_a.file_id)
            file_b = self.session.get(FileContainer, vf_b.file_id)

            if file_a and file_b:
                if file_a.checksum != file_b.checksum:
                    modified.append(
                        {
                            "file_id": vf_a.file_id,
                            "file_role": vf_a.file_role,
                            "filename": file_a.filename,
                            "checksum_a": file_a.checksum,
                            "checksum_b": file_b.checksum,
                        }
                    )

        return {
            "version_a": version_a_id,
            "version_b": version_b_id,
            "added": added,
            "removed": removed,
            "modified": modified,
            "summary": {
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
            },
        }

    def get_version_detail(self, version_id: str) -> Dict[str, Any]:
        """
        Get complete version information including files.

        Args:
            version_id: Version ID

        Returns:
            Dictionary with version data and file list
        """
        version = self.session.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")

        files = self.get_version_files(version_id)

        # Group files by role
        files_by_role = {}
        for vf in files:
            role = vf.file_role
            if role not in files_by_role:
                files_by_role[role] = []
            files_by_role[role].append(
                {
                    "id": vf.id,
                    "file_id": vf.file_id,
                    "filename": vf.file.filename if vf.file else None,
                    "file_type": vf.file.file_type if vf.file else None,
                    "file_size": vf.file.file_size if vf.file else None,
                    "is_primary": vf.is_primary,
                    "sequence": vf.sequence,
                }
            )

        return {
            "id": version.id,
            "item_id": version.item_id,
            "generation": version.generation,
            "revision": version.revision,
            "version_label": version.version_label,
            "state": version.state,
            "is_current": version.is_current,
            "is_released": version.is_released,
            "branch_name": version.branch_name,
            "predecessor_id": version.predecessor_id,
            "file_count": version.file_count or 0,
            "primary_file_id": version.primary_file_id,
            "thumbnail_data": version.thumbnail_data,
            "properties": version.properties,
            "created_at": (
                version.created_at.isoformat() if version.created_at else None
            ),
            "files": files_by_role,
        }

    def set_thumbnail(self, version_id: str, thumbnail_data: str) -> ItemVersion:
        """
        Set the thumbnail for a version.

        Args:
            version_id: Version ID
            thumbnail_data: Base64 encoded thumbnail image

        Returns:
            Updated version
        """
        version = self.session.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")

        version.thumbnail_data = thumbnail_data
        self.session.add(version)
        self.session.flush()
        return version
