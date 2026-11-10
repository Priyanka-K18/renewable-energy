from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from backend.app.database.db_manager import db_manager

router = APIRouter(prefix="/global-energy", tags=["Global Energy Statistics (OWID)"])

@router.get("/countries")
def list_available_countries() -> List[Dict[str, Any]]:
    conn = db_manager._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT country, iso_code FROM global_energy_statistics ORDER BY country ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@router.get("/generation")
def get_country_generation_statistics(
    country: Optional[str] = Query(None),
    iso_code: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200)
) -> List[Dict[str, Any]]:
    return db_manager.get_global_energy_statistics(
        country=country,
        iso_code=iso_code,
        year=year,
        limit=limit
    )

@router.get("/trends")
def get_global_trends(iso_code: str = Query("WLD")) -> List[Dict[str, Any]]:
    return db_manager.get_global_energy_statistics(iso_code=iso_code, limit=15)

@router.get("/india-vs-world")
def get_india_vs_world_comparison() -> Dict[str, Any]:
    india_stats = db_manager.get_global_energy_statistics(iso_code="IND", limit=1)
    world_stats = db_manager.get_global_energy_statistics(iso_code="WLD", limit=1)
    return {
        "india": india_stats[0] if india_stats else None,
        "world": world_stats[0] if world_stats else None,
        "source": "Our World in Data (OWID) Energy",
        "data_classification": "REAL_EXTERNAL_DATA"
    }
