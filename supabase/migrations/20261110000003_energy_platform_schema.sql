-- Additive, owner-scoped schema for the renewable energy platform.
-- No existing tables or records are modified or removed.

CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    organization TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.energy_plants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    energy_source TEXT NOT NULL
        CHECK (energy_source IN ('solar', 'wind', 'hydropower', 'geothermal', 'biomass')),
    country TEXT NOT NULL CHECK (length(trim(country)) > 0),
    region TEXT,
    location TEXT,
    latitude DOUBLE PRECISION CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION CHECK (longitude BETWEEN -180 AND 180),
    capacity_mw DOUBLE PRECISION NOT NULL CHECK (capacity_mw >= 0),
    commissioned_on DATE,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'maintenance', 'decommissioned')),
    operator_name TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadata) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.energy_generation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES public.energy_plants(id) ON DELETE RESTRICT,
    source_name TEXT NOT NULL CHECK (length(trim(source_name)) > 0),
    source_record_id TEXT NOT NULL CHECK (length(trim(source_record_id)) > 0),
    recorded_at TIMESTAMPTZ NOT NULL,
    power_mw DOUBLE PRECISION NOT NULL CHECK (power_mw >= 0),
    energy_mwh DOUBLE PRECISION NOT NULL CHECK (energy_mwh >= 0),
    efficiency_pct DOUBLE PRECISION CHECK (efficiency_pct BETWEEN 0 AND 100),
    data_classification TEXT NOT NULL
        CHECK (data_classification IN ('REAL_EXTERNAL_DATA', 'REAL_PLANT_DATA', 'DERIVED_ANALYTICS', 'SIMULATED_DATA')),
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metrics) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plant_id, source_name, source_record_id)
);

CREATE TABLE IF NOT EXISTS public.weather_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES public.energy_plants(id) ON DELETE RESTRICT,
    source_name TEXT NOT NULL CHECK (length(trim(source_name)) > 0),
    observed_at TIMESTAMPTZ NOT NULL,
    temperature_c DOUBLE PRECISION,
    relative_humidity_pct DOUBLE PRECISION CHECK (relative_humidity_pct BETWEEN 0 AND 100),
    cloud_cover_pct DOUBLE PRECISION CHECK (cloud_cover_pct BETWEEN 0 AND 100),
    irradiance_w_m2 DOUBLE PRECISION CHECK (irradiance_w_m2 >= 0),
    wind_speed_m_s DOUBLE PRECISION CHECK (wind_speed_m_s >= 0),
    precipitation_mm DOUBLE PRECISION CHECK (precipitation_mm >= 0),
    data_classification TEXT NOT NULL
        CHECK (data_classification IN ('REAL_EXTERNAL_DATA', 'REAL_PLANT_DATA', 'DERIVED_ANALYTICS', 'SIMULATED_DATA')),
    measurements JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(measurements) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plant_id, source_name, observed_at)
);

CREATE TABLE IF NOT EXISTS public.anomaly_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES public.energy_plants(id) ON DELETE RESTRICT,
    source_record_id TEXT NOT NULL CHECK (length(trim(source_record_id)) > 0),
    anomaly_type TEXT NOT NULL CHECK (length(trim(anomaly_type)) > 0),
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'investigating', 'resolved')),
    detected_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    measured_value DOUBLE PRECISION,
    expected_value DOUBLE PRECISION,
    deviation_pct DOUBLE PRECISION,
    unit TEXT,
    recommended_action TEXT,
    detection_method TEXT NOT NULL,
    data_classification TEXT NOT NULL
        CHECK (data_classification IN ('REAL_EXTERNAL_DATA', 'REAL_PLANT_DATA', 'DERIVED_ANALYTICS', 'SIMULATED_DATA')),
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metrics) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plant_id, source_record_id),
    CHECK (resolved_at IS NULL OR resolved_at >= detected_at)
);

CREATE TABLE IF NOT EXISTS public.analytics_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plant_id UUID NOT NULL REFERENCES public.energy_plants(id) ON DELETE RESTRICT,
    result_key TEXT NOT NULL CHECK (length(trim(result_key)) > 0),
    analysis_type TEXT NOT NULL CHECK (length(trim(analysis_type)) > 0),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    metrics JSONB NOT NULL CHECK (jsonb_typeof(metrics) = 'object'),
    algorithm_name TEXT NOT NULL,
    algorithm_version TEXT,
    data_classification TEXT NOT NULL
        CHECK (data_classification IN ('REAL_EXTERNAL_DATA', 'REAL_PLANT_DATA', 'DERIVED_ANALYTICS', 'SIMULATED_DATA')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (plant_id, result_key),
    CHECK (period_end > period_start)
);

CREATE INDEX IF NOT EXISTS idx_energy_plants_owner_source
    ON public.energy_plants (owner_id, energy_source);
CREATE INDEX IF NOT EXISTS idx_energy_plants_country_status
    ON public.energy_plants (country, status);
CREATE INDEX IF NOT EXISTS idx_energy_generation_plant_time
    ON public.energy_generation (plant_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_data_plant_time
    ON public.weather_data (plant_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_records_plant_status_time
    ON public.anomaly_records (plant_id, status, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_results_plant_period
    ON public.analytics_results (plant_id, period_start DESC);

CREATE OR REPLACE FUNCTION public.set_energy_platform_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at := pg_catalog.now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER set_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.set_energy_platform_updated_at();
DROP TRIGGER IF EXISTS set_energy_plants_updated_at ON public.energy_plants;
CREATE TRIGGER set_energy_plants_updated_at
    BEFORE UPDATE ON public.energy_plants
    FOR EACH ROW EXECUTE FUNCTION public.set_energy_platform_updated_at();

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.energy_plants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.energy_generation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weather_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.anomaly_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analytics_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read their own profile"
    ON public.user_profiles FOR SELECT TO authenticated
    USING (id = (SELECT auth.uid()));
CREATE POLICY "Users can create their own profile"
    ON public.user_profiles FOR INSERT TO authenticated
    WITH CHECK (id = (SELECT auth.uid()));
CREATE POLICY "Users can update their own profile"
    ON public.user_profiles FOR UPDATE TO authenticated
    USING (id = (SELECT auth.uid()))
    WITH CHECK (id = (SELECT auth.uid()));

CREATE POLICY "Owners can read their energy plants"
    ON public.energy_plants FOR SELECT TO authenticated
    USING (owner_id = (SELECT auth.uid()));
CREATE POLICY "Owners can read generation for their plants"
    ON public.energy_generation FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.energy_plants AS p
        WHERE p.id = plant_id AND p.owner_id = (SELECT auth.uid())
    ));
CREATE POLICY "Owners can read weather for their plants"
    ON public.weather_data FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.energy_plants AS p
        WHERE p.id = plant_id AND p.owner_id = (SELECT auth.uid())
    ));
CREATE POLICY "Owners can read anomalies for their plants"
    ON public.anomaly_records FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.energy_plants AS p
        WHERE p.id = plant_id AND p.owner_id = (SELECT auth.uid())
    ));
CREATE POLICY "Owners can read analytics for their plants"
    ON public.analytics_results FOR SELECT TO authenticated
    USING (EXISTS (
        SELECT 1 FROM public.energy_plants AS p
        WHERE p.id = plant_id AND p.owner_id = (SELECT auth.uid())
    ));

GRANT SELECT, INSERT, UPDATE ON public.user_profiles TO authenticated;
GRANT SELECT ON public.energy_plants TO authenticated;
GRANT SELECT ON public.energy_generation TO authenticated;
GRANT SELECT ON public.weather_data TO authenticated;
GRANT SELECT ON public.anomaly_records TO authenticated;
GRANT SELECT ON public.analytics_results TO authenticated;

GRANT ALL ON public.user_profiles TO service_role;
GRANT ALL ON public.energy_plants TO service_role;
GRANT ALL ON public.energy_generation TO service_role;
GRANT ALL ON public.weather_data TO service_role;
GRANT ALL ON public.anomaly_records TO service_role;
GRANT ALL ON public.analytics_results TO service_role;
GRANT EXECUTE ON FUNCTION public.set_energy_platform_updated_at() TO authenticated, service_role;
