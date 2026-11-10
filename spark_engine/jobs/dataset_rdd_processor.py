from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from math import sqrt
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple

import ijson
import xlrd
from openpyxl import load_workbook

from spark_engine.core.spark_manager import spark_manager

if TYPE_CHECKING:
    from backend.app.database.dataset_repository import DatasetRepository


_MAX_COLUMNS = 500
_MISSING_STRINGS = {"", "na", "n/a", "null", "none", "nan"}
_ALIASES = {
    "timestamp": {
        "timestamp", "datetime", "date_time", "recorded_at", "observed_at",
        "date", "time",
    },
    "power": {
        "ac_power", "active_power", "power", "power_kw", "power_mw",
        "generated_power", "generation_power",
    },
    "energy": {
        "energy", "energy_generated", "energy_generation", "generation",
        "daily_yield", "daily_generation", "total_yield", "total_generation",
        "hydro_generation", "water_generation",
    },
    "temperature": {
        "temperature", "ambient_temperature", "ambient_temp", "module_temperature",
        "module_temp", "temperature_c", "temp_c",
    },
    "irradiance": {
        "irradiation", "solar_irradiation", "irradiance", "irradiance_w_m2",
        "shortwave_radiation",
    },
    "wind_speed": {"wind_speed", "wind_velocity", "wind_speed_ms", "wind_speed_10m"},
    "water_flow": {"water_flow", "water_flow_rate", "flow_rate", "flow_m3_s"},
    "plant_id": {"plant_id", "plant", "facility_id", "site_id"},
    "location": {"location", "site", "region", "country", "latitude", "longitude"},
}
_MEASUREMENT_TYPES = {"power", "energy", "temperature", "irradiance", "wind_speed", "water_flow"}


def _column_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _is_missing(value: Any) -> bool:
    return value is None or (
        isinstance(value, str) and value.strip().lower() in _MISSING_STRINGS
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _json_rows(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("rb") as stream:
        first = stream.read(1)
        stream.seek(0)
        while first and first.isspace():
            stream.read(1)
            first = stream.read(1)
        stream.seek(0)
        if first == b"[":
            yield from ijson.items(stream, "item")
            return
        if first == b"{":
            stream.seek(0)
            first_line = next((line for line in stream if line.strip()), b"")
            try:
                first_value = json.loads(first_line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                first_value = None

            if isinstance(first_value, dict) and not any(
                isinstance(first_value.get(key), list) for key in ("records", "data")
            ):
                pending = first_value
                first_error = None
            elif first_value is None:
                second_line = next((line for line in stream if line.strip()), b"")
                try:
                    second_value = json.loads(second_line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    second_value = None
                if isinstance(second_value, dict):
                    pending = second_value
                    first_error = first_line
                else:
                    pending = None
                    first_error = None
            else:
                pending = None
                first_error = None

            if pending is not None:
                if first_error is not None:
                    yield {
                        "__parse_error__": "Malformed JSON Lines record.",
                        "__raw__": first_error.decode("utf-8", errors="replace")[:2000],
                    }
                else:
                    yield pending
                for raw_line in stream:
                    if not raw_line.strip():
                        continue
                    try:
                        value = json.loads(raw_line)
                        if isinstance(value, dict):
                            yield value
                        else:
                            yield {
                                "__parse_error__": "Each JSON Lines item must be an object.",
                                "__raw__": value,
                            }
                    except (json.JSONDecodeError, UnicodeDecodeError) as error:
                        yield {"__parse_error__": f"Invalid JSON Lines record: {error}", "__raw__": raw_line.decode("utf-8", errors="replace")[:2000]}
                return

            has_wrapper = isinstance(first_value, dict) and any(
                isinstance(first_value.get(key), list) for key in ("records", "data")
            )
            for prefix in ("records.item", "data.item"):
                with path.open("rb") as wrapped:
                    try:
                        items = ijson.items(wrapped, prefix)
                        first_item = next(items, None)
                        if first_item is not None:
                            yield first_item
                            yield from items
                            return
                    except ijson.JSONError:
                        break
            if has_wrapper:
                return
            with path.open("rb") as single:
                try:
                    value = json.load(single)
                except (json.JSONDecodeError, UnicodeDecodeError) as error:
                    raise ValueError("JSON file contains malformed data.") from error
            if isinstance(value, dict):
                yield value
            else:
                raise ValueError("JSON must contain an array of objects or JSON Lines.")
            return
        raise ValueError("JSON file must start with an object or array.")


def _source_rows(path: Path, file_format: str) -> Tuple[List[str], Iterator[Dict[str, Any]]]:
    if file_format == "csv":
        stream = path.open("r", encoding="utf-8-sig", newline="")
        reader = csv.DictReader(stream)
        headers = [str(column or "").strip() for column in (reader.fieldnames or [])]
        if not headers:
            stream.close()
            raise ValueError("CSV file has no header row.")

        def csv_iter() -> Iterator[Dict[str, Any]]:
            try:
                for row in reader:
                    yield {str(key).strip(): value for key, value in row.items() if key is not None}
            finally:
                stream.close()

        return headers, csv_iter()

    if file_format == "xlsx":
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        raw_headers = next(rows, None)
        headers = [str(value).strip() if value is not None else "" for value in (raw_headers or [])]
        if not headers:
            workbook.close()
            raise ValueError("Excel workbook has no header row.")

        def xlsx_iter() -> Iterator[Dict[str, Any]]:
            try:
                for values in rows:
                    yield {
                        headers[index]: _json_value(value)
                        for index, value in enumerate(values[: len(headers)])
                    }
            finally:
                workbook.close()

        return headers, xlsx_iter()

    if file_format == "xls":
        workbook = xlrd.open_workbook(path, on_demand=True)
        sheet = workbook.sheet_by_index(0)
        headers = [
            str(value).strip() if value is not None else ""
            for value in (sheet.row_values(0) if sheet.nrows else [])
        ]
        if not headers:
            workbook.release_resources()
            raise ValueError("Excel workbook has no header row.")

        def xls_iter() -> Iterator[Dict[str, Any]]:
            try:
                for row_index in range(1, sheet.nrows):
                    values = sheet.row_values(row_index)
                    record = {}
                    for index in range(min(len(headers), len(values))):
                        value = values[index]
                        if sheet.cell_type(row_index, index) == xlrd.XL_CELL_DATE:
                            value = xlrd.xldate_as_datetime(value, workbook.datemode)
                        record[headers[index]] = _json_value(value)
                    yield record
            finally:
                workbook.release_resources()

        return headers, xls_iter()

    if file_format == "json":
        iterator = _json_rows(path)
        first_row = next(iterator, None)
        if first_row is None:
            raise ValueError("JSON file contains no records.")
        if first_row.get("__parse_error__"):
            headers = list(first_row.keys())

            def malformed_iter() -> Iterator[Dict[str, Any]]:
                yield first_row
                yield from iterator

            return headers, malformed_iter()
        if not isinstance(first_row, dict):
            raise ValueError("JSON records must be objects with named fields.")
        headers = [str(key) for key in first_row.keys()]

        def json_iter() -> Iterator[Dict[str, Any]]:
            yield {str(key): _json_value(value) for key, value in first_row.items()}
            for row in iterator:
                if isinstance(row, dict):
                    yield {str(key): _json_value(value) for key, value in row.items()}
                else:
                    yield {"__parse_error__": "JSON record is not an object.", "__raw__": row}

        return headers, json_iter()

    raise ValueError(f"Unsupported dataset format: {file_format}")


def inspect_dataset(path: Path, file_format: str) -> Dict[str, Any]:
    headers, rows = _source_rows(path, file_format)
    if len(headers) > _MAX_COLUMNS:
        raise ValueError(f"Dataset has more than {_MAX_COLUMNS} columns.")
    if any(not header for header in headers):
        raise ValueError("Dataset contains a blank column name.")
    if len({_column_key(header) for header in headers}) != len(headers):
        raise ValueError("Dataset contains duplicate column names.")

    sample = []
    for row in rows:
        sample.append(row)
        if len(sample) >= 100:
            break
    close = getattr(rows, "close", None)
    if close:
        close()
    if not sample:
        raise ValueError("Dataset contains a header but no data records.")

    detected: Dict[str, str] = {}
    types: Dict[str, str] = {}
    for header in headers:
        key = _column_key(header)
        aliases = {kind for kind, names in _ALIASES.items() if key in names}
        detected[header] = next(iter(aliases)) if aliases else "unclassified"
        values = [row.get(header) for row in sample if not _is_missing(row.get(header))]
        if not values:
            type_name = "empty"
        elif all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            type_name = "numeric"
        elif (
            detected[header] in _MEASUREMENT_TYPES
            or sum(_to_float(value) is not None for value in values) / len(values) >= 0.8
        ):
            type_name = "numeric"
        elif detected[header] == "timestamp":
            type_name = "datetime"
        else:
            type_name = "categorical"
        types[header] = type_name

    numeric_columns = [
        header for header in headers
        if types[header] == "numeric" and len(headers) < _MAX_COLUMNS
    ]
    return {
        "columns": headers,
        "column_count": len(headers),
        "sample_size": len(sample),
        "data_types": types,
        "detected_fields": detected,
        "numeric_columns": numeric_columns,
        "recognized_columns": {
            kind: [header for header in headers if detected[header] == kind]
            for kind in _ALIASES
        },
        "warnings": [
            "Field meaning and units are inferred from column names; verify them before interpreting results."
        ],
    }


def _to_float(value: Any) -> Optional[float]:
    if _is_missing(value) or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _fingerprint(record: Dict[str, Any]) -> str:
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_partition(
    rows: Iterator[Tuple[str, int]],
    schema: Dict[str, Any],
) -> Iterator[Tuple[int, Dict[str, Any], str, List[str]]]:
    numeric_columns = set(schema["numeric_columns"])
    detected = schema["detected_fields"]
    for raw, index in rows:
        issues: List[str] = []
        try:
            record = json.loads(raw)
            if not isinstance(record, dict):
                raise ValueError("Record is not a JSON object.")
        except (json.JSONDecodeError, ValueError) as error:
            yield index + 1, {"__raw__": raw[:2000]}, "invalid", [f"Invalid record encoding: {error}"]
            continue

        if "__parse_error__" in record:
            yield (
                index + 1,
                record,
                "invalid",
                [f"Invalid record encoding: {record['__parse_error__']}"],
            )
            continue

        for column, value in list(record.items()):
            if _is_missing(value):
                record[column] = None
                issues.append(f"Missing value: {column}")
                continue
            if column in numeric_columns:
                numeric_value = _to_float(value)
                if numeric_value is None:
                    issues.append(f"Unexpected non-numeric value in {column}")
                    continue
                record[column] = numeric_value
                if detected.get(column) in _MEASUREMENT_TYPES and numeric_value < 0:
                    issues.append(f"Negative {detected[column]} reading in {column}; flagged for review")

        timestamp_columns = [
            column for column, kind in detected.items() if kind == "timestamp"
        ]
        for column in timestamp_columns:
            value = record.get(column)
            if value is None:
                continue
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                record[column] = parsed.astimezone(timezone.utc).isoformat()
            except ValueError:
                issues.append(f"Invalid timestamp in {column}")

        is_invalid = any(issue.startswith("Unexpected non-numeric") for issue in issues)
        yield index + 1, record, "invalid" if is_invalid else ("warning" if issues else "valid"), issues


def _classify_duplicate(pair: Tuple[str, Any]) -> Dict[str, Any]:
    fingerprint, (row, counts) = pair
    index, record, classification, issues = row
    count, first_index = counts
    if count > 1 and index != first_index:
        classification = "duplicate"
        issues = [*issues, "Duplicate record content"]
    return {
        "row_number": index,
        "classification": classification,
        "issues": issues,
        "record": record,
        "fingerprint": fingerprint,
    }


class DatasetRddProcessor:
    def __init__(self, repository: DatasetRepository) -> None:
        self.repository = repository

    def process(
        self,
        dataset: Dict[str, Any],
        file_path: Path,
        stage_callback,
    ) -> Dict[str, Any]:
        started = datetime.now(timezone.utc)
        dataset_id = dataset["id"]
        owner_id = dataset["owner_id"]
        stage_callback("validating", "file_validation")
        schema = inspect_dataset(file_path, dataset["file_format"])
        self.repository.update(
            dataset_id, owner_id,
            {"processing_status": "processing", "progress_stage": "schema_detection", "schema_report": schema},
        )

        _, records = _source_rows(file_path, dataset["file_format"])
        spool_dir = Path(tempfile.mkdtemp(prefix=f"reip-{dataset_id}-"))
        canonical_path = spool_dir / "records.jsonl"
        classified = None
        sc = None
        job_group_id = f"dataset-{dataset_id}"
        try:
            with canonical_path.open("w", encoding="utf-8") as output:
                for record in records:
                    output.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")
            if canonical_path.stat().st_size == 0:
                raise ValueError("Dataset contains no data records.")

            stage_callback("processing", "spark_processing")
            sc = spark_manager.get_context()
            sc.setJobGroup(
                job_group_id,
                f"Process uploaded renewable-energy dataset {dataset_id}",
                interruptOnCancel=True,
            )
            partition_limit = 2 if os.name == "nt" else 4
            min_partitions = max(2, min(sc.defaultParallelism, partition_limit))
            source_rdd = sc.textFile(str(canonical_path), minPartitions=min_partitions)
            validated = source_rdd.zipWithIndex().mapPartitions(
                lambda partition: _validate_partition(partition, schema)
            )
            total = validated.count()
            if total == 0:
                raise ValueError("Spark found no data records to process.")

            fingerprinted = validated.map(
                lambda row: (_fingerprint(row[1]), row)
            )
            duplicate_stats = fingerprinted.mapValues(lambda row: (1, row[0])).reduceByKey(
                lambda left, right: (left[0] + right[0], min(left[1], right[1])),
                numPartitions=min_partitions,
            )
            classified = fingerprinted.join(
                duplicate_stats, numPartitions=min_partitions
            ).map(_classify_duplicate).cache()

            status_counts = (
                classified.map(lambda item: (item["classification"], 1))
                .reduceByKey(lambda left, right: left + right, numPartitions=min_partitions)
                .collect()
            )
            missing_counts = (
                classified.flatMap(
                    lambda item: (
                        (column, 1)
                        for column, value in item["record"].items()
                        if value is None
                    )
                )
                .reduceByKey(lambda left, right: left + right, numPartitions=min_partitions)
                .collect()
            )
            analytics = self._analytics(classified, schema, min_partitions)

            stage_callback("persisting", "database_persistence")
            batch: List[Dict[str, Any]] = []
            for item in classified.toLocalIterator():
                batch.append(item)
                if len(batch) >= 200:
                    stage_callback("persisting", "database_persistence")
                    self.repository.insert_records(dataset_id, batch)
                    batch = []
            stage_callback("persisting", "database_persistence")
            if batch:
                self.repository.insert_records(dataset_id, batch)

            counts = dict(status_counts)
            duplicates = counts.get("duplicate", 0)
            invalid = counts.get("invalid", 0)
            warnings = counts.get("warning", 0)
            valid = counts.get("valid", 0)
            quality_report = {
                "total_rows": total,
                "valid_rows": valid,
                "warning_rows": warnings,
                "invalid_rows": invalid,
                "duplicate_rows": duplicates,
                "invalid_timestamps": analytics.pop("invalid_timestamps", 0),
                "negative_readings": analytics.pop("negative_readings", 0),
                "outliers": analytics.pop("outliers", {}),
                "validation_score_pct": round(
                    (valid + warnings) * 100.0 / total, 2
                ),
                "warnings": schema["warnings"],
                "classification_rules": [
                    "invalid: detected numeric fields contain non-numeric values",
                    "warning: missing values, invalid timestamps, or negative recognized measurements",
                    "duplicate: repeated canonical record content after the first occurrence",
                    "valid: no detected issues",
                ],
            }
            duration = (datetime.now(timezone.utc) - started).total_seconds()
            summary = {
                "processing_status": "completed",
                "progress_stage": "completed",
                "total_records": total,
                "valid_records": valid,
                "warning_records": warnings,
                "invalid_records": invalid,
                "duplicate_records": duplicates,
                "missing_values": dict(missing_counts),
                "schema_report": schema,
                "quality_report": quality_report,
                "analytics": analytics,
                "processing_duration_seconds": round(duration, 3),
                "processing_error": None,
            }
            self.repository.update(dataset_id, owner_id, summary)
            return summary
        finally:
            if sc is not None:
                for property_name in (
                    "spark.jobGroup.id",
                    "spark.job.description",
                    "spark.job.interruptOnCancel",
                ):
                    sc.setLocalProperty(property_name, None)
            if classified is not None:
                classified.unpersist(blocking=True)
            shutil.rmtree(spool_dir, ignore_errors=False)

    @staticmethod
    def _analytics(
        classified, schema: Dict[str, Any], partitions: int
    ) -> Dict[str, Any]:
        recognized = schema["recognized_columns"]
        output: Dict[str, Any] = {
            "measured_or_derived": {},
            "time_series": [],
            "by_date": [],
            "available_charts": [],
        }
        numeric_columns = schema["numeric_columns"][:50]
        numeric_pairs = classified.flatMap(
            lambda item: (
                ((column, "stats"), (value, value * value, value, value, 1))
                for column in numeric_columns
                if (value := _to_float(item["record"].get(column))) is not None
            )
        )
        stat_rdd = numeric_pairs.aggregateByKey(
            (0.0, 0.0, math.inf, -math.inf, 0),
            lambda state, item: (
                state[0] + item[0],
                state[1] + item[1],
                min(state[2], item[2]),
                max(state[3], item[3]),
                state[4] + item[4],
            ),
            lambda left, right: (
                left[0] + right[0],
                left[1] + right[1],
                min(left[2], right[2]),
                max(left[3], right[3]),
                left[4] + right[4],
            ),
            numPartitions=partitions,
        ).collect()
        stats = {key[0]: value for key, value in stat_rdd}
        for column, (total, sum_squares, minimum, maximum, count) in stats.items():
            output["measured_or_derived"][column] = {
                "observations": count,
                "average": total / count,
                "minimum": minimum,
                "maximum": maximum,
                "unit": "source unit; not inferred",
            }

        energy_columns = recognized["energy"] + recognized["power"]
        date_columns = recognized["timestamp"]
        if energy_columns:
            metric = energy_columns[0]
            output["available_charts"].append(
                {
                    "type": "time_series",
                    "title": f"{metric} over time",
                    "x_axis": date_columns[0] if date_columns else None,
                    "y_axis": metric,
                    "unit": "source unit; not inferred",
                }
            )
            if date_columns:
                date_column = date_columns[0]
                by_date = (
                    classified.flatMap(
                        lambda item: DatasetRddProcessor._date_energy_pair(
                            item, date_column, metric
                        )
                    )
                    .reduceByKey(lambda left, right: left + right, numPartitions=partitions)
                    .sortByKey(numPartitions=partitions)
                    .take(500)
                )
                output["by_date"] = [
                    {"date": key, "value": value, "column": metric}
                    for key, value in by_date
                ]

        for kind in ("temperature", "irradiance", "wind_speed", "water_flow"):
            if recognized[kind]:
                output["available_charts"].append(
                    {
                        "type": "distribution",
                        "title": f"{recognized[kind][0]} distribution",
                        "column": recognized[kind][0],
                        "unit": "source unit; not inferred",
                    }
                )

        quality_counts = dict(
            classified.flatMap(
                lambda item: (
                    [("invalid_timestamps", 1)]
                    if any(issue.startswith("Invalid timestamp") for issue in item["issues"])
                    else []
                ) + (
                    [("negative_readings", 1)]
                    if any(issue.startswith("Negative ") for issue in item["issues"])
                    else []
                )
            )
            .reduceByKey(lambda left, right: left + right, numPartitions=partitions)
            .collect()
        )
        outlier_limits: Dict[str, Tuple[float, float]] = {}
        for column, (total, sum_squares, minimum, maximum, count) in stats.items():
            if count < 3:
                continue
            mean = total / count
            deviation = sqrt(max(0.0, sum_squares / count - mean * mean))
            if deviation:
                outlier_limits[column] = (mean, 3.0 * deviation)
        outliers = dict(
            classified.flatMap(
                lambda item: (
                    (column, 1)
                    for column, (mean, threshold) in outlier_limits.items()
                    if (value := _to_float(item["record"].get(column))) is not None
                    and abs(value - mean) > threshold
                )
            )
            .reduceByKey(lambda left, right: left + right, numPartitions=partitions)
            .collect()
        )

        invalid_timestamps = quality_counts.get("invalid_timestamps", 0)
        negative_readings = quality_counts.get("negative_readings", 0)
        output["invalid_timestamps"] = invalid_timestamps
        output["negative_readings"] = negative_readings
        output["outliers"] = outliers
        return output

    @staticmethod
    def _date_energy_pair(item: Dict[str, Any], date_column: str, metric: str):
        timestamp = item["record"].get(date_column)
        value = _to_float(item["record"].get(metric))
        if timestamp is None or value is None:
            return []
        try:
            date_key = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            ).date().isoformat()
        except ValueError:
            return []
        return [(date_key, value)]
