from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any, Optional
from backend.app.database.db_manager import db_manager

router = APIRouter(prefix="/weather", tags=["Live Weather & Environmental Intelligence"])

@router.get("/current")
def get_current_weather(plant_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    obs = db_manager.get_weather_observations(plant_id=plant_id, observation_type="current", limit=1)
    if not obs:
        # Fallback to general current observation
        obs = db_manager.get_weather_observations(observation_type="current", limit=1)
    return {
        "status": "success",
        "data": obs[0] if obs else None,
        "source": "Open-Meteo",
        "data_classification": "REAL_EXTERNAL_DATA"
    }

@router.get("/forecast")
def get_weather_forecast(plant_id: Optional[str] = Query(None), hours: int = Query(24, ge=1, le=48)) -> List[Dict[str, Any]]:
    return db_manager.get_weather_observations(plant_id=plant_id, observation_type="forecast_hourly", limit=hours)

@router.get("/history")
def get_historical_environmental_context(plant_id: Optional[str] = Query(None), limit: int = Query(30, ge=1, le=90)) -> List[Dict[str, Any]]:
    """
    Returns historical solar radiation, wind speed, temperature and precipitation from NASA POWER.
    """
    return db_manager.get_environmental_observations(plant_id=plant_id, limit=limit)
