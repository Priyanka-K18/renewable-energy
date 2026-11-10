import httpx
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from backend.app.database.db_manager import db_manager

logger = logging.getLogger("open_meteo_connector")

class OpenMeteoConnector:
    """
    Open-Meteo Weather API Connector for Current Weather and Forecast Data.
    Official portal: https://open-meteo.com/
    Endpoint: https://api.open-meteo.com/v1/forecast
    Attribution: Weather data by Open-Meteo.com (CC-BY 4.0)
    Classification: REAL_EXTERNAL_DATA
    """
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    HOURLY_VARIABLES = [
        "temperature_2m",
        "relative_humidity_2m",
        "cloud_cover",
        "shortwave_radiation",
        "direct_radiation",
        "diffuse_radiation",
        "direct_normal_irradiance",
        "wind_speed_10m",
        "wind_speed_80m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "precipitation",
        "rain",
        "precipitation_probability"
    ]

    CURRENT_VARIABLES = [
        "temperature_2m",
        "relative_humidity_2m",
        "cloud_cover",
        "precipitation",
        "rain",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "shortwave_radiation",
        "direct_normal_irradiance"
    ]

    def __init__(self, timeout_sec: float = 20.0):
        self.timeout = timeout_sec

    def fetch_weather_for_plant(
        self,
        plant_id: str,
        latitude: float,
        longitude: float,
        forecast_days: int = 2
    ) -> Dict[str, Any]:
        """
        Fetches both current and hourly forecast conditions for a given plant coordinate.
        Normalizes and persists observations into weather_observations table.
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": ",".join(self.CURRENT_VARIABLES),
            "hourly": ",".join(self.HOURLY_VARIABLES),
            "forecast_days": forecast_days,
            "timezone": "UTC"
        }

        try:
            with httpx.Client(timeout=self.timeout, verify=False) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                raw_data = response.json()

            records_to_save: List[Dict[str, Any]] = []
            now_iso = datetime.now(timezone.utc).isoformat()

            # 1. Process Current Observation
            current_data = raw_data.get("current", {})
            current_time = current_data.get("time") or now_iso
            current_record = {
                "plant_id": plant_id,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": current_time,
                "observation_type": "current",
                "temperature_2m": current_data.get("temperature_2m"),
                "relative_humidity_2m": current_data.get("relative_humidity_2m"),
                "cloud_cover": current_data.get("cloud_cover"),
                "shortwave_radiation": current_data.get("shortwave_radiation"),
                "direct_radiation": None,
                "diffuse_radiation": None,
                "direct_normal_irradiance": current_data.get("direct_normal_irradiance"),
                "wind_speed_10m": current_data.get("wind_speed_10m"),
                "wind_speed_80m": None,
                "wind_direction_10m": current_data.get("wind_direction_10m"),
                "wind_gusts_10m": current_data.get("wind_gusts_10m"),
                "precipitation": current_data.get("precipitation"),
                "rain": current_data.get("rain"),
                "precipitation_probability": None,
                "source_name": "Open-Meteo",
                "data_classification": "REAL_EXTERNAL_DATA",
                "retrieval_timestamp": now_iso,
                "quality_status": "valid"
            }
            records_to_save.append(current_record)

            # 2. Process Hourly Forecast Observations
            hourly_data = raw_data.get("hourly", {})
            times = hourly_data.get("time", [])

            for idx, t in enumerate(times[:48]): # up to 48 hours
                hourly_record = {
                    "plant_id": plant_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": t,
                    "observation_type": "forecast_hourly",
                    "temperature_2m": hourly_data.get("temperature_2m", [])[idx] if idx < len(hourly_data.get("temperature_2m", [])) else None,
                    "relative_humidity_2m": hourly_data.get("relative_humidity_2m", [])[idx] if idx < len(hourly_data.get("relative_humidity_2m", [])) else None,
                    "cloud_cover": hourly_data.get("cloud_cover", [])[idx] if idx < len(hourly_data.get("cloud_cover", [])) else None,
                    "shortwave_radiation": hourly_data.get("shortwave_radiation", [])[idx] if idx < len(hourly_data.get("shortwave_radiation", [])) else None,
                    "direct_radiation": hourly_data.get("direct_radiation", [])[idx] if idx < len(hourly_data.get("direct_radiation", [])) else None,
                    "diffuse_radiation": hourly_data.get("diffuse_radiation", [])[idx] if idx < len(hourly_data.get("diffuse_radiation", [])) else None,
                    "direct_normal_irradiance": hourly_data.get("direct_normal_irradiance", [])[idx] if idx < len(hourly_data.get("direct_normal_irradiance", [])) else None,
                    "wind_speed_10m": hourly_data.get("wind_speed_10m", [])[idx] if idx < len(hourly_data.get("wind_speed_10m", [])) else None,
                    "wind_speed_80m": hourly_data.get("wind_speed_80m", [])[idx] if idx < len(hourly_data.get("wind_speed_80m", [])) else None,
                    "wind_direction_10m": hourly_data.get("wind_direction_10m", [])[idx] if idx < len(hourly_data.get("wind_direction_10m", [])) else None,
                    "wind_gusts_10m": hourly_data.get("wind_gusts_10m", [])[idx] if idx < len(hourly_data.get("wind_gusts_10m", [])) else None,
                    "precipitation": hourly_data.get("precipitation", [])[idx] if idx < len(hourly_data.get("precipitation", [])) else None,
                    "rain": hourly_data.get("rain", [])[idx] if idx < len(hourly_data.get("rain", [])) else None,
                    "precipitation_probability": hourly_data.get("precipitation_probability", [])[idx] if idx < len(hourly_data.get("precipitation_probability", [])) else None,
                    "source_name": "Open-Meteo",
                    "data_classification": "REAL_EXTERNAL_DATA",
                    "retrieval_timestamp": now_iso,
                    "quality_status": "valid"
                }
                records_to_save.append(hourly_record)

            # Persist batch to db
            if records_to_save:
                db_manager.insert_weather_observations_batch(records_to_save)
                db_manager.update_data_source_sync("open_meteo", "success", len(records_to_save))

            return {
                "status": "success",
                "source": "Open-Meteo",
                "data_classification": "REAL_EXTERNAL_DATA",
                "current": current_record,
                "hourly_forecast_count": len(records_to_save) - 1,
                "hourly_sample": records_to_save[1:6]
            }

        except Exception as e:
            logger.error(f"Open-Meteo API query failed: {e}")
            db_manager.update_data_source_sync("open_meteo", f"error: {str(e)[:50]}")
            return {
                "status": "failed",
                "source": "Open-Meteo",
                "error": str(e),
                "note": "Serving cached weather data if available"
            }

open_meteo_connector = OpenMeteoConnector()
