-- ==============================================================================
-- RENEWABLE ENERGY INTELLIGENCE PLATFORM
-- Supabase PostgreSQL Schema Migration: 20261110000001_initial_schema.sql
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Profiles (User Profiles linked to Supabase Auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_id UUID UNIQUE,
    full_name TEXT,
    email TEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'analyst', -- admin, engineer, analyst, viewer
    department TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Renewable Plants
CREATE TABLE IF NOT EXISTS renewable_plants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_name TEXT NOT NULL,
    energy_source TEXT NOT NULL, -- solar, wind, hydropower, geothermal, biomass
    country TEXT NOT NULL,
    state TEXT,
    location TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    installed_capacity DOUBLE PRECISION NOT NULL, -- in MW
    capacity_unit TEXT DEFAULT 'MW',
    commissioning_date DATE,
    status TEXT DEFAULT 'active', -- active, maintenance, decommissioned
    operator_name TEXT,
    specifications JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_energy_source CHECK (energy_source IN ('solar', 'wind', 'hydropower', 'geothermal', 'biomass'))
);

-- 3. Equipment (Inverters, Turbines, Wells, Boilers)
CREATE TABLE IF NOT EXISTS equipment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES renewable_plants(id) ON DELETE CASCADE,
    equipment_code TEXT NOT NULL,
    equipment_type TEXT NOT NULL, -- inverter, wind_turbine, hydro_turbine, geothermal_well, biomass_boiler, generator
    rated_capacity DOUBLE PRECISION, -- in kW or MW
    capacity_unit TEXT DEFAULT 'kW',
    model_number TEXT,
    manufacturer TEXT,
    installation_date DATE,
    status TEXT DEFAULT 'operational', -- operational, warning, offline, maintenance
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_equipment_per_plant UNIQUE (plant_id, equipment_code)
);

-- 4. Datasets
CREATE TABLE IF NOT EXISTS datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID REFERENCES renewable_plants(id) ON DELETE SET NULL,
    energy_source TEXT NOT NULL,
    source_name TEXT NOT NULL, -- NASA POWER, OWID, Open-Meteo, In-situ Plant, Synthetic Benchmark
    file_name TEXT NOT NULL,
    storage_path TEXT,
    dataset_version TEXT DEFAULT 'v1.0',
    record_count INTEGER DEFAULT 0,
    file_size_bytes BIGINT DEFAULT 0,
    upload_status TEXT DEFAULT 'uploaded', -- uploaded, processing, processed, failed
    data_type TEXT DEFAULT 'operational_telemetry', -- telemetry, weather, climate, statistical
    data_classification TEXT NOT NULL DEFAULT 'REAL_PLANT_DATA', -- REAL_EXTERNAL_DATA, REAL_PLANT_DATA, SIMULATED_DATA, DERIVED_ANALYTICS
    schema_definition JSONB DEFAULT '{}'::jsonb,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Raw Energy Records (Staging before Spark ingestion)
CREATE TABLE IF NOT EXISTS raw_energy_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE CASCADE,
    plant_id UUID REFERENCES renewable_plants(id) ON DELETE CASCADE,
    equipment_code TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    raw_payload JSONB NOT NULL,
    source_name TEXT,
    data_classification TEXT DEFAULT 'REAL_PLANT_DATA',
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Processed Energy Records (Output of Spark RDD Transformations & Cleansing)
CREATE TABLE IF NOT EXISTS processed_energy_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    plant_id UUID NOT NULL REFERENCES renewable_plants(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    equipment_code TEXT,
    energy_source TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    generated_power DOUBLE PRECISION NOT NULL, -- in kW or MW
    energy_generated DOUBLE PRECISION NOT NULL, -- in kWh or MWh
    efficiency DOUBLE PRECISION, -- percentage 0-100% or ratio
    additional_metrics JSONB DEFAULT '{}'::jsonb, -- source-specific operational variables
    source_name TEXT NOT NULL,
    data_classification TEXT NOT NULL DEFAULT 'DERIVED_ANALYTICS',
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Energy Daily Summary
CREATE TABLE IF NOT EXISTS energy_daily_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES renewable_plants(id) ON DELETE CASCADE,
    energy_source TEXT NOT NULL,
    summary_date DATE NOT NULL,
    total_energy_generated_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    peak_power_kw DOUBLE PRECISION DEFAULT 0,
    avg_power_kw DOUBLE PRECISION DEFAULT 0,
    avg_efficiency DOUBLE PRECISION DEFAULT 0,
    capacity_factor DOUBLE PRECISION DEFAULT 0,
    operating_hours DOUBLE PRECISION DEFAULT 24,
    anomaly_count INTEGER DEFAULT 0,
    environmental_context JSONB DEFAULT '{}'::jsonb, -- avg temp, irradiation, wind, rainfall
    data_classification TEXT DEFAULT 'DERIVED_ANALYTICS',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_plant_date_summary UNIQUE (plant_id, summary_date)
);

-- 8. Energy Monthly Summary
CREATE TABLE IF NOT EXISTS energy_monthly_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES renewable_plants(id) ON DELETE CASCADE,
    energy_source TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_energy_generated_mwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    avg_daily_generation_mwh DOUBLE PRECISION DEFAULT 0,
    avg_capacity_factor DOUBLE PRECISION DEFAULT 0,
    expected_generation_mwh DOUBLE PRECISION DEFAULT 0,
    performance_ratio DOUBLE PRECISION DEFAULT 0,
    total_anomalies INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_plant_month_summary UNIQUE (plant_id, year, month)
);

-- 9. Anomaly Alerts (Dedicated Intelligent Anomaly Engine)
CREATE TABLE IF NOT EXISTS anomaly_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES renewable_plants(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,
    equipment_code TEXT,
    energy_source TEXT NOT NULL,
    anomaly_type TEXT NOT NULL,
    severity TEXT NOT NULL, -- Critical, High, Medium, Low
    description TEXT NOT NULL,
    measured_value DOUBLE PRECISION,
    expected_value DOUBLE PRECISION,
    deviation_percentage DOUBLE PRECISION,
    unit TEXT,
    recommended_action TEXT NOT NULL,
    detection_method TEXT NOT NULL, -- Spark Rule Engine, Statistical 3-Sigma, Power Curve Delta, Threshold Check
    data_source TEXT NOT NULL,
    data_classification TEXT DEFAULT 'DERIVED_ANALYTICS',
    status TEXT DEFAULT 'Open', -- Open, Investigating, Resolved
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    CONSTRAINT valid_severity CHECK (severity IN ('Critical', 'High', 'Medium', 'Low')),
    CONSTRAINT valid_status CHECK (status IN ('Open', 'Investigating', 'Resolved'))
);

-- 10. Plant Performance Benchmarks
CREATE TABLE IF NOT EXISTS plant_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES renewable_plants(id) ON DELETE CASCADE,
    evaluation_period_start DATE NOT NULL,
    evaluation_period_end DATE NOT NULL,
    availability_factor DOUBLE PRECISION DEFAULT 0,
    performance_ratio DOUBLE PRECISION DEFAULT 0,
    capacity_utilization_factor DOUBLE PRECISION DEFAULT 0,
    carbon_avoidance_metric_tons DOUBLE PRECISION DEFAULT 0,
    performance_rank INTEGER,
    status_assessment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Processing Jobs (Spark RDD Pipeline Tracking)
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
    energy_source TEXT NOT NULL,
    source_name TEXT NOT NULL,
    job_type TEXT DEFAULT 'SPARK_RDD_INGESTION', -- SPARK_RDD_INGESTION, ANOMALY_DETECTION, HOURLY_AGGREGATION, EXTERNAL_SYNC
    job_status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    records_ingested INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_rejected INTEGER DEFAULT 0,
    execution_time_seconds DOUBLE PRECISION DEFAULT 0,
    throughput_records_per_sec DOUBLE PRECISION DEFAULT 0,
    rdd_transformation_count INTEGER DEFAULT 0,
    rdd_partition_count INTEGER DEFAULT 0,
    spark_application_id TEXT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 12. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    details JSONB DEFAULT '{}'::jsonb,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. Data Sources Registry
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key TEXT UNIQUE NOT NULL, -- nasa_power, owid_energy, open_meteo
    source_name TEXT NOT NULL,
    official_url TEXT NOT NULL,
    api_endpoint TEXT,
    data_classification TEXT NOT NULL DEFAULT 'REAL_EXTERNAL_DATA',
    sync_frequency TEXT DEFAULT 'hourly', -- hourly, daily, on_demand
    status TEXT DEFAULT 'active', -- active, degraded, offline
    last_sync_at TIMESTAMPTZ,
    last_sync_status TEXT,
    records_cached INTEGER DEFAULT 0,
    attribution_notice TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 14. External Data Ingestion Log
CREATE TABLE IF NOT EXISTS external_data_ingestion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key TEXT NOT NULL REFERENCES data_sources(source_key) ON DELETE CASCADE,
    parameters JSONB NOT NULL,
    http_status_code INTEGER,
    records_retrieved INTEGER DEFAULT 0,
    response_size_kb DOUBLE PRECISION DEFAULT 0,
    duration_ms DOUBLE PRECISION DEFAULT 0,
    status TEXT DEFAULT 'success',
    error_details TEXT,
    retrieved_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. Weather Observations (Open-Meteo Current & Forecast)
CREATE TABLE IF NOT EXISTS weather_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID REFERENCES renewable_plants(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    observation_type TEXT DEFAULT 'current', -- current, forecast_hourly, historical
    temperature_2m DOUBLE PRECISION, -- deg C
    relative_humidity_2m DOUBLE PRECISION, -- %
    cloud_cover DOUBLE PRECISION, -- %
    shortwave_radiation DOUBLE PRECISION, -- W/m2
    direct_radiation DOUBLE PRECISION, -- W/m2
    diffuse_radiation DOUBLE PRECISION, -- W/m2
    direct_normal_irradiance DOUBLE PRECISION, -- W/m2
    wind_speed_10m DOUBLE PRECISION, -- m/s
    wind_speed_80m DOUBLE PRECISION, -- m/s
    wind_direction_10m DOUBLE PRECISION, -- deg
    wind_gusts_10m DOUBLE PRECISION, -- m/s
    precipitation DOUBLE PRECISION, -- mm
    rain DOUBLE PRECISION, -- mm
    precipitation_probability DOUBLE PRECISION, -- %
    source_name TEXT DEFAULT 'Open-Meteo',
    data_classification TEXT DEFAULT 'REAL_EXTERNAL_DATA',
    retrieval_timestamp TIMESTAMPTZ DEFAULT NOW(),
    quality_status TEXT DEFAULT 'valid',
    CONSTRAINT unique_plant_weather_time UNIQUE (plant_id, timestamp, observation_type)
);

-- 16. Global Energy Statistics (Our World in Data - OWID)
CREATE TABLE IF NOT EXISTS global_energy_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    country TEXT NOT NULL,
    iso_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    solar_electricity_twh DOUBLE PRECISION,
    wind_electricity_twh DOUBLE PRECISION,
    hydro_electricity_twh DOUBLE PRECISION,
    geothermal_electricity_twh DOUBLE PRECISION,
    bioenergy_electricity_twh DOUBLE PRECISION,
    total_renewable_electricity_twh DOUBLE PRECISION,
    total_electricity_generation_twh DOUBLE PRECISION,
    renewable_electricity_share_pct DOUBLE PRECISION,
    electricity_consumption_twh DOUBLE PRECISION,
    per_capita_electricity_kwh DOUBLE PRECISION,
    source_name TEXT DEFAULT 'Our World in Data (OWID)',
    data_classification TEXT DEFAULT 'REAL_EXTERNAL_DATA',
    dataset_version TEXT DEFAULT '2024-latest',
    retrieved_at TIMESTAMPTZ DEFAULT NOW(),
    quality_status TEXT DEFAULT 'verified',
    CONSTRAINT unique_country_year_owid UNIQUE (iso_code, year)
);

-- 17. Environmental Observations (NASA POWER Historical Meteorology & Solar)
CREATE TABLE IF NOT EXISTS environmental_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID REFERENCES renewable_plants(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    temporal_resolution TEXT DEFAULT 'daily', -- daily, hourly
    allsky_sfc_sw_dwn DOUBLE PRECISION, -- kW-hr/m^2/day or W/m^2
    allsky_sfc_sw_dni DOUBLE PRECISION,
    t2m DOUBLE PRECISION, -- temperature at 2m (C)
    t2m_max DOUBLE PRECISION,
    t2m_min DOUBLE PRECISION,
    ws10m DOUBLE PRECISION, -- wind speed at 10m (m/s)
    ws50m DOUBLE PRECISION, -- wind speed at 50m (m/s)
    prectotcorr DOUBLE PRECISION, -- precipitation (mm/day)
    rh2m DOUBLE PRECISION, -- relative humidity at 2m (%)
    source_name TEXT DEFAULT 'NASA POWER',
    data_classification TEXT DEFAULT 'REAL_EXTERNAL_DATA',
    retrieval_timestamp TIMESTAMPTZ DEFAULT NOW(),
    quality_status TEXT DEFAULT 'valid',
    CONSTRAINT unique_plant_nasa_time UNIQUE (plant_id, timestamp, temporal_resolution)
);

-- 18. Data Source Metadata & Provenance Records
CREATE TABLE IF NOT EXISTS data_source_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_key TEXT NOT NULL,
    variable_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    measurement_unit TEXT NOT NULL,
    description TEXT,
    typical_range_min DOUBLE PRECISION,
    typical_range_max DOUBLE PRECISION,
    sampling_frequency TEXT,
    data_classification TEXT NOT NULL,
    attribution_citation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==============================================================================
-- INDEXES FOR HIGH-PERFORMANCE QUERYING
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_processed_plant_time ON processed_energy_records(plant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_processed_source_time ON processed_energy_records(energy_source, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_daily_summary_plant_date ON energy_daily_summary(plant_id, summary_date DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_status_severity ON anomaly_alerts(status, severity, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_plant ON anomaly_alerts(plant_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_plant_time ON weather_observations(plant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_nasa_plant_time ON environmental_observations(plant_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_owid_iso_year ON global_energy_statistics(iso_code, year DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON processing_jobs(job_status, started_at DESC);

-- ==============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE renewable_plants ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE datasets ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_energy_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_energy_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE energy_daily_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE energy_monthly_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE anomaly_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE plant_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_data_ingestion ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE global_energy_statistics ENABLE ROW LEVEL SECURITY;
ALTER TABLE environmental_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_source_metadata ENABLE ROW LEVEL SECURITY;

-- Allow read access for authenticated and anonymous users in dashboard demo mode
CREATE POLICY "Public read access on renewable_plants" ON renewable_plants FOR SELECT USING (true);
CREATE POLICY "Public insert/update on renewable_plants" ON renewable_plants FOR ALL USING (true);

CREATE POLICY "Public read access on equipment" ON equipment FOR SELECT USING (true);
CREATE POLICY "Public insert/update on equipment" ON equipment FOR ALL USING (true);

CREATE POLICY "Public read access on datasets" ON datasets FOR SELECT USING (true);
CREATE POLICY "Public insert/update on datasets" ON datasets FOR ALL USING (true);

CREATE POLICY "Public read on processed_energy_records" ON processed_energy_records FOR SELECT USING (true);
CREATE POLICY "Public write on processed_energy_records" ON processed_energy_records FOR ALL USING (true);

CREATE POLICY "Public read on energy_daily_summary" ON energy_daily_summary FOR SELECT USING (true);
CREATE POLICY "Public write on energy_daily_summary" ON energy_daily_summary FOR ALL USING (true);

CREATE POLICY "Public read on energy_monthly_summary" ON energy_monthly_summary FOR SELECT USING (true);
CREATE POLICY "Public write on energy_monthly_summary" ON energy_monthly_summary FOR ALL USING (true);

CREATE POLICY "Public read on anomaly_alerts" ON anomaly_alerts FOR SELECT USING (true);
CREATE POLICY "Public write on anomaly_alerts" ON anomaly_alerts FOR ALL USING (true);

CREATE POLICY "Public read on plant_performance" ON plant_performance FOR SELECT USING (true);
CREATE POLICY "Public write on plant_performance" ON plant_performance FOR ALL USING (true);

CREATE POLICY "Public read on processing_jobs" ON processing_jobs FOR SELECT USING (true);
CREATE POLICY "Public write on processing_jobs" ON processing_jobs FOR ALL USING (true);

CREATE POLICY "Public read on data_sources" ON data_sources FOR SELECT USING (true);
CREATE POLICY "Public write on data_sources" ON data_sources FOR ALL USING (true);

CREATE POLICY "Public read on external_data_ingestion" ON external_data_ingestion FOR SELECT USING (true);
CREATE POLICY "Public write on external_data_ingestion" ON external_data_ingestion FOR ALL USING (true);

CREATE POLICY "Public read on weather_observations" ON weather_observations FOR SELECT USING (true);
CREATE POLICY "Public write on weather_observations" ON weather_observations FOR ALL USING (true);

CREATE POLICY "Public read on global_energy_statistics" ON global_energy_statistics FOR SELECT USING (true);
CREATE POLICY "Public write on global_energy_statistics" ON global_energy_statistics FOR ALL USING (true);

CREATE POLICY "Public read on environmental_observations" ON environmental_observations FOR SELECT USING (true);
CREATE POLICY "Public write on environmental_observations" ON environmental_observations FOR ALL USING (true);

CREATE POLICY "Public read on data_source_metadata" ON data_source_metadata FOR SELECT USING (true);
CREATE POLICY "Public write on data_source_metadata" ON data_source_metadata FOR ALL USING (true);
