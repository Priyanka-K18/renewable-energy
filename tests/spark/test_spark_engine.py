import pytest
from pathlib import Path
from spark_engine.jobs.pipeline_runner import spark_pipeline_runner
from backend.app.database.db_manager import db_manager

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def test_spark_solar_pipeline():
    solar_csv = str(BASE_DIR / "datasets" / "solar" / "bhadla_solar_telemetry.csv")
    res = spark_pipeline_runner.execute_file_pipeline(
        file_path=solar_csv,
        energy_source="solar",
        plant_id="a0000001-0000-0000-0000-000000000001"
    )

    assert res["status"] == "completed"
    assert res["records_processed"] > 0
    assert res["rdd_transformation_count"] >= 10
    assert res["execution_time_seconds"] > 0
    assert res["daily_summaries_count"] > 0
    # Solar dataset has an injected inverter trip anomaly
    assert res["anomalies_detected_count"] >= 1

    # Verify db persistence
    records = db_manager.get_processed_records(plant_id="a0000001-0000-0000-0000-000000000001", energy_source="solar", limit=10)
    assert len(records) > 0
    assert records[0]["energy_source"] == "solar"

def test_spark_wind_pipeline():
    wind_csv = str(BASE_DIR / "datasets" / "wind" / "muppandal_wind_telemetry.csv")
    res = spark_pipeline_runner.execute_file_pipeline(
        file_path=wind_csv,
        energy_source="wind",
        plant_id="a0000002-0000-0000-0000-000000000002"
    )

    assert res["status"] == "completed"
    assert res["records_processed"] > 0
    assert res["anomalies_detected_count"] >= 1

    # Check gearbox anomaly was saved
    anomalies = db_manager.get_anomalies(energy_source="wind", plant_id="a0000002-0000-0000-0000-000000000002")
    assert len(anomalies) > 0
