from typing import Dict, Any, List, Tuple
from pyspark import RDD

class RddMetricsAggregator:
    """
    Computes daily summaries and plant rollups using RDD reduceByKey(), mapValues(), and sortByKey().
    Avoids expensive groupByKey() shuffles.
    """

    @staticmethod
    def aggregate_daily_summaries(processed_rdd: RDD) -> List[Dict[str, Any]]:
        """
        Aggregates processed records by (plant_id, summary_date, energy_source) using reduceByKey().
        Returns list of daily summary dictionaries.
        """
        # Map to ((plant_id, date, source), (energy, peak_p, sum_p, cnt_p, sum_eff, cnt_eff))
        def map_to_pair(record: Dict[str, Any]):
            ts = record.get("timestamp", "")
            date_str = ts.split(" ")[0] if " " in ts else ts.split("T")[0]
            key = (record.get("plant_id"), date_str, record.get("energy_source"))
            
            p = float(record.get("generated_power", 0.0))
            e = float(record.get("energy_generated", 0.0))
            eff = float(record.get("efficiency", 0.0))
            eff_cnt = 1 if eff > 0 else 0

            return (key, (e, p, p, 1, eff, eff_cnt))

        pairs_rdd = processed_rdd.map(map_to_pair)

        # Reduce by key: (total_e, max_p, sum_p, count_p, sum_eff, count_eff)
        reduced_rdd = pairs_rdd.reduceByKey(
            lambda a, b: (
                a[0] + b[0],
                max(a[1], b[1]),
                a[2] + b[2],
                a[3] + b[3],
                a[4] + b[4],
                a[5] + b[5]
            )
        )

        # Map values to summary structure
        def format_summary(item: Tuple[Tuple[str, str, str], Tuple[float, float, float, int, float, int]]):
            (plant_id, summary_date, energy_source), (total_e, max_p, sum_p, cnt_p, sum_eff, cnt_eff) = item
            avg_p = round(sum_p / cnt_p, 2) if cnt_p > 0 else 0.0
            avg_eff = round(sum_eff / cnt_eff, 2) if cnt_eff > 0 else 0.0
            
            # Operating hours: cnt_p * 15 min / 60 or bounded to 24h
            operating_hours = min(24.0, round(cnt_p * 0.25, 1))

            return {
                "plant_id": plant_id,
                "energy_source": energy_source,
                "summary_date": summary_date,
                "total_energy_generated_kwh": round(total_e, 2),
                "peak_power_kw": round(max_p, 2),
                "avg_power_kw": avg_p,
                "avg_efficiency": avg_eff,
                "capacity_factor": round((avg_p / max(1.0, max_p)) * 100.0, 2) if max_p > 0 else 0.0,
                "operating_hours": operating_hours,
                "anomaly_count": 0,
                "data_classification": "DERIVED_ANALYTICS"
            }

        sorted_rdd = reduced_rdd.sortByKey(ascending=False)
        summaries = sorted_rdd.map(format_summary).collect()
        return summaries
