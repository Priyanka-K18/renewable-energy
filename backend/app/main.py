import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.database.db_manager import db_manager
from backend.app.scheduler.task_scheduler import task_scheduler

# Import API Routers
from backend.app.api.auth import router as auth_router
from backend.app.api.plants import router as plants_router
from backend.app.api.datasets import router as datasets_router
from backend.app.api.sources import router as sources_router
from backend.app.api.weather import router as weather_router
from backend.app.api.global_energy import router as global_energy_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.anomalies import router as anomalies_router
from backend.app.api.spark import router as spark_router
from backend.app.api.reports import router as reports_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("renewable_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Renewable Energy Intelligence Platform Backend...")
    # Start background task scheduler unless in test mode
    if os.environ.get("TESTING") != "1":
        task_scheduler.start()
    yield
    # Graceful shutdown
    logger.info("Shutting down Renewable Energy Intelligence Platform Backend...")
    if os.environ.get("TESTING") != "1":
        task_scheduler.shutdown()

app = FastAPI(
    title="Renewable Energy Intelligence Platform API",
    description="Multi-Source Big Data Analytics, Monitoring and Intelligent Reporting System Using Apache Spark RDD and Supabase",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth_router, prefix="/api")
app.include_router(plants_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(global_energy_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(anomalies_router, prefix="/api")
app.include_router(spark_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

@app.get("/")
def root():
    return {
        "platform": "Renewable Energy Intelligence Platform",
        "tagline": "Transforming Renewable Energy Data into Intelligent Decisions.",
        "status": "operational",
        "docs_url": "/docs",
        "database_connected": db_manager.is_supabase_connected,
        "database_mode": "Supabase Remote PostgreSQL" if db_manager.is_supabase_connected else "Local Resilient SQL Storage",
        "spark_engine": "Apache Spark RDD In-Process Core"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "supabase_connected": db_manager.is_supabase_connected,
        "sources_tracked": len(db_manager.get_data_sources()),
        "registered_plants": len(db_manager.get_plants())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
