import io
import csv
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional

from backend.app.database.db_manager import db_manager

router = APIRouter(prefix="/reports", tags=["Intelligent Reporting & Exports"])

class ReportGenerateRequest(BaseModel):
    report_type: str # overall, solar, wind, hydro, geothermal, biomass, anomalies, spark, owid, weather
    export_format: str = "json" # json, csv
    plant_id: Optional[str] = None
    time_period: Optional[str] = "Last 30 Days"

@router.get("/overview")
def get_available_report_types() -> List[Dict[str, Any]]:
    return [
        {"id": "overall", "title": "Comprehensive Renewable Energy Executive Summary", "category": "Executive", "formats": ["json", "csv"]},
        {"id": "solar", "title": "Solar Photovoltaic Generation & Inverter Health Audit", "category": "Source Intelligence", "formats": ["json", "csv"]},
        {"id": "wind", "title": "Wind Farm Aerodynamic & Turbine Performance Report", "category": "Source Intelligence", "formats": ["json", "csv"]},
        {"id": "hydropower", "title": "Hydroelectric Complex Hydraulic Head & Flow Analysis", "category": "Source Intelligence", "formats": ["json", "csv"]},
        {"id": "geothermal", "title": "Geothermal Reservoir Thermodynamics & Mass Flow Audit", "category": "Source Intelligence", "formats": ["json", "csv"]},
        {"id": "biomass", "title": "Biomass CFB Boiler Combustion & Feedstock Moisture Report", "category": "Source Intelligence", "formats": ["json", "csv"]},
        {"id": "anomalies", "title": "Operational Incident & Anomaly Alert Log", "category": "Reliability", "formats": ["json", "csv"]},
        {"id": "spark", "title": "Apache Spark Distributed Processing & Job Metrics", "category": "Big Data Infrastructure", "formats": ["json", "csv"]},
        {"id": "owid", "title": "Global Renewable Electricity Mix (OWID Energy)", "category": "Global Benchmarks", "formats": ["json", "csv"]},
        {"id": "weather", "title": "Plant-Specific Meteorological & Resource Conditions", "category": "Environmental", "formats": ["json", "csv"]}
    ]

@router.post("/generate")
def generate_report(req: ReportGenerateRequest):
    now_str = datetime.now(timezone.utc).isoformat()
    r_type = req.report_type.lower()

    if r_type == "overall":
        kpis = db_manager.get_overview_kpis()
        plants = db_manager.get_plants()
        anomalies = db_manager.get_anomalies(limit=10)
        report_data = {
            "report_title": "Comprehensive Renewable Energy Executive Summary",
            "generation_timestamp": now_str,
            "data_classification": "DERIVED_ANALYTICS",
            "kpis": kpis,
            "registered_plants": plants,
            "recent_anomalies": anomalies
        }

    elif r_type in ("solar", "wind", "hydropower", "geothermal", "biomass"):
        plants = db_manager.get_plants(energy_source=r_type)
        daily = db_manager.get_daily_summaries(plant_id=req.plant_id, energy_source=r_type, limit=30)
        anomalies = db_manager.get_anomalies(energy_source=r_type, plant_id=req.plant_id, limit=15)
        records = db_manager.get_processed_records(plant_id=req.plant_id, energy_source=r_type, limit=50)
        report_data = {
            "report_title": f"{r_type.capitalize()} Energy Intelligence Audit",
            "energy_source": r_type,
            "generation_timestamp": now_str,
            "data_classification": "DERIVED_ANALYTICS",
            "plant_count": len(plants),
            "daily_summaries": daily,
            "telemetry_sample": records,
            "detected_anomalies": anomalies
        }

    elif r_type == "anomalies":
        anomalies = db_manager.get_anomalies(plant_id=req.plant_id, limit=100)
        report_data = {
            "report_title": "Operational Incident & Anomaly Alert Log",
            "generation_timestamp": now_str,
            "data_classification": "DERIVED_ANALYTICS",
            "total_incidents": len(anomalies),
            "anomalies": anomalies
        }

    elif r_type == "spark":
        jobs = db_manager.get_processing_jobs(limit=50)
        report_data = {
            "report_title": "Apache Spark Distributed Processing Performance Report",
            "generation_timestamp": now_str,
            "data_classification": "DERIVED_ANALYTICS",
            "spark_version": "PySpark 3.5.x RDD API",
            "jobs_logged": len(jobs),
            "jobs": jobs
        }

    elif r_type == "owid":
        stats = db_manager.get_global_energy_statistics(limit=100)
        report_data = {
            "report_title": "Global Renewable Electricity Mix (Our World in Data)",
            "generation_timestamp": now_str,
            "data_classification": "REAL_EXTERNAL_DATA",
            "source": "Our World in Data (OWID) Energy Database",
            "records_count": len(stats),
            "country_statistics": stats
        }

    elif r_type == "weather":
        obs = db_manager.get_weather_observations(plant_id=req.plant_id, limit=48)
        report_data = {
            "report_title": "Plant-Specific Meteorological & Resource Conditions",
            "generation_timestamp": now_str,
            "data_classification": "REAL_EXTERNAL_DATA",
            "source": "Open-Meteo API",
            "observations_count": len(obs),
            "observations": obs
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported report type {req.report_type}")

    if req.export_format.lower() == "csv":
        # Extract list to export as CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        target_list = []
        if "anomalies" in report_data and isinstance(report_data["anomalies"], list):
            target_list = report_data["anomalies"]
        elif "daily_summaries" in report_data and isinstance(report_data["daily_summaries"], list):
            target_list = report_data["daily_summaries"]
        elif "jobs" in report_data and isinstance(report_data["jobs"], list):
            target_list = report_data["jobs"]
        elif "country_statistics" in report_data and isinstance(report_data["country_statistics"], list):
            target_list = report_data["country_statistics"]
        elif "registered_plants" in report_data and isinstance(report_data["registered_plants"], list):
            target_list = report_data["registered_plants"]

        if target_list:
            headers = list(target_list[0].keys())
            writer.writerow(headers)
            for item in target_list:
                writer.writerow([str(item.get(h, "")) for h in headers])
        else:
            writer.writerow(["Key", "Value"])
            for k, v in report_data.items():
                writer.writerow([k, str(v)])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=report_{r_type}_{datetime.now().strftime('%Y%m%d%H%M')}.csv"}
        )

    return report_data
