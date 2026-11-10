import os
import sys
import logging
from typing import Optional
from pyspark import SparkContext, SparkConf
from backend.app.core.config import settings

logger = logging.getLogger("spark_manager")

class SparkContextManager:
    """
    Centralized SparkContext Manager.
    Configures and initializes a singleton SparkContext for distributed RDD computation.
    """
    _instance: Optional["SparkContextManager"] = None
    _sc: Optional[SparkContext] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SparkContextManager, cls).__new__(cls)
        return cls._instance

    def get_context(self) -> SparkContext:
        if self._sc is None or self._sc._jsc is None:
            self._initialize_context()
        return self._sc

    def _initialize_context(self):
        # Configure JVM and Python workers
        if os.path.exists(settings.JAVA_HOME):
            os.environ["JAVA_HOME"] = settings.JAVA_HOME

        py_executable = sys.executable
        os.environ["PYSPARK_PYTHON"] = py_executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = py_executable

        conf = SparkConf()
        conf.setAppName(settings.SPARK_APP_NAME)
        conf.setMaster(settings.SPARK_MASTER)
        conf.set("spark.driver.memory", settings.SPARK_DRIVER_MEMORY)
        conf.set("spark.executor.memory", settings.SPARK_EXECUTOR_MEMORY)
        conf.set("spark.sql.execution.arrow.pyspark.enabled", "false")
        conf.set("spark.ui.enabled", "false") # Run lightweight in-process
        conf.set("spark.driver.host", "127.0.0.1")
        conf.set("spark.driver.bindAddress", "127.0.0.1")

        try:
            self._sc = SparkContext.getOrCreate(conf=conf)
            self._sc.setLogLevel("WARN")
            logger.info(f"PySpark SparkContext initialized successfully. Master: {settings.SPARK_MASTER}")
        except Exception as e:
            logger.error(f"Failed to initialize SparkContext: {e}")
            raise e

    def stop(self):
        if self._sc is not None:
            self._sc.stop()
            self._sc = None
            logger.info("SparkContext stopped.")

    def cancel_job_group(self, job_group_id: str) -> None:
        if self._sc is not None and self._sc._jsc is not None:
            self._sc.cancelJobGroup(job_group_id)


spark_manager = SparkContextManager()
