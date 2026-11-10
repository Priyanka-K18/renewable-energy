import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Supabase credentials
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_NORMALIZED_SCHEMA_ENABLED: bool = False
    DATASET_MAX_UPLOAD_MB: int = 100
    DATASET_UPLOAD_DIR: str = "datasets/uploads"
    SUPABASE_DATASET_STORAGE_BUCKET: str = ""
    DATABASE_URL: str = ""

    # Spark Config
    SPARK_APP_NAME: str = "RenewableEnergyIntelligencePlatform"
    SPARK_MASTER: str = "local[*]"
    SPARK_DRIVER_MEMORY: str = "2g"
    SPARK_EXECUTOR_MEMORY: str = "2g"
    JAVA_HOME: str = r"C:\Program Files\Java\jdk-17"

    # API Endpoints
    NASA_POWER_API_BASE: str = "https://power.larc.nasa.gov/api/temporal"
    OWID_ENERGY_CSV_URL: str = "https://catalog.ourworldindata.org/energy/owid_energy/owid_energy.csv"
    OPEN_METEO_API_BASE: str = "https://api.open-meteo.com/v1"

    # Scheduler intervals
    WEATHER_SYNC_INTERVAL_HOURS: int = 1
    OWID_SYNC_INTERVAL_DAYS: int = 30
    NASA_POWER_SYNC_INTERVAL_DAYS: int = 7

    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    JWT_SECRET: str = "renewable-energy-intelligence-secret-key-32-chars-min"

    class Config:
        env_file = str(BASE_DIR / ".env")
        extra = "ignore"

settings = Settings()

# Ensure Java and PySpark Python environments are set correctly
if os.path.exists(settings.JAVA_HOME):
    os.environ["JAVA_HOME"] = settings.JAVA_HOME

py_executable = sys.executable
os.environ["PYSPARK_PYTHON"] = py_executable
os.environ["PYSPARK_DRIVER_PYTHON"] = py_executable
