from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from backend.app.connectors.nasa_power_connector import nasa_power_connector
from backend.app.connectors.owid_energy_connector import owid_energy_connector
from backend.app.connectors.open_meteo_connector import open_meteo_connector
from backend.app.database.db_manager import db_manager

router = APIRouter(prefix="/sources", tags=["External Data Sources"])

class NasaSyncRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: str # YYYYMMDD
    end_date: str   # YYYYMMDD
    plant_id: Optional[str] = None

class OwidSyncRequest(BaseModel):
    target_years: Optional[List[int]] = [2020, 2021, 2022, 2023]
    max_records: Optional[int] = 300
    force_download: Optional[bool] = False

class OpenMeteoSyncRequest(BaseModel):
    plant_id: str
    latitude: float
    longitude: float
    forecast_days: Optional[int] = 2

@router.get("/status")
def get_sources_status() -> List[Dict[str, Any]]:
    return db_manager.get_data_sources()

@router.post("/nasa-power/sync")
def sync_nasa_power_data(req: NasaSyncRequest) -> Dict[str, Any]:
    return nasa_power_connector.fetch_historical_data(
        latitude=req.latitude,
        longitude=req.longitude,
        start_date=req.start_date,
        end_date=req.end_date,
        plant_id=req.plant_id
    )

@router.post("/owid/sync")
def sync_owid_energy_data(req: OwidSyncRequest) -> Dict[str, Any]:
    return owid_energy_connector.ingest_owid_data(
        target_years=req.target_years,
        max_records=req.max_records or 300,
        force_download=req.force_download or False
    )

@router.post("/open-meteo/sync")
def sync_open_meteo_weather(req: OpenMeteoSyncRequest) -> Dict[str, Any]:
    return open_meteo_connector.fetch_weather_for_plant(
        plant_id=req.plant_id,
        latitude=req.latitude,
        longitude=req.longitude,
        forecast_days=req.forecast_days or 2
    )

@router.get("/metadata")
def get_sources_metadata() -> List[Dict[str, Any]]:
    conn = db_manager._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM data_source_metadata")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
