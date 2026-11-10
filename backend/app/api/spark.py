from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from backend.app.database.db_manager import db_manager

router = APIRouter(prefix="/spark", tags=["Apache Spark RDD Processing Monitor"])

@router.get("/jobs")
def list_spark_jobs(limit: int = Query(25, ge=1, le=100)) -> List[Dict[str, Any]]:
    return db_manager.get_processing_jobs(limit=limit)

@router.get("/jobs/{job_id}")
def get_spark_job_detail(job_id: str) -> Dict[str, Any]:
    conn = db_manager._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM processing_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Spark job not found")
    return dict(row)

@router.get("/metrics")
def get_spark_engine_metrics() -> Dict[str, Any]:
    jobs = db_manager.get_processing_jobs(limit=50)
    total_processed = sum(j.get("records_processed", 0) for j in jobs)
    total_rejected = sum(j.get("records_rejected", 0) for j in jobs)
    completed_jobs = sum(1 for j in jobs if j.get("job_status") == "completed")
    failed_jobs = sum(1 for j in jobs if j.get("job_status") == "failed")
    
    avg_throughput = 0.0
    valid_tp = [j.get("throughput_records_per_sec", 0.0) for j in jobs if j.get("throughput_records_per_sec", 0.0) > 0]
    if valid_tp:
        avg_throughput = round(sum(valid_tp) / len(valid_tp), 2)

    return {
        "engine": "Apache Spark 3.5 / PySpark RDD Core",
        "cluster_master": "local[*]",
        "total_jobs_tracked": len(jobs),
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "total_records_processed": total_processed,
        "total_records_rejected": total_rejected,
        "average_throughput_records_sec": avg_throughput,
        "active_jobs": [j for j in jobs if j.get("job_status") == "running"],
        "recent_jobs": jobs[:5]
    }
