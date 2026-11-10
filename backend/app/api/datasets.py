import hashlib
import logging
import shutil
import threading
import uuid
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from supabase import Client, create_client

from backend.app.core.config import BASE_DIR, settings
from backend.app.core.security import require_supabase_user
from backend.app.database.dataset_repository import dataset_repository
from spark_engine.core.spark_manager import spark_manager
from spark_engine.jobs.dataset_rdd_processor import DatasetRddProcessor
from spark_engine.jobs.pipeline_runner import spark_pipeline_runner

logger = logging.getLogger("dataset_uploads")
router = APIRouter(prefix="/datasets", tags=["Datasets & Ingestion"])

UPLOAD_DIR = Path(settings.DATASET_UPLOAD_DIR)
if not UPLOAD_DIR.is_absolute():
    UPLOAD_DIR = BASE_DIR / UPLOAD_DIR
UPLOAD_DIR = UPLOAD_DIR.resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_MAX_UPLOAD_BYTES = settings.DATASET_MAX_UPLOAD_MB * 1024 * 1024
_ALLOWED_FORMATS = {"csv", "xlsx", "xls", "json"}
_ALLOWED_SOURCES = {"solar", "wind", "hydropower", "geothermal", "biomass", "other"}
_TERMINAL_STATES = {"completed", "failed", "cancelled"}
_PUBLIC_DATASET_FIELDS = {
    "id",
    "original_filename",
    "description",
    "file_format",
    "energy_source",
    "file_size_bytes",
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
}
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dataset-spark")
_processing_lock = threading.Lock()
_processing: Dict[str, Future] = {}
_cancelled: Set[str] = set()
_processor = DatasetRddProcessor(dataset_repository)


class DatasetProcessingCancelled(Exception):
    pass


@lru_cache(maxsize=1)
def _storage_client() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Supabase Storage is configured without backend service credentials.",
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def _storage_object_path(owner_id: str, dataset_id: str, suffix: str) -> str:
    return f"{owner_id}/{dataset_id}.{suffix}"


def _remove_storage_object(bucket: str, object_path: str) -> None:
    try:
        _storage_client().storage.from_(bucket).remove([object_path])
    except Exception:
        logger.exception("Could not remove Supabase Storage object %s.", object_path)


def _owner_id(user: Any) -> str:
    return str(user.id)


def _public_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in dataset.items()
        if key in _PUBLIC_DATASET_FIELDS
    }


def _is_cancelled(dataset_id: str) -> bool:
    with _processing_lock:
        return dataset_id in _cancelled


def _safe_local_path(dataset: Dict[str, Any]) -> Path:
    path = Path(dataset["storage_location"]).resolve()
    try:
        path.relative_to(UPLOAD_DIR)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Dataset storage path is invalid.") from error
    return path


def _check_file_content(path: Path, file_format: str, mime_type: Optional[str]) -> None:
    allowed_mimes = {
        "csv": {"text/csv", "application/csv", "text/plain", "application/octet-stream"},
        "json": {"application/json", "text/json", "text/plain", "application/octet-stream"},
        "xlsx": {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",
            "application/octet-stream",
        },
        "xls": {"application/vnd.ms-excel", "application/octet-stream"},
    }
    if mime_type and mime_type.lower() not in allowed_mimes[file_format]:
        raise HTTPException(status_code=415, detail="The declared MIME type does not match the supported file format.")
    with path.open("rb") as stream:
        prefix = stream.read(65536)
    if file_format == "csv":
        if not prefix or b"\x00" in prefix:
            raise HTTPException(status_code=400, detail="The file content is not valid CSV text.")
        try:
            prefix.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise HTTPException(status_code=400, detail="CSV uploads must use UTF-8 encoding.") from error
    elif file_format == "json":
        stripped = prefix.lstrip()
        if not stripped or stripped[:1] not in {b"{", b"["}:
            raise HTTPException(status_code=400, detail="The file content is not a JSON object or array.")
    elif file_format == "xlsx":
        if not prefix.startswith(b"PK"):
            raise HTTPException(status_code=400, detail="The file is not a valid XLSX workbook.")
        try:
            with zipfile.ZipFile(path) as workbook:
                names = set(workbook.namelist())
                if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                    raise HTTPException(status_code=400, detail="The XLSX workbook structure is invalid.")
                uncompressed_size = sum(info.file_size for info in workbook.infolist())
                if len(names) > 5000 or uncompressed_size > 1024 * 1024 * 1024 or any(
                    info.file_size > 250 * 1024 * 1024
                    or (info.compress_size and info.file_size / info.compress_size > 200)
                    for info in workbook.infolist()
                ):
                    raise HTTPException(status_code=400, detail="The XLSX workbook exceeds safe decompression limits.")
        except zipfile.BadZipFile as error:
            raise HTTPException(status_code=400, detail="The XLSX workbook is corrupted.") from error
    elif file_format == "xls" and not prefix.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        raise HTTPException(status_code=400, detail="The file is not a valid legacy XLS workbook.")


def _schedule_processing(dataset_id: str, owner_id: str) -> None:
    with _processing_lock:
        current = _processing.get(dataset_id)
        if current and not current.done():
            return
        _cancelled.discard(dataset_id)
        future = _executor.submit(_process_dataset, dataset_id, owner_id)
        _processing[dataset_id] = future


def _process_dataset(dataset_id: str, owner_id: str) -> None:
    dataset = dataset_repository.get(dataset_id, owner_id)
    if not dataset:
        return
    try:
        path = _safe_local_path(dataset)

        def update_stage(status: str, stage: str) -> None:
            if _is_cancelled(dataset_id):
                raise DatasetProcessingCancelled()
            dataset_repository.update(
                dataset_id,
                owner_id,
                {"processing_status": status, "progress_stage": stage, "processing_error": None},
            )

        _processor.process(
            dataset,
            path,
            update_stage,
        )
    except DatasetProcessingCancelled:
        dataset_repository.update(
            dataset_id, owner_id,
            {"processing_status": "cancelled", "progress_stage": "cancelled"},
        )
    except Exception as error:
        logger.exception("Dataset processing failed for dataset %s", dataset_id)
        if _is_cancelled(dataset_id):
            dataset_repository.update(
                dataset_id, owner_id,
                {"processing_status": "cancelled", "progress_stage": "cancelled"},
            )
            return
        dataset_repository.update(
            dataset_id,
            owner_id,
            {
                "processing_status": "failed",
                "progress_stage": "failed",
                "processing_error": str(error)[:2000],
            },
        )
    finally:
        with _processing_lock:
            _processing.pop(dataset_id, None)
            _cancelled.discard(dataset_id)


def _dataset_or_404(dataset_id: str, user: Any) -> Dict[str, Any]:
    dataset = dataset_repository.get(dataset_id, _owner_id(user))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.get("")
def list_datasets(
    energy_source: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: Any = Depends(require_supabase_user),
) -> Dict[str, Any]:
    datasets = [
        _public_dataset(dataset)
        for dataset in dataset_repository.list(_owner_id(user), limit, offset)
    ]
    if energy_source:
        datasets = [
            dataset for dataset in datasets
            if dataset["energy_source"] == energy_source.lower()
        ]
    return {"datasets": datasets, "limit": limit, "offset": offset}


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, user: Any = Depends(require_supabase_user)) -> Dict[str, Any]:
    return _public_dataset(_dataset_or_404(dataset_id, user))


@router.post("/upload", status_code=202)
async def upload_dataset_file(
    file: UploadFile = File(...),
    energy_source: str = Form(...),
    description: str = Form(""),
    user: Any = Depends(require_supabase_user),
) -> Dict[str, Any]:
    original_filename = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    suffix = Path(original_filename).suffix.lower().lstrip(".")
    if suffix not in _ALLOWED_FORMATS:
        raise HTTPException(status_code=415, detail="Supported formats are CSV, XLSX, XLS, and JSON.")
    source = energy_source.lower().strip()
    if source not in _ALLOWED_SOURCES:
        raise HTTPException(status_code=400, detail="Unsupported renewable energy source.")
    if len(description) > 2000:
        raise HTTPException(status_code=400, detail="Description must be at most 2,000 characters.")
    if not original_filename or len(original_filename) > 255:
        raise HTTPException(status_code=400, detail="Filename must be between 1 and 255 characters.")

    dataset_id = str(uuid.uuid4())
    target_path = (UPLOAD_DIR / f"{dataset_id}.{suffix}").resolve()
    partial_path = target_path.with_suffix(target_path.suffix + ".uploading")
    digest = hashlib.sha256()
    total_bytes = 0
    object_path = None
    storage_bucket = settings.SUPABASE_DATASET_STORAGE_BUCKET.strip()
    try:
        with partial_path.open("xb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > _MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {settings.DATASET_MAX_UPLOAD_MB} MB upload limit.",
                    )
                digest.update(chunk)
                output.write(chunk)
        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Empty files cannot be uploaded.")
        _check_file_content(partial_path, suffix, file.content_type)
        checksum = digest.hexdigest()
        owner_id = _owner_id(user)
        duplicate = dataset_repository.find_by_checksum(owner_id, checksum)
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail={"message": "This file has already been uploaded.", "dataset_id": duplicate["id"]},
            )
        partial_path.replace(target_path)
        if storage_bucket:
            storage_client = _storage_client()
            object_path = _storage_object_path(owner_id, dataset_id, suffix)
            storage_client.storage.from_(storage_bucket).upload(
                object_path,
                target_path,
                file_options={
                    "content-type": file.content_type or "application/octet-stream",
                    "upsert": "false",
                },
            )
        dataset = dataset_repository.create(
            {
                "id": dataset_id,
                "owner_id": owner_id,
                "original_filename": original_filename,
                "description": description.strip(),
                "file_format": suffix,
                "energy_source": source,
                "file_size_bytes": total_bytes,
                "sha256": checksum,
                "storage_location": str(target_path),
                "processing_status": "queued",
                "progress_stage": "upload_complete",
            }
        )
    except HTTPException:
        partial_path.unlink(missing_ok=True)
        target_path.unlink(missing_ok=True)
        if object_path and storage_bucket:
            _remove_storage_object(storage_bucket, object_path)
        raise
    except Exception as error:
        partial_path.unlink(missing_ok=True)
        target_path.unlink(missing_ok=True)
        if object_path and storage_bucket:
            _remove_storage_object(storage_bucket, object_path)
        logger.exception("Dataset upload could not be persisted.")
        raise HTTPException(status_code=500, detail="Dataset upload could not be persisted.") from error
    finally:
        await file.close()

    _schedule_processing(dataset_id, _owner_id(user))
    return {
        "status": "queued",
        "message": "Upload accepted; Spark schema detection and processing started.",
        "dataset": _public_dataset(dataset),
    }


@router.get("/{dataset_id}/status")
def get_dataset_status(dataset_id: str, user: Any = Depends(require_supabase_user)) -> Dict[str, Any]:
    dataset = _dataset_or_404(dataset_id, user)
    return {
        "id": dataset["id"],
        "processing_status": dataset["processing_status"],
        "progress_stage": dataset["progress_stage"],
        "total_records": dataset["total_records"],
        "valid_records": dataset["valid_records"],
        "warning_records": dataset["warning_records"],
        "invalid_records": dataset["invalid_records"],
        "duplicate_records": dataset["duplicate_records"],
        "processing_error": dataset["processing_error"],
    }


@router.post("/{dataset_id}/cancel", status_code=202)
def cancel_dataset_processing(
    dataset_id: str, user: Any = Depends(require_supabase_user)
) -> Dict[str, Any]:
    dataset = _dataset_or_404(dataset_id, user)
    if dataset["processing_status"] not in {"queued", "validating", "processing", "persisting"}:
        raise HTTPException(status_code=409, detail="Dataset processing is not active.")

    with _processing_lock:
        _cancelled.add(dataset_id)
        future = _processing.get(dataset_id)
        cancelled_before_start = bool(future and future.cancel())
        if cancelled_before_start:
            _processing.pop(dataset_id, None)
            _cancelled.discard(dataset_id)
        elif future is None or future.done():
            _cancelled.discard(dataset_id)

    spark_manager.cancel_job_group(f"dataset-{dataset_id}")
    dataset_repository.update(
        dataset_id,
        _owner_id(user),
        {"processing_status": "cancelled", "progress_stage": "cancelled"},
    )
    return {"status": "cancelled", "dataset_id": dataset_id}


@router.get("/{dataset_id}/preview")
def get_dataset_preview(
    dataset_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    classification: Optional[str] = Query(None, pattern="^(valid|warning|invalid|duplicate)$"),
    user: Any = Depends(require_supabase_user),
) -> Dict[str, Any]:
    _dataset_or_404(dataset_id, user)
    records, total = dataset_repository.preview(
        dataset_id, _owner_id(user), limit, offset, classification
    )
    return {"records": records, "total": total, "limit": limit, "offset": offset}


@router.get("/{dataset_id}/analytics")
def get_dataset_analytics(dataset_id: str, user: Any = Depends(require_supabase_user)) -> Dict[str, Any]:
    dataset = _dataset_or_404(dataset_id, user)
    return dataset.get("analytics") or {}


@router.get("/{dataset_id}/visualizations")
def get_dataset_visualizations(dataset_id: str, user: Any = Depends(require_supabase_user)) -> Dict[str, Any]:
    dataset = _dataset_or_404(dataset_id, user)
    analytics = dataset.get("analytics") or {}
    return {"available_charts": analytics.get("available_charts", []), "by_date": analytics.get("by_date", [])}


@router.get("/{dataset_id}/download")
def download_dataset(dataset_id: str, user: Any = Depends(require_supabase_user)):
    dataset = _dataset_or_404(dataset_id, user)
    path = _safe_local_path(dataset)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Original dataset file is no longer available.")
    return FileResponse(path, filename=dataset["original_filename"])


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str, user: Any = Depends(require_supabase_user)):
    dataset = _dataset_or_404(dataset_id, user)
    if dataset["processing_status"] not in _TERMINAL_STATES | {"queued"}:
        raise HTTPException(status_code=409, detail="Wait until processing completes before deleting this dataset.")
    with _processing_lock:
        future = _processing.get(dataset_id)
        if future and not future.done():
            raise HTTPException(status_code=409, detail="Cancel or wait for the active processing job before deleting this dataset.")
    storage_bucket = settings.SUPABASE_DATASET_STORAGE_BUCKET.strip()
    if storage_bucket:
        object_path = _storage_object_path(
            _owner_id(user), dataset_id, dataset["file_format"]
        )
        try:
            _storage_client().storage.from_(storage_bucket).remove([object_path])
        except Exception as error:
            logger.exception(
                "Could not remove Supabase Storage object for dataset %s.",
                dataset_id,
            )
            raise HTTPException(
                status_code=502,
                detail="Dataset metadata was kept because the mirrored file could not be removed.",
            ) from error
    removed = dataset_repository.delete(dataset_id, _owner_id(user))
    if removed:
        path = _safe_local_path(removed)
        path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.post("/{dataset_id}/process", status_code=202)
def trigger_dataset_spark_processing(dataset_id: str, user: Any = Depends(require_supabase_user)) -> Dict[str, Any]:
    dataset = _dataset_or_404(dataset_id, user)
    if dataset["processing_status"] not in _TERMINAL_STATES:
        raise HTTPException(status_code=409, detail="Dataset is already queued or processing.")
    path = _safe_local_path(dataset)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Original dataset file is no longer available.")
    dataset_repository.update(
        dataset_id,
        _owner_id(user),
        {
            "processing_status": "queued",
            "progress_stage": "queued",
            "processing_error": None,
        },
    )
    _schedule_processing(dataset_id, _owner_id(user))
    return {"status": "queued", "dataset_id": dataset_id}


@router.post("/process-sample")
def process_bundled_sample_dataset(
    energy_source: str = Query(..., description="solar, wind, hydropower, geothermal, biomass"),
    plant_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    src = energy_source.lower()
    sample_files = {
        "solar": ("bhadla_solar_telemetry.csv", "a0000001-0000-0000-0000-000000000001"),
        "wind": ("muppandal_wind_telemetry.csv", "a0000002-0000-0000-0000-000000000002"),
        "hydropower": ("tehri_hydro_telemetry.csv", "a0000003-0000-0000-0000-000000000003"),
        "geothermal": ("olkaria_geothermal_telemetry.csv", "a0000004-0000-0000-0000-000000000004"),
        "biomass": ("ironbridge_biomass_telemetry.csv", "a0000005-0000-0000-0000-000000000005"),
    }
    if src not in sample_files:
        raise HTTPException(status_code=400, detail=f"Invalid energy source {energy_source}")
    filename, default_plant_id = sample_files[src]
    target_plant_id = plant_id or default_plant_id
    file_path = BASE_DIR / "datasets" / src / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Bundled sample dataset file not found.")
    result = spark_pipeline_runner.execute_file_pipeline(
        file_path=str(file_path),
        energy_source=src,
        plant_id=target_plant_id,
    )
    return {
        "status": "success",
        "energy_source": src,
        "sample_file": filename,
        "spark_metrics": result,
    }
