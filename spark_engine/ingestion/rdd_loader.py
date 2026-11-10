import os
import csv
import io
from typing import List, Dict, Any, Tuple
from pyspark import SparkContext, RDD

class RddLoader:
    """
    Ingests raw data into PySpark RDDs from distributed files or in-memory batches.
    """
    @staticmethod
    def load_csv_lines(sc: SparkContext, file_path: str, min_partitions: int = 2) -> RDD:
        """
        Loads CSV dataset into an RDD of raw text lines using SparkContext.textFile.
        """
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        return sc.textFile(file_path, minPartitions=min_partitions)

    @staticmethod
    def parallelize_records(sc: SparkContext, records: List[Dict[str, Any]], num_slices: int = 2) -> RDD:
        """
        Parallelizes in-memory Python collections into an RDD using SparkContext.parallelize.
        """
        return sc.parallelize(records, numSlices=num_slices)
