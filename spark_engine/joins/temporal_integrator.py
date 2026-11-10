from typing import Dict, Any, List, Tuple
from pyspark import RDD

class RddTemporalIntegrator:
    """
    Integrates heterogeneous operational telemetry with external environmental & weather datasets
    using PySpark RDD join(), leftOuterJoin(), and union() transformations.
    """

    @staticmethod
    def enrich_operational_with_weather(
        processed_op_rdd: RDD,
        weather_records_rdd: RDD
    ) -> RDD:
        """
        Enriches hourly operational records with Open-Meteo weather observations using leftOuterJoin().
        Key format: (plant_id, hourly_timestamp_str)
        """
        def op_key(r: Dict[str, Any]):
            ts = r.get("timestamp", "")
            # Truncate to hour: YYYY-MM-DD HH:00
            hour_str = ts[:13] + ":00" if len(ts) >= 13 else ts
            return ((r.get("plant_id"), hour_str), r)

        def weather_key(w: Dict[str, Any]):
            ts = w.get("timestamp", "")
            hour_str = ts[:13] + ":00" if len(ts) >= 13 else ts
            return ((w.get("plant_id"), hour_str), w)

        keyed_op = processed_op_rdd.map(op_key)
        keyed_weather = weather_records_rdd.map(weather_key)

        # Apply RDD leftOuterJoin()
        joined_rdd = keyed_op.leftOuterJoin(keyed_weather)

        # Merge weather metrics into record additional_metrics
        def merge_joined(item):
            ((plant_id, hour_str), (op_record, weather_opt)) = item
            record_copy = dict(op_record)
            add_metrics = dict(record_copy.get("additional_metrics", {}))
            
            if weather_opt is not None:
                add_metrics["ext_weather_temp_c"] = weather_opt.get("temperature_2m")
                add_metrics["ext_weather_wind_speed_ms"] = weather_opt.get("wind_speed_10m")
                add_metrics["ext_weather_shortwave_rad_wm2"] = weather_opt.get("shortwave_radiation")
                add_metrics["ext_weather_precipitation_mm"] = weather_opt.get("precipitation")
                add_metrics["ext_weather_source"] = weather_opt.get("source_name", "Open-Meteo")

            record_copy["additional_metrics"] = add_metrics
            return record_copy

        return joined_rdd.map(merge_joined)

    @staticmethod
    def union_operational_streams(rdd_stream_a: RDD, rdd_stream_b: RDD) -> RDD:
        """
        Merges multiple operational streams across different partitions using union().
        """
        return rdd_stream_a.union(rdd_stream_b)
