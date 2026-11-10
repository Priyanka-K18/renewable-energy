import pytest

from backend.app.database.supabase_energy_repository import SupabaseEnergyRepository


class FakeSupabaseQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table

    def upsert(self, rows, on_conflict):
        self.client.upserts.append((self.table_name, rows, on_conflict))
        return self

    def select(self, columns):
        self.client.selected.append((self.table_name, columns))
        return self

    def eq(self, column, value):
        return self

    def order(self, column, desc=False):
        return self

    def limit(self, value):
        return self

    def execute(self):
        return type("Response", (), {"data": self.client.result_rows})()


class FakeSupabaseClient:
    def __init__(self):
        self.upserts = []
        self.selected = []
        self.result_rows = [{"id": "test-record"}]

    def table(self, table_name):
        return FakeSupabaseQuery(self, table_name)


def test_spark_results_are_normalized_and_upserted():
    repository = object.__new__(SupabaseEnergyRepository)
    repository.client = FakeSupabaseClient()

    repository.write_spark_results(
        records=[
            {
                "plant_id": "plant-1",
                "source_name": "Spark RDD Solar Pipeline",
                "equipment_code": "INV-1",
                "timestamp": "2025-01-02T03:04:05Z",
                "generated_power": 1250,
                "energy_generated": 250,
                "efficiency": 95.0,
                "additional_metrics": {"irradiance_wm2": 800},
                "data_classification": "DERIVED_ANALYTICS",
            }
        ],
        summaries=[
            {
                "plant_id": "plant-1",
                "energy_source": "solar",
                "summary_date": "2025-01-02",
                "total_energy_generated_kwh": 250,
                "peak_power_kw": 1250,
                "avg_power_kw": 1000,
                "avg_efficiency": 95,
                "data_classification": "DERIVED_ANALYTICS",
            }
        ],
        anomalies=[],
    )

    assert [entry[0] for entry in repository.client.upserts] == [
        "energy_generation",
        "analytics_results",
    ]
    generation = repository.client.upserts[0][1][0]
    assert generation["recorded_at"] == "2025-01-02T03:04:05+00:00"
    assert generation["power_mw"] == 1.25
    assert generation["energy_mwh"] == 0.25
    assert generation["data_classification"] == "DERIVED_ANALYTICS"

    analytics = repository.client.upserts[1][1][0]
    assert analytics["period_start"] == "2025-01-02T00:00:00+00:00"
    assert analytics["metrics"]["total_energy_mwh"] == 0.25


def test_weather_observations_are_upserted():
    repository = object.__new__(SupabaseEnergyRepository)
    repository.client = FakeSupabaseClient()

    repository.upsert_weather_observations(
        [
            {
                "plant_id": "plant-1",
                "timestamp": "2025-01-02T03:04:05Z",
                "temperature_2m": 22.5,
                "shortwave_radiation": 440,
                "source_name": "Open-Meteo",
                "data_classification": "REAL_EXTERNAL_DATA",
            }
        ]
    )

    table, rows, conflict = repository.client.upserts[0]
    assert table == "weather_data"
    assert conflict == "plant_id,source_name,observed_at"
    assert rows[0]["temperature_c"] == 22.5
    assert rows[0]["irradiance_w_m2"] == 440


def test_enabled_repository_requires_backend_service_role_key():
    with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
        SupabaseEnergyRepository(
            enabled=True,
            url="https://project.supabase.co",
            service_role_key="",
        )


def test_generation_records_can_be_read_back():
    repository = object.__new__(SupabaseEnergyRepository)
    repository.client = FakeSupabaseClient()

    assert repository.get_generation_records("plant-1", limit=1) == [
        {"id": "test-record"}
    ]
    assert repository.client.selected == [("energy_generation", "*")]


def test_generation_read_limit_is_bounded():
    repository = object.__new__(SupabaseEnergyRepository)
    repository.client = FakeSupabaseClient()

    with pytest.raises(ValueError, match="between 1 and 500"):
        repository.get_generation_records("plant-1", limit=501)
