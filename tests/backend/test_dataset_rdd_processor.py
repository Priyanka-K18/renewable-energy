import json

from openpyxl import Workbook

from spark_engine.jobs.dataset_rdd_processor import (
    DatasetRddProcessor,
    _source_rows,
    inspect_dataset,
)


class InMemoryDatasetRepository:
    def __init__(self):
        self.updates = []
        self.records = []

    def update(self, dataset_id, owner_id, values):
        self.updates.append(values)
        return True

    def insert_records(self, dataset_id, rows):
        self.records.extend(rows)


def test_inspect_csv_xlsx_and_wrapped_json(tmp_path):
    csv_path = tmp_path / "energy.csv"
    csv_path.write_text("timestamp,power_kw\n2025-01-01T00:00:00Z,10\n", encoding="utf-8")
    assert inspect_dataset(csv_path, "csv")["numeric_columns"] == ["power_kw"]

    xlsx_path = tmp_path / "energy.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["timestamp", "power_kw"])
    sheet.append(["2025-01-01T00:00:00Z", 10])
    workbook.save(xlsx_path)
    assert inspect_dataset(xlsx_path, "xlsx")["numeric_columns"] == ["power_kw"]

    json_path = tmp_path / "energy.json"
    json_path.write_text(
        json.dumps({"metadata": {"source": "test"}, "records": [{"power_kw": 10}]}),
        encoding="utf-8",
    )
    headers, rows = _source_rows(json_path, "json")
    assert headers == ["power_kw"]
    assert list(rows) == [{"power_kw": 10}]


def test_jsonl_malformed_row_is_retained_and_processing_continues(tmp_path):
    path = tmp_path / "energy.json"
    path.write_text(
        '{"power_kw":10}\nnot-json\n{"power_kw":12}\n',
        encoding="utf-8",
    )
    _, rows = _source_rows(path, "json")
    decoded = list(rows)
    assert decoded[0] == {"power_kw": 10}
    assert decoded[1]["__parse_error__"].startswith("Invalid JSON Lines record:")
    assert decoded[2] == {"power_kw": 12}


def test_spark_rdd_processing_classifies_quality_and_persists_records(tmp_path):
    path = tmp_path / "telemetry.csv"
    path.write_text(
        "timestamp,power_kw,energy_generated\n"
        "2025-01-01T00:00:00Z,10,20\n"
        "2025-01-01T01:00:00Z,12,24\n"
        "2025-01-01T01:00:00Z,12,24\n"
        "not-a-timestamp,-3,unknown\n",
        encoding="utf-8",
    )
    repository = InMemoryDatasetRepository()
    dataset = {"id": "test-dataset", "owner_id": "test-owner", "file_format": "csv"}
    stages = []

    summary = DatasetRddProcessor(repository).process(
        dataset, path, lambda status, stage: stages.append((status, stage))
    )

    assert summary["processing_status"] == "completed"
    assert summary["total_records"] == 4
    assert summary["valid_records"] == 2
    assert summary["duplicate_records"] == 1
    assert summary["invalid_records"] == 1
    assert summary["quality_report"]["invalid_timestamps"] == 1
    assert summary["quality_report"]["negative_readings"] == 1
    assert summary["missing_values"] == {}
    assert len(repository.records) == 4
    assert len(repository.updates) == 2
    assert stages[-1] == ("persisting", "database_persistence")
