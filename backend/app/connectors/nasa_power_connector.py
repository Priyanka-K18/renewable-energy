import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from backend.app.database.db_manager import db_manager

logger = logging.getLogger("nasa_power_connector")

class NasaPowerConnector:
    """
    NASA POWER Connector for Historical Environmental and Solar Resource Data.
    Official portal: https://power.larc.nasa.gov/
    API Endpoint: https://power.larc.nasa.gov/api/temporal/daily/point
    Community: RE (Renewable Energy)
    Classification: REAL_EXTERNAL_DATA
    """
    BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

    DEFAULT_PARAMETERS = [
        "ALLSKY_SFC_SW_DWN", # kW-hr/m^2/day: Surface downward irradiance
        "ALLSKY_SFC_SW_DNI", # kW-hr/m^2/day: Direct normal irradiance
        "T2M",               # C: Temperature at 2 Meters
        "T2M_MAX",           # C: Maximum Temperature at 2 Meters
        "T2M_MIN",           # C: Minimum Temperature at 2 Meters
        "WS10M",             # m/s: Wind Speed at 10 Meters
        "WS50M",             # m/s: Wind Speed at 50 Meters
        "PRECTOTCORR",       # mm/day: Precipitation Corrected
        "RH2M"               # %: Relative Humidity at 2 Meters
    ]

    def __init__(self, timeout_sec: float = 30.0):
        self.timeout = timeout_sec

    def fetch_historical_data(
        self,
        latitude: float,
        longitude: float,
        start_date: str, # YYYYMMDD
        end_date: str,   # YYYYMMDD
        plant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieves daily historical solar and meteorological data from NASA POWER.
        Handles NASA's fill values (-999.0 indicates missing observation).
        """
        params = {
            "parameters": ",".join(self.DEFAULT_PARAMETERS),
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date,
            "end": end_date,
            "format": "JSON"
        }

        try:
            with httpx.Client(timeout=self.timeout, verify=False) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                raw_data = response.json()

            properties = raw_data.get("properties", {})
            parameter_data = properties.get("parameter", {})

            # Extract date keys
            first_param = self.DEFAULT_PARAMETERS[0]
            dates = list(parameter_data.get(first_param, {}).keys())
            dates.sort()

            normalized_records: List[Dict[str, Any]] = []

            for d_str in dates:
                # Convert YYYYMMDD to ISO date YYYY-MM-DD
                try:
                    iso_date = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}"
                except Exception:
                    iso_date = d_str

                def clean_val(param_name: str) -> Optional[float]:
                    val = parameter_data.get(param_name, {}).get(d_str)
                    if val is None or val <= -900.0: # NASA uses -999 as missing
                        return None
                    return float(val)

                record = {
                    "plant_id": plant_id,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": iso_date,
                    "temporal_resolution": "daily",
                    "allsky_sfc_sw_dwn": clean_val("ALLSKY_SFC_SW_DWN"),
                    "allsky_sfc_sw_dni": clean_val("ALLSKY_SFC_SW_DNI"),
                    "t2m": clean_val("T2M"),
                    "t2m_max": clean_val("T2M_MAX"),
                    "t2m_min": clean_val("T2M_MIN"),
                    "ws10m": clean_val("WS10M"),
                    "ws50m": clean_val("WS50M"),
                    "prectotcorr": clean_val("PRECTOTCORR"),
                    "rh2m": clean_val("RH2M"),
                    "source_name": "NASA POWER",
                    "data_classification": "REAL_EXTERNAL_DATA",
                    "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                    "quality_status": "valid"
                }
                normalized_records.append(record)

            # Persist to database
            if normalized_records:
                db_manager.insert_environmental_observations_batch(normalized_records)
                db_manager.update_data_source_sync("nasa_power", "success", len(normalized_records))

            return {
                "status": "success",
                "source": "NASA POWER",
                "data_classification": "REAL_EXTERNAL_DATA",
                "record_count": len(normalized_records),
                "latitude": latitude,
                "longitude": longitude,
                "date_range": f"{start_date} to {end_date}",
                "records": normalized_records[:10] # Return preview
            }

        except Exception as e:
            logger.error(f"NASA POWER API request failed: {e}")
            db_manager.update_data_source_sync("nasa_power", f"error: {str(e)[:50]}")
            return {
                "status": "failed",
                "source": "NASA POWER",
                "error": str(e),
                "note": "Retaining previously cached NASA POWER observations"
            }

nasa_power_connector = NasaPowerConnector()
