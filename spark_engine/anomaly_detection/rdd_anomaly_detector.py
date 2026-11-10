import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any
from pyspark import RDD

class RddAnomalyDetector:
    """
    Intelligent Rule-Based and Statistical Anomaly Detection Engine using PySpark RDD.
    Evaluates source-specific engineering limits via flatMap() and filter().
    """

    @staticmethod
    def detect_anomalies_rdd(processed_rdd: RDD) -> List[Dict[str, Any]]:
        """
        Maps processed records to potential anomaly alert records using flatMap().
        """
        def evaluate_record(record: Dict[str, Any]) -> List[Dict[str, Any]]:
            alerts = []
            source = record.get("energy_source", "").lower()
            metrics = record.get("additional_metrics", {})
            plant_id = record.get("plant_id")
            eq_code = record.get("equipment_code")
            ts = record.get("timestamp")

            # -------------------------------------------------------------
            # 1. SOLAR RULES
            # -------------------------------------------------------------
            if source == "solar":
                irrad = float(metrics.get("irradiation_wm2", 0.0))
                ac_power = float(record.get("generated_power", 0.0))
                mod_temp = float(metrics.get("module_temp_c", 25.0))
                eff = float(record.get("efficiency", 0.0))

                # Zero AC Power under peak sunlight
                if irrad > 350.0 and ac_power <= 5.0:
                    expected_p = float(metrics.get("expected_power_kw", 1500.0))
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "plant_id": plant_id,
                        "equipment_code": eq_code,
                        "energy_source": "solar",
                        "anomaly_type": "Zero Generation Under High Irradiation",
                        "severity": "Critical",
                        "description": f"Inverter AC output dropped to {ac_power} kW while incident solar irradiation is {irrad} W/m2",
                        "measured_value": ac_power,
                        "expected_value": expected_p,
                        "deviation_percentage": -100.0,
                        "unit": "kW",
                        "recommended_action": "Inspect inverter breaker trips, string fuses, and DC isolator switchgear immediately",
                        "detection_method": "Spark RDD STC Irradiation Threshold Rule",
                        "data_source": "Operational SCADA",
                        "status": "Open",
                        "detected_at": ts
                    })

                # Inverter / Module Overheating
                if mod_temp > 72.0:
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "plant_id": plant_id,
                        "equipment_code": eq_code,
                        "energy_source": "solar",
                        "anomaly_type": "Excessive Module Temperature",
                        "severity": "High",
                        "description": f"Photovoltaic module temperature reached {mod_temp} C, exceeding thermal threshold of 70 C",
                        "measured_value": mod_temp,
                        "expected_value": 55.0,
                        "deviation_percentage": round(((mod_temp - 55.0) / 55.0) * 100.0, 1),
                        "unit": "C",
                        "recommended_action": "Verify ventilation around module rows and clean soiling buildup",
                        "detection_method": "Thermal Threshold RDD",
                        "data_source": "Operational SCADA",
                        "status": "Open",
                        "detected_at": ts
                    })

            # -------------------------------------------------------------
            # 2. WIND RULES
            # -------------------------------------------------------------
            elif source == "wind":
                ws = float(metrics.get("wind_speed_ms", 0.0))
                active_p = float(record.get("generated_power", 0.0))
                gear_temp = float(metrics.get("gearbox_temp_c", 45.0))
                vibe = float(metrics.get("vibration_level_mms", 1.0))
                expected_p = float(metrics.get("expected_power_kw", 0.0))

                # Gearbox Overheating & Vibration
                if gear_temp > 78.0 or vibe > 3.8:
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "plant_id": plant_id,
                        "equipment_code": eq_code,
                        "energy_source": "wind",
                        "anomaly_type": "Gearbox Overheating & High Vibration",
                        "severity": "Critical" if gear_temp > 85.0 else "High",
                        "description": f"Main gearbox bearing temperature {gear_temp} C with mechanical vibration {vibe} mm/s",
                        "measured_value": gear_temp,
                        "expected_value": 65.0,
                        "deviation_percentage": round(((gear_temp - 65.0) / 65.0) * 100.0, 1),
                        "unit": "C",
                        "recommended_action": "Check lubrication pressure and schedule urgent mechanical drive alignment",
                        "detection_method": "Spark Multi-variable SCADA Rule",
                        "data_source": "Operational SCADA",
                        "status": "Open",
                        "detected_at": ts
                    })

                # High Wind Speed with Unusually Low Power
                if ws > 11.0 and active_p < 500.0 and expected_p > 1500.0:
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "plant_id": plant_id,
                        "equipment_code": eq_code,
                        "energy_source": "wind",
                        "anomaly_type": "Power Curve Degradation",
                        "severity": "High",
                        "description": f"Wind speed {ws} m/s generated only {active_p} kW compared to rated {expected_p} kW",
                        "measured_value": active_p,
                        "expected_value": expected_p,
                        "deviation_percentage": round(((active_p - expected_p) / expected_p) * 100.0, 1),
                        "unit": "kW",
                        "recommended_action": "Inspect blade pitch angle calibration and aerodynamic yaw control",
                        "detection_method": "Turbine Power Curve RDD Model",
                        "data_source": "Operational SCADA",
                        "status": "Open",
                        "detected_at": ts
                    })

            # -------------------------------------------------------------
            # 3. HYDROPOWER RULES
            # -------------------------------------------------------------
            elif source == "hydropower":
                p_bar = float(metrics.get("water_pressure_bar", 18.0))
                flow = float(metrics.get("water_flow_rate_m3s", 140.0))
                vib = float(metrics.get("vibration_mms", 1.0))
                gen_t = float(metrics.get("generator_temp_c", 50.0))

                if p_bar < 16.5 or vib > 3.0:
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "plant_id": plant_id,
                        "equipment_code": eq_code,
                        "energy_source": "hydropower",
                        "anomaly_type": "Penstock Pressure Drop & Turbine Vibration",
                        "severity": "High",
                        "description": f"Water intake pressure dropped to {p_bar} bar (normal 18.5 bar) with vibration {vib} mm/s",
                        "measured_value": p_bar,
                        "expected_value": 18.5,
                        "deviation_percentage": round(((p_bar - 18.5) / 18.5) * 100.0, 1),
                        "unit": "bar",
                        "recommended_action": "Check intake trash rack clogging and examine runner seal clearances",
                        "detection_method": "Hydro Differential Pressure Rule",
                        "data_source": "Plant Telemetry",
                        "status": "Open",
                        "detected_at": ts
                    })

            # -------------------------------------------------------------
            # 4. GEOTHERMAL RULES
            # -------------------------------------------------------------
            elif source == "geothermal":
                mass_flow = float(metrics.get("mass_flow_rate_th", 140.0))
                p_drop = float(metrics.get("pressure_drop_bar", 0.4))
                steam_t = float(metrics.get("steam_temp_c", 240.0))

                if mass_flow < 125.0 or p_drop > 0.65:
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "plant_id": plant_id,
                        "equipment_code": eq_code,
                        "energy_source": "geothermal",
                        "anomaly_type": "Wellhead Mass Flow Fluctuation",
                        "severity": "Medium",
                        "description": f"Well mass flow dropped to {mass_flow} t/h with pressure drop {p_drop} bar",
                        "measured_value": mass_flow,
                        "expected_value": 142.0,
                        "deviation_percentage": round(((mass_flow - 142.0) / 142.0) * 100.0, 1),
                        "unit": "t/h",
                        "recommended_action": "Inspect two-phase separator and test for calcite scale deposition in wellbore",
                        "detection_method": "Geothermal Mass Balance RDD",
                        "data_source": "Field Wellhead Telemetry",
                        "status": "Open",
                        "detected_at": ts
                    })

            # -------------------------------------------------------------
            # 5. BIOMASS RULES
            # -------------------------------------------------------------
            elif source == "biomass":
                moist = float(metrics.get("moisture_content_pct", 20.0))
                combust_eff = float(metrics.get("combustion_efficiency_pct", 85.0))
                emiss = float(metrics.get("emissions_level_mg_nm3", 40.0))
                boiler_t = float(metrics.get("boiler_temp_c", 880.0))

                if moist > 35.0 or boiler_t < 810.0 or emiss > 70.0:
                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "plant_id": plant_id,
                        "equipment_code": eq_code,
                        "energy_source": "biomass",
                        "anomaly_type": "Excessive Fuel Moisture & Combustion Instability",
                        "severity": "High" if emiss > 80.0 else "Medium",
                        "description": f"Biomass fuel moisture reached {moist}%, causing boiler temp to drop to {boiler_t} C and emissions to rise to {emiss} mg/Nm3",
                        "measured_value": moist,
                        "expected_value": 20.0,
                        "deviation_percentage": round(((moist - 20.0) / 20.0) * 100.0, 1),
                        "unit": "%",
                        "recommended_action": "Switch to dry fuel storage bunker and adjust primary combustion air blower dampers",
                        "detection_method": "Biomass Stoichiometry RDD Engine",
                        "data_source": "Plant Fuel Lab Ingestion",
                        "status": "Open",
                        "detected_at": ts
                    })

            return alerts

        # Use flatMap to produce flattened list of alerts across all records
        alerts_rdd = processed_rdd.flatMap(evaluate_record)
        
        # Deduplicate alerts by (equipment_code, anomaly_type)
        deduped_alerts = alerts_rdd.map(lambda a: ((a["plant_id"], a["equipment_code"], a["anomaly_type"]), a)) \
                                   .reduceByKey(lambda a, b: a) \
                                   .map(lambda pair: pair[1]) \
                                   .collect()

        return deduped_alerts
