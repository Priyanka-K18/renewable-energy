-- ==============================================================================
-- RENEWABLE ENERGY INTELLIGENCE PLATFORM
-- Supabase PostgreSQL Seed Data: seed.sql
-- ==============================================================================

-- 1. Insert Core Data Sources
INSERT INTO data_sources (source_key, source_name, official_url, api_endpoint, data_classification, sync_frequency, status, attribution_notice)
VALUES
('nasa_power', 'NASA POWER Project', 'https://power.larc.nasa.gov/', 'https://power.larc.nasa.gov/api/temporal/daily/point', 'REAL_EXTERNAL_DATA', 'daily', 'active', 'NASA Langley Research Center POWER Project'),
('owid_energy', 'Our World in Data (OWID) Energy', 'https://ourworldindata.org/energy', 'https://catalog.ourworldindata.org/energy/owid_energy/owid_energy.csv', 'REAL_EXTERNAL_DATA', 'monthly', 'active', 'Our World in Data Energy Database (CC BY 4.0)'),
('open_meteo', 'Open-Meteo Weather API', 'https://open-meteo.com/', 'https://api.open-meteo.com/v1/forecast', 'REAL_EXTERNAL_DATA', 'hourly', 'active', 'Open-Meteo Weather Forecast & Historical API (CC-BY 4.0)')
ON CONFLICT (source_key) DO NOTHING;

-- 2. Insert Data Source Metadata
INSERT INTO data_source_metadata (source_key, variable_name, display_name, measurement_unit, typical_range_min, typical_range_max, sampling_frequency, data_classification, description)
VALUES
('nasa_power', 'ALLSKY_SFC_SW_DWN', 'All Sky Surface Shortwave Downward Irradiance', 'kW-hr/m^2/day', 0.5, 9.5, 'Daily', 'REAL_EXTERNAL_DATA', 'Total solar radiation incident on a horizontal surface'),
('nasa_power', 'T2M', 'Temperature at 2 Meters', 'C', -20.0, 50.0, 'Daily', 'REAL_EXTERNAL_DATA', 'Air temperature measured 2 meters above ground level'),
('nasa_power', 'WS10M', 'Wind Speed at 10 Meters', 'm/s', 0.0, 35.0, 'Daily', 'REAL_EXTERNAL_DATA', 'Wind speed measured at standard 10 meter altitude'),
('nasa_power', 'PRECTOTCORR', 'Precipitation Corrected', 'mm/day', 0.0, 250.0, 'Daily', 'REAL_EXTERNAL_DATA', 'Corrected daily total precipitation'),
('open_meteo', 'shortwave_radiation', 'Shortwave Solar Radiation', 'W/m^2', 0.0, 1200.0, 'Hourly', 'REAL_EXTERNAL_DATA', 'Direct + diffuse solar radiation on ground plane'),
('open_meteo', 'wind_speed_10m', 'Wind Speed at 10m', 'm/s', 0.0, 45.0, 'Hourly', 'REAL_EXTERNAL_DATA', 'Current and forecasted 10m wind velocity'),
('open_meteo', 'precipitation', 'Precipitation Amount', 'mm', 0.0, 100.0, 'Hourly', 'REAL_EXTERNAL_DATA', 'Total liquid and solid water equivalent precipitation'),
('owid_energy', 'solar_electricity_twh', 'Solar Electricity Generation', 'TWh', 0.0, 2000.0, 'Annual', 'REAL_EXTERNAL_DATA', 'Annual nationwide solar electricity output'),
('owid_energy', 'wind_electricity_twh', 'Wind Electricity Generation', 'TWh', 0.0, 2500.0, 'Annual', 'REAL_EXTERNAL_DATA', 'Annual nationwide wind electricity output'),
('owid_energy', 'hydro_electricity_twh', 'Hydropower Electricity Generation', 'TWh', 0.0, 4500.0, 'Annual', 'REAL_EXTERNAL_DATA', 'Annual nationwide hydroelectricity output');

-- 3. Insert Five Primary Renewable Energy Plants
INSERT INTO renewable_plants (id, plant_name, energy_source, country, state, location, latitude, longitude, installed_capacity, capacity_unit, commissioning_date, status, operator_name, specifications)
VALUES
('a0000001-0000-0000-0000-000000000001', 'Bhadla Solar Park', 'solar', 'India', 'Rajasthan', 'Phalodi Tehsil, Jodhpur', 27.5397, 71.9161, 2245.0, 'MW', '2020-03-01', 'active', 'Saurya Urja Company', '{"panel_type": "Monocrystalline PERC", "tilt_angle": 25, "inverters_count": 80}'),
('a0000002-0000-0000-0000-000000000002', 'Muppandal Wind Farm', 'wind', 'India', 'Tamil Nadu', 'Kanyakumari District', 8.2588, 77.5458, 1500.0, 'MW', '2011-06-15', 'active', 'Tamil Nadu Generation and Distribution Corp', '{"turbines_count": 60, "rotor_diameter_m": 82, "cut_in_speed_ms": 3.0, "rated_speed_ms": 12.0}'),
('a0000003-0000-0000-0000-000000000003', 'Tehri Hydroelectric Complex', 'hydropower', 'India', 'Uttarakhand', 'Tehri Garhwal', 30.3789, 78.4808, 2400.0, 'MW', '2006-07-30', 'active', 'THDC India Limited', '{"dam_type": "Rock and earth-fill", "reservoir_capacity_m3": 4000000000, "rated_head_m": 188, "turbines_count": 4}'),
('a0000004-0000-0000-0000-000000000004', 'Olkaria Geothermal Field', 'geothermal', 'Kenya', 'Nakuru', 'Hell''s Gate National Park', -0.8872, 36.3142, 800.0, 'MW', '2014-02-20', 'active', 'KenGen Kenya Electricity Generating Co', '{"wells_active": 32, "avg_well_depth_m": 2800, "reservoir_enthalpy_kj_kg": 2600}'),
('a0000005-0000-0000-0000-000000000005', 'Ironbridge Biomass Power Station', 'biomass', 'United Kingdom', 'Shropshire', 'Severn Gorge', 52.6289, -2.5161, 740.0, 'MW', '2012-04-10', 'active', 'Severn Green Energy Ltd', '{"boiler_technology": "Circulating Fluidized Bed", "primary_feedstock": "Wood Pellets & Agro Residues", "calorific_value_mj_kg": 17.5}');

-- 4. Insert Primary Equipment
INSERT INTO equipment (id, plant_id, equipment_code, equipment_type, rated_capacity, capacity_unit, model_number, manufacturer, installation_date, status)
VALUES
('b0000001-0000-0000-0000-000000000001', 'a0000001-0000-0000-0000-000000000001', 'INV-SOLAR-01', 'inverter', 2500, 'kW', 'SG2500HX', 'Sungrow Power', '2020-01-15', 'operational'),
('b0000001-0000-0000-0000-000000000002', 'a0000001-0000-0000-0000-000000000001', 'INV-SOLAR-02', 'inverter', 2500, 'kW', 'SG2500HX', 'Sungrow Power', '2020-01-15', 'operational'),
('b0000002-0000-0000-0000-000000000001', 'a0000002-0000-0000-0000-000000000002', 'WTG-WIND-01', 'wind_turbine', 2100, 'kW', 'S97-2.1MW', 'Suzlon Energy', '2011-05-10', 'operational'),
('b0000002-0000-0000-0000-000000000002', 'a0000002-0000-0000-0000-000000000002', 'WTG-WIND-02', 'wind_turbine', 2100, 'kW', 'S97-2.1MW', 'Suzlon Energy', '2011-05-10', 'warning'),
('b0000003-0000-0000-0000-000000000001', 'a0000003-0000-0000-0000-000000000001', 'TURB-HYDRO-01', 'hydro_turbine', 250, 'MW', 'Francis 250MW', 'BHEL-Alstom', '2006-06-20', 'operational'),
('b0000004-0000-0000-0000-000000000001', 'a0000004-0000-0000-0000-000000000001', 'WELL-GEO-01', 'geothermal_well', 50, 'MW', 'SteamFlash-50', 'Mitsubishi Power', '2014-01-10', 'operational'),
('b0000005-0000-0000-0000-000000000001', 'a0000005-0000-0000-0000-000000000001', 'BLR-BIOMASS-01', 'biomass_boiler', 185, 'MW', 'CFB-Superheater', 'Doosan Babcock', '2012-03-05', 'operational');

-- 5. Insert Anomaly Alerts for Monitoring
INSERT INTO anomaly_alerts (plant_id, equipment_code, energy_source, anomaly_type, severity, description, measured_value, expected_value, deviation_percentage, unit, recommended_action, detection_method, data_source, status, detected_at)
VALUES
('a0000001-0000-0000-0000-000000000001', 'INV-SOLAR-02', 'solar', 'Zero Generation Under High Irradiation', 'Critical', 'Inverter AC output 0.0 kW during peak sunshine (irradiance 840 W/m2)', 0.0, 2240.0, -100.0, 'kW', 'Inspect string fuse box, DC disconnector switch and inverter inverter grid breaker', 'Spark RDD Threshold Engine', 'Operational SCADA', 'Open', NOW() - INTERVAL '2 hours'),
('a0000002-0000-0000-0000-000000000002', 'WTG-WIND-02', 'wind', 'Gearbox Overheating & High Vibration', 'High', 'Main gearbox bearing temperature reached 88.5 deg C (exceeding 80.0 limit) with vibration amplitude 4.8 mm/s', 88.5, 72.0, 22.9, 'deg C', 'Schedule oil filtration and mechanical alignment inspection; derate to 60% rated output', 'Spark RDD Multi-variable Anomaly Rule', 'Operational SCADA', 'Investigating', NOW() - INTERVAL '5 hours'),
('a0000003-0000-0000-0000-000000000001', 'TURB-HYDRO-01', 'hydropower', 'Penstock Pressure Drop', 'Medium', 'Transient pressure drop observed across intake butterfly valve exceeding hydraulic safety margin', 17.2, 18.5, -7.0, 'bar', 'Check penstock trash rack for debris clogging and calibrate hydraulic actuator feedback sensor', 'Hydro Differential Pressure Rule', 'Plant Telemetry', 'Resolved', NOW() - INTERVAL '1 day'),
('a0000004-0000-0000-0000-000000000001', 'WELL-GEO-01', 'geothermal', 'Steam Mass Flow Fluctuation', 'Medium', 'Mass flow rate dipped 18% below baseline during steady wellhead pressure', 115.0, 140.0, -17.8, 't/h', 'Inspect two-phase separator and check for calcite scaling in wellbore casing', 'Geothermal Mass-Balance RDD', 'Field Wellhead Telemetry', 'Open', NOW() - INTERVAL '12 hours'),
('a0000005-0000-0000-0000-000000000001', 'BLR-BIOMASS-01', 'biomass', 'Excessive Fuel Moisture Content', 'High', 'Feedstock moisture content reached 42.5% causing combustion instability and flue gas temp drop', 42.5, 20.0, 112.5, '%', 'Switch to covered storage silo batch and increase primary air preheat fan rate', 'Biomass Combustion Stoichiometry Rule', 'Plant Fuel Lab Ingestion', 'Open', NOW() - INTERVAL '3 hours');
