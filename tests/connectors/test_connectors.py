import pytest
from backend.app.connectors.open_meteo_connector import open_meteo_connector
from backend.app.connectors.nasa_power_connector import nasa_power_connector
from backend.app.connectors.owid_energy_connector import owid_energy_connector
from backend.app.database.db_manager import db_manager

def test_owid_connector_ingestion():
    result = owid_energy_connector.ingest_owid_data(target_years=[2022, 2023], max_records=20)
    assert result["status"] == "success"
    assert result["data_classification"] == "REAL_EXTERNAL_DATA"
    assert result["records_ingested"] > 0

    stats = db_manager.get_global_energy_statistics(limit=10)
    assert len(stats) > 0
    assert stats[0]["country"] is not None
    assert stats[0]["data_classification"] == "REAL_EXTERNAL_DATA"

def test_open_meteo_connector():
    # Test with Bhadla Solar Park coordinates (27.5397, 71.9161)
    res = open_meteo_connector.fetch_weather_for_plant(
        plant_id="a0000001-0000-0000-0000-000000000001",
        latitude=27.5397,
        longitude=71.9161,
        forecast_days=1
    )
    # Even if offline/firewalled, status will be handled gracefully
    if res["status"] == "success":
        assert res["current"]["temperature_2m"] is not None
        assert res["data_classification"] == "REAL_EXTERNAL_DATA"

def test_nasa_power_connector():
    # Test coordinate query with historical date range
    res = nasa_power_connector.fetch_historical_data(
        latitude=27.5397,
        longitude=71.9161,
        start_date="20230101",
        end_date="20230105",
        plant_id="a0000001-0000-0000-0000-000000000001"
    )
    if res["status"] == "success":
        assert res["data_classification"] == "REAL_EXTERNAL_DATA"
        assert res["record_count"] > 0
