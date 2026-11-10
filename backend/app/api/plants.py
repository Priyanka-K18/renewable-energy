from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from backend.app.database.db_manager import db_manager

router = APIRouter(prefix="/plants", tags=["Renewable Plants"])

class PlantCreateRequest(BaseModel):
    plant_name: str
    energy_source: str
    country: str
    state: Optional[str] = None
    location: str
    latitude: float
    longitude: float
    installed_capacity: float
    capacity_unit: Optional[str] = "MW"
    commissioning_date: Optional[str] = None
    status: Optional[str] = "active"
    operator_name: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = {}

@router.get("")
def list_plants(energy_source: Optional[str] = Query(None, description="solar, wind, hydropower, geothermal, biomass")) -> List[Dict[str, Any]]:
    return db_manager.get_plants(energy_source=energy_source)

@router.post("")
def create_plant(req: PlantCreateRequest) -> Dict[str, Any]:
    valid_sources = ["solar", "wind", "hydropower", "geothermal", "biomass"]
    if req.energy_source.lower() not in valid_sources:
        raise HTTPException(status_code=400, detail=f"Invalid energy_source. Must be one of {valid_sources}")
    return db_manager.create_plant(req.model_dump())

@router.get("/{plant_id}")
def get_plant_detail(plant_id: str) -> Dict[str, Any]:
    plant = db_manager.get_plant(plant_id)
    if not plant:
        raise HTTPException(status_code=404, detail="Renewable plant not found")
    equipment = db_manager.get_equipment(plant_id=plant_id)
    daily_summaries = db_manager.get_daily_summaries(plant_id=plant_id, limit=7)
    anomalies = db_manager.get_anomalies(plant_id=plant_id, limit=5)
    return {
        "plant": plant,
        "equipment": equipment,
        "recent_daily_summaries": daily_summaries,
        "recent_anomalies": anomalies
    }

@router.get("/{plant_id}/equipment")
def get_plant_equipment(plant_id: str) -> List[Dict[str, Any]]:
    return db_manager.get_equipment(plant_id=plant_id)
