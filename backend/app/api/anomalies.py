from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from backend.app.database.db_manager import db_manager

router = APIRouter(prefix="/anomalies", tags=["Intelligent Anomaly Detection"])

class AnomalyStatusUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str] = None

@router.get("")
def list_anomalies(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    energy_source: Optional[str] = Query(None),
    plant_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
) -> List[Dict[str, Any]]:
    return db_manager.get_anomalies(
        status=status,
        severity=severity,
        energy_source=energy_source,
        plant_id=plant_id,
        limit=limit
    )

@router.get("/{anomaly_id}")
def get_anomaly_detail(anomaly_id: str) -> Dict[str, Any]:
    conn = db_manager._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM anomaly_alerts WHERE id = ?", (anomaly_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Anomaly alert not found")
    return dict(row)

@router.patch("/{anomaly_id}/status")
def update_anomaly_status(anomaly_id: str, req: AnomalyStatusUpdate) -> Dict[str, Any]:
    valid_statuses = {
        "open": "Open",
        "investigating": "Investigating",
        "resolved": "Resolved",
        "ignored": "Ignored",
    }
    status = valid_statuses.get(req.status.strip().lower())
    if status is None:
        allowed_statuses = ", ".join(valid_statuses.values())
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {allowed_statuses}")
    
    success = db_manager.update_anomaly_status(anomaly_id, status, req.resolution_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    
    return {
        "status": "success",
        "anomaly_id": anomaly_id,
        "new_status": status,
        "notes": req.resolution_notes
    }
