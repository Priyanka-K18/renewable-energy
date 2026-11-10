from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from supabase import create_client
except ImportError:
    create_client = None

from backend.app.core.config import settings


_DATA_CLASSIFICATIONS = {
    "REAL_EXTERNAL_DATA",
    "REAL_PLANT_DATA",
    "DERIVED_ANALYTICS",
    "SIMULATED_DATA",
}
_BATCH_SIZE = 200


class SupabaseEnergyRepository:
    """Opt-in writer for the normalized Supabase energy schema."""

    def __init__(
        self,
        enabled: bool = settings.SUPABASE_NORMALIZED_SCHEMA_ENABLED,
        url: str = settings.SUPABASE_URL,
        service_role_key: str = settings.SUPABASE_SERVICE_ROLE_KEY,
    ) -> None:
        self.client: Optional[Any] = None
        if not enabled:
            return
        if not url:
            raise RuntimeError(
                "SUPABASE_NORMALIZED_SCHEMA_ENABLED requires SUPABASE_URL."
            )
        if not service_role_key:
            raise RuntimeError(
                "SUPABASE_NORMALIZED_SCHEMA_ENABLED requires "
                "SUPABASE_SERVICE_ROLE_KEY in the backend environment."
            )
        if create_client is None:
            raise RuntimeError(
                "Install the backend Supabase dependency before enabling "
                "normalized Supabase writes."
            )

        self.client = create_client(url, service_role_key)
        for table in (
            "user_profiles",
            "energy_plants",
            "energy_generation",
            "weather_data",
            "anomaly_records",
            "analytics_results",
            "uploaded_datasets",
            "uploaded_dataset_records",
        ):
            self.client.table(table).select("id").limit(0).execute()

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def write_spark_results(
        self,
        records: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        anomalies: List[Dict[str, Any]],
    ) -> None:
        client = self._require_client()
        generation_rows = [self._generation_row(record) for record in records]
        analytics_rows = [self._analytics_row(summary) for summary in summaries]
        anomaly_rows = [self._anomaly_row(anomaly) for anomaly in anomalies]

        self._upsert(
            client,
            "energy_generation",
            generation_rows,
            "plant_id,source_name,source_record_id",
        )
        self._upsert(
            client,
            "analytics_results",
            analytics_rows,
            "plant_id,result_key",
        )
        self._upsert(
            client,
            "anomaly_records",
            anomaly_rows,
            "plant_id,source_record_id",
        )

    def create_uploaded_dataset(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        response = self._require_client().table("uploaded_datasets").insert(dataset).execute()
        if not response.data:
            raise RuntimeError("Supabase did not return the created dataset.")
        return response.data[0]

    def get_uploaded_dataset(
        self, dataset_id: str, owner_id: str
    ) -> Optional[Dict[str, Any]]:
        response = (
            self._require_client()
            .table("uploaded_datasets")
            .select("*")
            .eq("id", dataset_id)
            .eq("owner_id", owner_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def find_uploaded_dataset_by_checksum(
        self, owner_id: str, checksum: str
    ) -> Optional[Dict[str, Any]]:
        response = (
            self._require_client()
            .table("uploaded_datasets")
            .select("*")
            .eq("owner_id", owner_id)
            .eq("sha256", checksum)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def list_uploaded_datasets(
        self, owner_id: str, limit: int, offset: int
    ) -> List[Dict[str, Any]]:
        response = (
            self._require_client()
            .table("uploaded_datasets")
            .select("*")
            .eq("owner_id", owner_id)
            .order("uploaded_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data

    def update_uploaded_dataset(
        self, dataset_id: str, owner_id: str, values: Dict[str, Any]
    ) -> bool:
        response = (
            self._require_client()
            .table("uploaded_datasets")
            .update(values)
            .eq("id", dataset_id)
            .eq("owner_id", owner_id)
            .execute()
        )
        return bool(response.data)

    def insert_uploaded_dataset_records(
        self, dataset_id: str, rows: List[Dict[str, Any]]
    ) -> None:
        records = [
            {
                "dataset_id": dataset_id,
                "row_number": row["row_number"],
                "classification": row["classification"],
                "issues": row["issues"],
                "record": row["record"],
            }
            for row in rows
        ]
        self._upsert(
            self._require_client(),
            "uploaded_dataset_records",
            records,
            "dataset_id,row_number",
        )

    def preview_uploaded_dataset_records(
        self,
        dataset_id: str,
        owner_id: str,
        limit: int,
        offset: int,
        classification: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        if self.get_uploaded_dataset(dataset_id, owner_id) is None:
            return [], 0
        query = (
            self._require_client()
            .table("uploaded_dataset_records")
            .select("row_number,classification,issues,record", count="exact")
            .eq("dataset_id", dataset_id)
            .order("row_number")
            .range(offset, offset + limit - 1)
        )
        if classification:
            query = query.eq("classification", classification)
        response = query.execute()
        return response.data, response.count or 0

    def delete_uploaded_dataset(
        self, dataset_id: str, owner_id: str
    ) -> Optional[Dict[str, Any]]:
        dataset = self.get_uploaded_dataset(dataset_id, owner_id)
        if dataset is None:
            return None
        self._require_client().table("uploaded_datasets").delete().eq(
            "id", dataset_id
        ).eq("owner_id", owner_id).execute()
        return dataset

    def get_generation_records(
        self, plant_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        if not plant_id:
            raise ValueError("plant_id is required to retrieve energy generation.")
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500.")
        response = (
            self._require_client()
            .table("energy_generation")
            .select("*")
            .eq("plant_id", plant_id)
            .order("recorded_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data

    def upsert_weather_observations(
        self, observations: List[Dict[str, Any]]
    ) -> None:
        rows = []
        for observation in observations:
            if not observation.get("plant_id"):
                raise ValueError(
                    "Normalized weather_data requires a plant_id for every observation."
                )
            rows.append(
                {
                    "plant_id": observation["plant_id"],
                    "source_name": observation.get("source_name", "Open-Meteo"),
                    "observed_at": self._timestamp(observation.get("timestamp")),
                    "temperature_c": observation.get("temperature_2m"),
                    "relative_humidity_pct": observation.get("relative_humidity_2m"),
                    "cloud_cover_pct": observation.get("cloud_cover"),
                    "irradiance_w_m2": observation.get("shortwave_radiation"),
                    "wind_speed_m_s": observation.get("wind_speed_10m"),
                    "precipitation_mm": observation.get("precipitation"),
                    "data_classification": self._classification(observation),
                    "measurements": {
                        key: value
                        for key, value in observation.items()
                        if key
                        not in {
                            "id",
                            "plant_id",
                            "source_name",
                            "timestamp",
                            "temperature_2m",
                            "relative_humidity_2m",
                            "cloud_cover",
                            "shortwave_radiation",
                            "wind_speed_10m",
                            "precipitation",
                            "data_classification",
                        }
                        and value is not None
                    },
                }
            )
        self._upsert(
            self._require_client(),
            "weather_data",
            rows,
            "plant_id,source_name,observed_at",
        )

    def upsert_environmental_observations(
        self, observations: List[Dict[str, Any]]
    ) -> None:
        rows = []
        for observation in observations:
            if not observation.get("plant_id"):
                raise ValueError(
                    "Normalized weather_data requires a plant_id for every observation."
                )
            rows.append(
                {
                    "plant_id": observation["plant_id"],
                    "source_name": observation.get("source_name", "NASA POWER"),
                    "observed_at": self._timestamp(observation.get("timestamp")),
                    "temperature_c": observation.get("t2m"),
                    "relative_humidity_pct": observation.get("rh2m"),
                    "irradiance_w_m2": (
                        float(observation["allsky_sfc_sw_dwn"]) * 1000.0 / 24.0
                        if observation.get("allsky_sfc_sw_dwn") is not None
                        else None
                    ),
                    "wind_speed_m_s": observation.get("ws10m"),
                    "precipitation_mm": observation.get("prectotcorr"),
                    "data_classification": self._classification(observation),
                    "measurements": {
                        key: value
                        for key, value in observation.items()
                        if key
                        not in {
                            "id",
                            "plant_id",
                            "source_name",
                            "timestamp",
                            "t2m",
                            "rh2m",
                            "allsky_sfc_sw_dwn",
                            "ws10m",
                            "prectotcorr",
                            "data_classification",
                        }
                        and value is not None
                    },
                }
            )
        self._upsert(
            self._require_client(),
            "weather_data",
            rows,
            "plant_id,source_name,observed_at",
        )

    @staticmethod
    def _generation_row(record: Dict[str, Any]) -> Dict[str, Any]:
        plant_id = record.get("plant_id")
        source_name = record.get("source_name", "Spark RDD Pipeline")
        recorded_at = SupabaseEnergyRepository._timestamp(record.get("timestamp"))
        equipment_code = record.get("equipment_code") or "unknown-equipment"
        if not plant_id:
            raise ValueError("Normalized energy_generation requires a plant_id.")
        return {
            "plant_id": plant_id,
            "source_name": source_name,
            "source_record_id": f"{equipment_code}:{recorded_at}",
            "recorded_at": recorded_at,
            "power_mw": float(record.get("generated_power", 0.0)) / 1000.0,
            "energy_mwh": float(record.get("energy_generated", 0.0)) / 1000.0,
            "efficiency_pct": record.get("efficiency"),
            "data_classification": SupabaseEnergyRepository._classification(record),
            "metrics": record.get("additional_metrics") or {},
        }

    @staticmethod
    def _analytics_row(summary: Dict[str, Any]) -> Dict[str, Any]:
        plant_id = summary.get("plant_id")
        period_start = SupabaseEnergyRepository._date_start(
            summary.get("summary_date")
        )
        if not plant_id:
            raise ValueError("Normalized analytics_results requires a plant_id.")
        return {
            "plant_id": plant_id,
            "result_key": f"daily-generation:{period_start.date().isoformat()}",
            "analysis_type": "daily_generation_summary",
            "period_start": period_start.isoformat(),
            "period_end": (period_start + timedelta(days=1)).isoformat(),
            "metrics": {
                "energy_source": summary.get("energy_source"),
                "total_energy_mwh": float(
                    summary.get("total_energy_generated_kwh", 0.0)
                )
                / 1000.0,
                "peak_power_mw": float(summary.get("peak_power_kw", 0.0)) / 1000.0,
                "average_power_mw": float(summary.get("avg_power_kw", 0.0)) / 1000.0,
                "average_efficiency_pct": summary.get("avg_efficiency", 0.0),
                "capacity_factor_pct": summary.get("capacity_factor", 0.0),
                "operating_hours": summary.get("operating_hours", 0.0),
                "anomaly_count": summary.get("anomaly_count", 0),
            },
            "algorithm_name": "Spark RDD Metrics Aggregator",
            "algorithm_version": "1",
            "data_classification": SupabaseEnergyRepository._classification(summary),
        }

    @staticmethod
    def _anomaly_row(anomaly: Dict[str, Any]) -> Dict[str, Any]:
        plant_id = anomaly.get("plant_id")
        detected_at = SupabaseEnergyRepository._timestamp(
            anomaly.get("detected_at") or datetime.now(timezone.utc)
        )
        equipment_code = anomaly.get("equipment_code") or "unknown-equipment"
        anomaly_type = anomaly.get("anomaly_type", "unknown")
        if not plant_id:
            raise ValueError("Normalized anomaly_records requires a plant_id.")
        return {
            "plant_id": plant_id,
            "source_record_id": (
                f"{equipment_code}:{detected_at}:{anomaly_type}"
            ),
            "anomaly_type": anomaly_type,
            "severity": str(anomaly.get("severity", "low")).lower(),
            "description": anomaly.get("description", anomaly_type),
            "status": str(anomaly.get("status", "open")).lower(),
            "detected_at": detected_at,
            "measured_value": anomaly.get("measured_value"),
            "expected_value": anomaly.get("expected_value"),
            "deviation_pct": anomaly.get("deviation_percentage"),
            "unit": anomaly.get("unit"),
            "recommended_action": anomaly.get("recommended_action"),
            "detection_method": anomaly.get("detection_method", "Spark RDD"),
            "data_classification": SupabaseEnergyRepository._classification(anomaly),
            "metrics": {
                "energy_source": anomaly.get("energy_source"),
                "data_source": anomaly.get("data_source"),
                "equipment_code": equipment_code,
            },
        }

    @staticmethod
    def _classification(record: Dict[str, Any]) -> str:
        classification = record.get("data_classification", "DERIVED_ANALYTICS")
        if classification not in _DATA_CLASSIFICATIONS:
            raise ValueError(f"Unsupported data classification: {classification}")
        return classification

    @staticmethod
    def _timestamp(value: Any) -> str:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str) and value.strip():
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        else:
            raise ValueError("A valid timestamp is required for normalized Supabase data.")
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _date_start(value: Any) -> datetime:
        if isinstance(value, datetime):
            return datetime.combine(value.date(), time.min, tzinfo=timezone.utc)
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=timezone.utc)
        if isinstance(value, str):
            parsed = date.fromisoformat(value[:10])
            return datetime.combine(parsed, time.min, tzinfo=timezone.utc)
        raise ValueError("A valid summary_date is required for analytics_results.")

    @staticmethod
    def _upsert(
        client: Any,
        table: str,
        rows: List[Dict[str, Any]],
        conflict_columns: str,
    ) -> None:
        for offset in range(0, len(rows), _BATCH_SIZE):
            batch = rows[offset : offset + _BATCH_SIZE]
            if batch:
                (
                    client.table(table)
                    .upsert(batch, on_conflict=conflict_columns)
                    .execute()
                )

    def _require_client(self) -> Any:
        if self.client is None:
            raise RuntimeError(
                "Normalized Supabase writes are disabled. Set "
                "SUPABASE_NORMALIZED_SCHEMA_ENABLED=true after applying the "
                "energy platform migration and configure backend credentials."
            )
        return self.client
