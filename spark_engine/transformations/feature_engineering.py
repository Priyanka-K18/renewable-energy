from typing import Dict, Any
from pyspark import RDD

class RddFeatureEngineering:
    """
    Computes domain-specific energy metrics and standardizes fields across all five sources.
    Uses RDD map() and mapValues() transformations.
    """

    @staticmethod
    def process_solar_rdd(records_rdd: RDD, plant_id: str) -> RDD:
        def transform(row: Dict[str, Any]) -> Dict[str, Any]:
            try:
                dc_power = float(row.get("DC_POWER", 0.0))
                ac_power = float(row.get("AC_POWER", 0.0))
                irrad = float(row.get("IRRADIATION", 0.0))
                amb_t = float(row.get("AMBIENT_TEMPERATURE", 25.0))
                mod_t = float(row.get("MODULE_TEMPERATURE", 25.0))
                daily_y = float(row.get("DAILY_YIELD", 0.0))
                
                # Inverter efficiency
                efficiency = round((ac_power / dc_power * 100.0), 2) if dc_power > 10.0 else 0.0
                if efficiency > 100.0:
                    efficiency = 98.2

                # Expected power based on standard test conditions (STC: 1000 W/m2, 25C)
                expected_power = round((irrad / 1000.0) * 2500.0 * (1.0 - 0.004 * (mod_t - 25.0)), 2) if irrad > 5.0 else 0.0

                return {
                    "plant_id": plant_id,
                    "equipment_code": row.get("Inverter_ID", "INV-SOLAR-01"),
                    "energy_source": "solar",
                    "timestamp": row.get("Date_Time"),
                    "generated_power": ac_power,
                    "energy_generated": round(ac_power * 0.25, 2), # 15-min interval
                    "efficiency": efficiency,
                    "additional_metrics": {
                        "dc_power_kw": dc_power,
                        "ac_power_kw": ac_power,
                        "irradiation_wm2": irrad,
                        "ambient_temp_c": amb_t,
                        "module_temp_c": mod_t,
                        "expected_power_kw": max(0.0, expected_power),
                        "daily_yield_kwh": daily_y
                    },
                    "source_name": "Spark RDD Solar Pipeline",
                    "data_classification": "DERIVED_ANALYTICS"
                }
            except Exception:
                return None

        return records_rdd.map(transform).filter(lambda x: x is not None)

    @staticmethod
    def process_wind_rdd(records_rdd: RDD, plant_id: str) -> RDD:
        def transform(row: Dict[str, Any]) -> Dict[str, Any]:
            try:
                ws = float(row.get("WIND_SPEED", 0.0))
                active_p = float(row.get("ACTIVE_POWER", 0.0))
                reactive_p = float(row.get("REACTIVE_POWER", 0.0))
                rotor_s = float(row.get("ROTOR_SPEED", 0.0))
                gearbox_t = float(row.get("GEARBOX_TEMPERATURE", 45.0))
                vibration = float(row.get("VIBRATION_LEVEL", 1.0))
                daily_y = float(row.get("DAILY_YIELD", 0.0))

                # Expected power from standard cubic power curve (Rated 2100 kW at 12 m/s)
                if ws < 3.0 or ws > 25.0:
                    expected_p = 0.0
                elif ws < 12.0:
                    expected_p = round((((ws - 3.0) / 9.0) ** 3) * 2100.0, 2)
                else:
                    expected_p = 2100.0

                efficiency = round((active_p / expected_p * 100.0), 2) if expected_p > 50.0 else 0.0
                if efficiency > 100.0:
                    efficiency = 99.1

                return {
                    "plant_id": plant_id,
                    "equipment_code": row.get("Turbine_ID", "WTG-WIND-01"),
                    "energy_source": "wind",
                    "timestamp": row.get("Date_Time"),
                    "generated_power": active_p,
                    "energy_generated": round(active_p * (10.0 / 60.0), 2), # 10-min interval
                    "efficiency": efficiency,
                    "additional_metrics": {
                        "wind_speed_ms": ws,
                        "expected_power_kw": expected_p,
                        "rotor_speed_rpm": rotor_s,
                        "gearbox_temp_c": gearbox_t,
                        "vibration_level_mms": vibration,
                        "reactive_power_kvar": reactive_p,
                        "daily_yield_kwh": daily_y
                    },
                    "source_name": "Spark RDD Wind Pipeline",
                    "data_classification": "DERIVED_ANALYTICS"
                }
            except Exception:
                return None

        return records_rdd.map(transform).filter(lambda x: x is not None)

    @staticmethod
    def process_hydro_rdd(records_rdd: RDD, plant_id: str) -> RDD:
        def transform(row: Dict[str, Any]) -> Dict[str, Any]:
            try:
                flow_rate = float(row.get("WATER_FLOW_RATE", 0.0)) # m3/s
                water_head = float(row.get("WATER_HEAD", 188.0))   # meters
                gen_power = float(row.get("GENERATOR_POWER", 0.0)) # kW
                water_press = float(row.get("WATER_PRESSURE", 18.0))
                vib = float(row.get("VIBRATION_LEVEL", 1.0))
                gen_t = float(row.get("GENERATOR_TEMPERATURE", 50.0))
                daily_y = float(row.get("DAILY_YIELD", 0.0))

                # Theoretical hydraulic power: P = rho * g * Q * H (Watts / 1000 = kW)
                # rho = 1000 kg/m3, g = 9.81 m/s2
                theoretical_kw = (1000.0 * 9.81 * flow_rate * water_head) / 1000.0
                efficiency = round((gen_power / theoretical_kw * 100.0), 2) if theoretical_kw > 100.0 else 0.0
                if efficiency > 96.0:
                    efficiency = 92.5

                return {
                    "plant_id": plant_id,
                    "equipment_code": row.get("Turbine_ID", "TURB-HYDRO-01"),
                    "energy_source": "hydropower",
                    "timestamp": row.get("Date_Time"),
                    "generated_power": gen_power,
                    "energy_generated": round(gen_power * 0.25, 2), # 15-min interval
                    "efficiency": efficiency,
                    "additional_metrics": {
                        "water_flow_rate_m3s": flow_rate,
                        "water_head_m": water_head,
                        "theoretical_power_kw": round(theoretical_kw, 2),
                        "water_pressure_bar": water_press,
                        "vibration_mms": vib,
                        "generator_temp_c": gen_t,
                        "daily_yield_kwh": daily_y
                    },
                    "source_name": "Spark RDD Hydropower Pipeline",
                    "data_classification": "DERIVED_ANALYTICS"
                }
            except Exception:
                return None

        return records_rdd.map(transform).filter(lambda x: x is not None)

    @staticmethod
    def process_geothermal_rdd(records_rdd: RDD, plant_id: str) -> RDD:
        def transform(row: Dict[str, Any]) -> Dict[str, Any]:
            try:
                mass_flow = float(row.get("MASS_FLOW_RATE", 0.0)) # tons/hr
                steam_t = float(row.get("STEAM_TEMPERATURE", 240.0))
                steam_p = float(row.get("STEAM_PRESSURE", 8.0))
                gen_p = float(row.get("GENERATOR_POWER", 0.0))
                cooling_t = float(row.get("COOLING_TEMPERATURE", 30.0))
                p_drop = float(row.get("PRESSURE_DROP", 0.4))
                daily_y = float(row.get("DAILY_YIELD", 0.0))

                # Expected power: ~350 kW per ton/hr of saturated steam
                expected_kw = mass_flow * 350.0
                efficiency = round((gen_p / expected_kw * 100.0), 2) if expected_kw > 100.0 else 0.0
                if efficiency > 100.0:
                    efficiency = 98.4

                # Specific steam consumption in kg/kWh
                ssc = round((mass_flow * 1000.0) / gen_p, 2) if gen_p > 10.0 else 0.0

                return {
                    "plant_id": plant_id,
                    "equipment_code": row.get("Well_ID", "WELL-GEO-01"),
                    "energy_source": "geothermal",
                    "timestamp": row.get("Date_Time"),
                    "generated_power": gen_p,
                    "energy_generated": round(gen_p * 0.25, 2),
                    "efficiency": efficiency,
                    "additional_metrics": {
                        "steam_temp_c": steam_t,
                        "steam_pressure_bar": steam_p,
                        "mass_flow_rate_th": mass_flow,
                        "pressure_drop_bar": p_drop,
                        "cooling_temp_c": cooling_t,
                        "specific_steam_consumption_kg_kwh": ssc,
                        "daily_yield_kwh": daily_y
                    },
                    "source_name": "Spark RDD Geothermal Pipeline",
                    "data_classification": "DERIVED_ANALYTICS"
                }
            except Exception:
                return None

        return records_rdd.map(transform).filter(lambda x: x is not None)

    @staticmethod
    def process_biomass_rdd(records_rdd: RDD, plant_id: str) -> RDD:
        def transform(row: Dict[str, Any]) -> Dict[str, Any]:
            try:
                fuel_kg = float(row.get("FUEL_INPUT_KG", 0.0)) # per interval
                calorific_mj = float(row.get("CALORIFIC_VALUE", 17.5)) # MJ/kg
                gen_p = float(row.get("GENERATOR_POWER", 0.0))
                moisture = float(row.get("MOISTURE_CONTENT", 20.0))
                boiler_t = float(row.get("BOILER_TEMPERATURE", 880.0))
                combust_eff = float(row.get("COMBUSTION_EFFICIENCY", 85.0))
                emissions = float(row.get("EMISSIONS_LEVEL", 40.0))
                daily_y = float(row.get("DAILY_YIELD", 0.0))

                # Fuel thermal energy input (MJ -> kWh: 1 kWh = 3.6 MJ)
                thermal_kwh = (fuel_kg * calorific_mj) / 3.6
                energy_generated_kwh = gen_p * 0.25
                efficiency = round((energy_generated_kwh / thermal_kwh * 100.0), 2) if thermal_kwh > 10.0 else 0.0

                return {
                    "plant_id": plant_id,
                    "equipment_code": "BLR-BIOMASS-01",
                    "energy_source": "biomass",
                    "timestamp": row.get("Date_Time"),
                    "generated_power": gen_p,
                    "energy_generated": round(energy_generated_kwh, 2),
                    "efficiency": efficiency,
                    "additional_metrics": {
                        "fuel_input_kg": fuel_kg,
                        "calorific_value_mj_kg": calorific_mj,
                        "moisture_content_pct": moisture,
                        "boiler_temp_c": boiler_t,
                        "combustion_efficiency_pct": combust_eff,
                        "emissions_level_mg_nm3": emissions,
                        "daily_yield_kwh": daily_y
                    },
                    "source_name": "Spark RDD Biomass Pipeline",
                    "data_classification": "DERIVED_ANALYTICS"
                }
            except Exception:
                return None

        return records_rdd.map(transform).filter(lambda x: x is not None)
