import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from spark_engine.core.spark_manager import spark_manager
from spark_engine.ingestion.rdd_loader import RddLoader
from spark_engine.transformations.cleaning import RddDataCleaner
from spark_engine.transformations.feature_engineering import RddFeatureEngineering
from spark_engine.aggregation.metrics_aggregator import RddMetricsAggregator
from spark_engine.anomaly_detection.rdd_anomaly_detector import RddAnomalyDetector
from backend.app.database.db_manager import db_manager

logger = logging.getLogger("spark_pipeline_runner")

class SparkPipelineRunner:
    """
    Executes distributed Apache Spark RDD data processing pipelines
    for raw CSV files and operational telemetry.
    """

    EXPECTED_COLUMNS = {
        "solar": 10,
        "wind": 14,
        "hydropower": 13,
        "geothermal": 14,
        "biomass": 14
    }

    def execute_file_pipeline(
        self,
        file_path: str,
        energy_source: str,
        plant_id: str,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the end-to-end distributed Spark RDD processing workflow:
        1. Ingestion via sc.textFile()
        2. Header & line cleaning via filter() & distinct()
        3. Feature engineering via map()
        4. Aggregation via reduceByKey() & sortByKey()
        5. Anomaly detection via flatMap()
        6. Batch persistence to Supabase/SQLite
        """
        start_time = time.time()
        job_id = str(uuid.uuid4())
        source_lower = energy_source.lower()

        # Register processing job
        db_manager.create_processing_job({
            "id": job_id,
            "dataset_id": dataset_id,
            "energy_source": source_lower,
            "source_name": "Spark RDD Core Pipeline",
            "job_type": "SPARK_RDD_INGESTION",
            "job_status": "running"
        })

        try:
            sc = spark_manager.get_context()
            app_id = sc.applicationId
            transformation_counter = 0

            # STEP 1: Ingestion to RDD
            lines_rdd = RddLoader.load_csv_lines(sc, file_path, min_partitions=2)
            total_lines = lines_rdd.count()
            partition_count = lines_rdd.getNumPartitions()

            # STEP 2 & 3: Clean and parse lines
            header, data_lines = RddDataCleaner.extract_header_and_data(lines_rdd)
            transformation_counter += 1 # filter()

            expected_cols = self.EXPECTED_COLUMNS.get(source_lower, len(header))
            records_rdd, valid_count, rejected_count = RddDataCleaner.clean_and_parse_csv(
                data_lines, header, expected_cols
            )
            transformation_counter += 4 # distinct(), map(), filter(), map()

            # STEP 4: Source-specific feature engineering via map()
            if source_lower == "solar":
                processed_rdd = RddFeatureEngineering.process_solar_rdd(records_rdd, plant_id)
            elif source_lower == "wind":
                processed_rdd = RddFeatureEngineering.process_wind_rdd(records_rdd, plant_id)
            elif source_lower == "hydropower":
                processed_rdd = RddFeatureEngineering.process_hydro_rdd(records_rdd, plant_id)
            elif source_lower == "geothermal":
                processed_rdd = RddFeatureEngineering.process_geothermal_rdd(records_rdd, plant_id)
            elif source_lower == "biomass":
                processed_rdd = RddFeatureEngineering.process_biomass_rdd(records_rdd, plant_id)
            else:
                raise ValueError(f"Unsupported energy source: {energy_source}")
            transformation_counter += 2 # map(), filter()

            # Cache transformed RDD for multiple actions (aggregations & anomaly detection)
            processed_rdd.cache()

            # STEP 5: Aggregation via reduceByKey()
            daily_summaries = RddMetricsAggregator.aggregate_daily_summaries(processed_rdd)
            transformation_counter += 3 # map(), reduceByKey(), sortByKey()

            # STEP 6: Anomaly Detection via flatMap()
            anomalies = RddAnomalyDetector.detect_anomalies_rdd(processed_rdd)
            transformation_counter += 3 # flatMap(), reduceByKey(), map()

            # STEP 7: Collect bounded sample of processed records for database write
            # (In production, writes can be done using foreachPartition; here we collect bounded batch)
            processed_records_sample = processed_rdd.take(300)
            
            # Populate dataset_id
            for r in processed_records_sample:
                r["dataset_id"] = dataset_id

            # STEP 8: Persist to database in batch
            db_manager.insert_processed_records_batch(processed_records_sample)
            db_manager.insert_daily_summaries_batch(daily_summaries)
            if anomalies:
                db_manager.insert_anomaly_alerts_batch(anomalies)
            if db_manager.normalized_supabase_repository.enabled:
                db_manager.normalized_supabase_repository.write_spark_results(
                    processed_records_sample,
                    daily_summaries,
                    anomalies,
                )

            # Unpersist cache
            processed_rdd.unpersist()

            execution_time = round(time.time() - start_time, 2)
            throughput = round(valid_count / max(0.01, execution_time), 2)

            # Update job status
            db_manager.update_processing_job(job_id, {
                "job_status": "completed",
                "records_ingested": total_lines - 1, # minus header
                "records_processed": valid_count,
                "records_rejected": rejected_count,
                "execution_time_seconds": execution_time,
                "throughput_records_per_sec": throughput,
                "rdd_transformation_count": transformation_counter,
                "rdd_partition_count": partition_count,
                "spark_application_id": app_id,
                "metadata": {
                    "daily_summaries_generated": len(daily_summaries),
                    "anomalies_detected": len(anomalies),
                    "header_columns": header
                }
            })

            # Update dataset record count if dataset_id provided
            if dataset_id:
                db_manager.create_dataset({
                    "id": dataset_id,
                    "record_count": valid_count,
                    "upload_status": "processed"
                })

            return {
                "job_id": job_id,
                "status": "completed",
                "energy_source": source_lower,
                "spark_application_id": app_id,
                "records_ingested": total_lines - 1,
                "records_processed": valid_count,
                "records_rejected": rejected_count,
                "execution_time_seconds": execution_time,
                "throughput_records_per_sec": throughput,
                "rdd_transformation_count": transformation_counter,
                "daily_summaries_count": len(daily_summaries),
                "anomalies_detected_count": len(anomalies),
                "anomalies": anomalies
            }

        except Exception as e:
            logger.error(f"Spark RDD pipeline execution failed: {e}")
            execution_time = round(time.time() - start_time, 2)
            db_manager.update_processing_job(job_id, {
                "job_status": "failed",
                "execution_time_seconds": execution_time,
                "error_message": str(e)
            })
            raise e

spark_pipeline_runner = SparkPipelineRunner()
