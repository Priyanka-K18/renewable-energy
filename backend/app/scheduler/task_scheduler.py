import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from backend.app.connectors.open_meteo_connector import open_meteo_connector
from backend.app.connectors.nasa_power_connector import nasa_power_connector
from backend.app.connectors.owid_energy_connector import owid_energy_connector
from backend.app.database.db_manager import db_manager

logger = logging.getLogger("task_scheduler")

class RenewableTaskScheduler:
    """
    Automated Data Ingestion and Synchronization Scheduler.
    Handles Open-Meteo weather refreshes, NASA POWER updates, and OWID checks.
    """
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def start(self):
        if not self.is_running:
            # Weather sync every hour
            self.scheduler.add_job(
                self.sync_active_plants_weather,
                "interval",
                hours=1,
                id="weather_sync_job",
                replace_existing=True
            )
            self.scheduler.start()
            self.is_running = True
            logger.info("RenewableTaskScheduler started successfully.")

    def shutdown(self):
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("RenewableTaskScheduler stopped.")

    def sync_active_plants_weather(self):
        logger.info("Executing scheduled weather sync for active renewable plants...")
        plants = db_manager.get_plants()
        for p in plants:
            try:
                open_meteo_connector.fetch_weather_for_plant(
                    plant_id=p["id"],
                    latitude=p["latitude"],
                    longitude=p["longitude"],
                    forecast_days=2
                )
            except Exception as e:
                logger.error(f"Scheduled weather sync error for plant {p.get('plant_name')}: {e}")

task_scheduler = RenewableTaskScheduler()
