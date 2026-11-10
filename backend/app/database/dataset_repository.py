import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.config import settings
from backend.app.database.db_manager import db_manager


_DATASET_COLUMNS = (
    "id",
    "owner_id",
    "original_filename",
    "description",
    "file_format",
    "energy_source",
    "file_size_bytes",
    "sha256",
    "storage_location",
    "processing_status",
    "progress_stage",
    "total_records",
    "valid_records",
    "warning_records",
    "invalid_records",
    "duplicate_records",
    "missing_values",
    "schema_report",
    "quality_report",
    "analytics",
    "processing_duration_seconds",
    "processing_error",
    "uploaded_at",
    "updated_at",
)
_JSON_FIELDS = {"missing_values", "schema_report", "quality_report", "analytics"}


class DatasetRepository:
    """Owner-scoped dataset persistence; SQLite remains the default adapter."""

    def __init__(self) -> None:
        self._init_sqlite()

    @property
    def use_supabase(self) -> bool:
        return (
            settings.SUPABASE_NORMALIZED_SCHEMA_ENABLED
            and db_manager.normalized_supabase_repository.enabled
        )

    def _init_sqlite(self) -> None:
        conn = db_manager._get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_datasets (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    file_format TEXT NOT NULL,
                    energy_source TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    storage_location TEXT NOT NULL,
                    processing_status TEXT NOT NULL DEFAULT 'queued',
                    progress_stage TEXT NOT NULL DEFAULT 'upload_complete',
                    total_records INTEGER NOT NULL DEFAULT 0,
                    valid_records INTEGER NOT NULL DEFAULT 0,
                    warning_records INTEGER NOT NULL DEFAULT 0,
                    invalid_records INTEGER NOT NULL DEFAULT 0,
                    duplicate_records INTEGER NOT NULL DEFAULT 0,
                    missing_values TEXT NOT NULL DEFAULT '{}',
                    schema_report TEXT NOT NULL DEFAULT '{}',
                    quality_report TEXT NOT NULL DEFAULT '{}',
                    analytics TEXT NOT NULL DEFAULT '{}',
                    processing_duration_seconds REAL,
                    processing_error TEXT,
                    uploaded_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(owner_id, sha256)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_dataset_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT NOT NULL REFERENCES uploaded_datasets(id) ON DELETE CASCADE,
                    row_number INTEGER NOT NULL,
                    classification TEXT NOT NULL,
                    issues TEXT NOT NULL DEFAULT '[]',
                    record TEXT NOT NULL,
                    UNIQUE(dataset_id, row_number)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_uploaded_datasets_owner_uploaded "
                "ON uploaded_datasets(owner_id, uploaded_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_uploaded_dataset_records_page "
                "ON uploaded_dataset_records(dataset_id, row_number)"
            )
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()
        finally:
            conn.close()

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        dataset = dict(data)
        dataset.setdefault("id", str(uuid.uuid4()))
        now = datetime.now(timezone.utc).isoformat()
        dataset.setdefault("uploaded_at", now)
        dataset.setdefault("updated_at", now)
        dataset.setdefault("processing_status", "queued")
        dataset.setdefault("progress_stage", "upload_complete")
        for field in (
            "total_records",
            "valid_records",
            "warning_records",
            "invalid_records",
            "duplicate_records",
        ):
            dataset.setdefault(field, 0)
        dataset.setdefault("processing_duration_seconds", None)
        dataset.setdefault("processing_error", None)
        for field in _JSON_FIELDS:
            dataset.setdefault(field, {})

        if self.use_supabase:
            repo = db_manager.normalized_supabase_repository
            return repo.create_uploaded_dataset(dataset)

        columns = ", ".join(_DATASET_COLUMNS)
        placeholders = ", ".join("?" for _ in _DATASET_COLUMNS)
        values = [
            json.dumps(dataset[name], separators=(",", ":"))
            if name in _JSON_FIELDS
            else dataset.get(name)
            for name in _DATASET_COLUMNS
        ]
        conn = db_manager._get_connection()
        try:
            conn.execute(
                f"INSERT INTO uploaded_datasets ({columns}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
        finally:
            conn.close()
        return dataset

    def get(self, dataset_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase:
            return db_manager.normalized_supabase_repository.get_uploaded_dataset(
                dataset_id, owner_id
            )
        conn = db_manager._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM uploaded_datasets WHERE id = ? AND owner_id = ?",
                (dataset_id, owner_id),
            ).fetchone()
            return self._decode_dataset(dict(row)) if row else None
        finally:
            conn.close()

    def find_by_checksum(self, owner_id: str, checksum: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase:
            return db_manager.normalized_supabase_repository.find_uploaded_dataset_by_checksum(
                owner_id, checksum
            )
        conn = db_manager._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM uploaded_datasets WHERE owner_id = ? AND sha256 = ?",
                (owner_id, checksum),
            ).fetchone()
            return self._decode_dataset(dict(row)) if row else None
        finally:
            conn.close()

    def list(self, owner_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        if self.use_supabase:
            return db_manager.normalized_supabase_repository.list_uploaded_datasets(
                owner_id, limit, offset
            )
        conn = db_manager._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM uploaded_datasets WHERE owner_id = ? "
                "ORDER BY uploaded_at DESC LIMIT ? OFFSET ?",
                (owner_id, limit, offset),
            ).fetchall()
            return [self._decode_dataset(dict(row)) for row in rows]
        finally:
            conn.close()

    def update(self, dataset_id: str, owner_id: str, values: Dict[str, Any]) -> bool:
        allowed = {
            "processing_status",
            "progress_stage",
            "total_records",
            "valid_records",
            "warning_records",
            "invalid_records",
            "duplicate_records",
            "missing_values",
            "schema_report",
            "quality_report",
            "analytics",
            "processing_duration_seconds",
            "processing_error",
        }
        updates = {key: value for key, value in values.items() if key in allowed}
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.use_supabase:
            return db_manager.normalized_supabase_repository.update_uploaded_dataset(
                dataset_id, owner_id, updates
            )
        assignments = ", ".join(f"{key} = ?" for key in updates)
        params = [
            json.dumps(value, separators=(",", ":")) if key in _JSON_FIELDS else value
            for key, value in updates.items()
        ]
        params.extend([dataset_id, owner_id])
        conn = db_manager._get_connection()
        try:
            cursor = conn.execute(
                f"UPDATE uploaded_datasets SET {assignments} WHERE id = ? AND owner_id = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def insert_records(self, dataset_id: str, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        if self.use_supabase:
            db_manager.normalized_supabase_repository.insert_uploaded_dataset_records(
                dataset_id, rows
            )
            return
        conn = db_manager._get_connection()
        try:
            conn.executemany(
                "INSERT OR REPLACE INTO uploaded_dataset_records "
                "(dataset_id, row_number, classification, issues, record) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        dataset_id,
                        row["row_number"],
                        row["classification"],
                        json.dumps(row["issues"], separators=(",", ":")),
                        json.dumps(row["record"], separators=(",", ":"), default=str),
                    )
                    for row in rows
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def preview(
        self,
        dataset_id: str,
        owner_id: str,
        limit: int,
        offset: int,
        classification: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        if self.use_supabase:
            return db_manager.normalized_supabase_repository.preview_uploaded_dataset_records(
                dataset_id, owner_id, limit, offset, classification
            )
        conn = db_manager._get_connection()
        try:
            if classification:
                total = conn.execute(
                    "SELECT COUNT(*) FROM uploaded_dataset_records "
                    "WHERE dataset_id = ? AND classification = ?",
                    (dataset_id, classification),
                ).fetchone()[0]
                rows = conn.execute(
                    "SELECT row_number, classification, issues, record "
                    "FROM uploaded_dataset_records WHERE dataset_id = ? AND classification = ? "
                    "ORDER BY row_number LIMIT ? OFFSET ?",
                    (dataset_id, classification, limit, offset),
                ).fetchall()
            else:
                total = conn.execute(
                    "SELECT COUNT(*) FROM uploaded_dataset_records WHERE dataset_id = ?",
                    (dataset_id,),
                ).fetchone()[0]
                rows = conn.execute(
                    "SELECT row_number, classification, issues, record "
                    "FROM uploaded_dataset_records WHERE dataset_id = ? "
                    "ORDER BY row_number LIMIT ? OFFSET ?",
                    (dataset_id, limit, offset),
                ).fetchall()
            return (
                [
                    {
                        "row_number": row["row_number"],
                        "classification": row["classification"],
                        "issues": json.loads(row["issues"]),
                        "record": json.loads(row["record"]),
                    }
                    for row in rows
                ],
                total,
            )
        finally:
            conn.close()

    def delete(self, dataset_id: str, owner_id: str) -> Optional[Dict[str, Any]]:
        if self.use_supabase:
            return db_manager.normalized_supabase_repository.delete_uploaded_dataset(
                dataset_id, owner_id
            )
        conn = db_manager._get_connection()
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN")
            row = conn.execute(
                "SELECT * FROM uploaded_datasets WHERE id = ? AND owner_id = ?",
                (dataset_id, owner_id),
            ).fetchone()
            if row is None:
                conn.rollback()
                return None
            dataset = self._decode_dataset(dict(row))
            conn.execute(
                "DELETE FROM uploaded_dataset_records WHERE dataset_id = ?",
                (dataset_id,),
            )
            conn.execute(
                "DELETE FROM uploaded_datasets WHERE id = ? AND owner_id = ?",
                (dataset_id, owner_id),
            )
            conn.commit()
            return dataset
        finally:
            conn.close()

    @staticmethod
    def _decode_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
        for field in _JSON_FIELDS:
            value = dataset.get(field)
            if isinstance(value, str):
                dataset[field] = json.loads(value)
        return dataset


dataset_repository = DatasetRepository()
