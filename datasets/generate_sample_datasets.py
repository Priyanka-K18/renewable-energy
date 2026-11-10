import os
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def generate_solar():
    path = BASE_DIR / "solar" / "bhadla_solar_telemetry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Plant_ID", "Inverter_ID", "Date_Time", "DC_POWER", "AC_POWER",
        "DAILY_YIELD", "TOTAL_YIELD", "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"
    ]
    rows = []
    base_time = datetime(2024, 6, 1, 0, 0, 0)
    inverters = ["INV-SOLAR-01", "INV-SOLAR-02"]
    
    total_yield = {inv: 125000.0 for inv in inverters}
    daily_yield = {inv: 0.0 for inv in inverters}

    for step in range(288): # 3 days at 15-min intervals
        curr_time = base_time + timedelta(minutes=15 * step)
        hour = curr_time.hour + curr_time.minute / 60.0
        
        # Reset daily yield at midnight
        if curr_time.hour == 0 and curr_time.minute == 0:
            for inv in inverters:
                daily_yield[inv] = 0.0

        # Solar bell curve between 6:00 and 18:30
        if 6.0 <= hour <= 18.5:
            # Solar peak at 12:15
            sun_angle = math.sin((hour - 6.0) / 12.5 * math.pi)
            base_irrad = max(0.0, sun_angle * 950.0 + random.uniform(-25.0, 25.0))
            amb_temp = 28.0 + sun_angle * 14.0 + random.uniform(-0.5, 0.5)
            mod_temp = amb_temp + (base_irrad / 800.0) * 22.0 + random.uniform(-1.0, 1.0)
        else:
            base_irrad = 0.0
            amb_temp = 24.0 + random.uniform(-0.5, 0.5)
            mod_temp = amb_temp

        for inv in inverters:
            if base_irrad > 10.0:
                # DC power calculation (2.5 MW inverter)
                dc_power = (base_irrad / 1000.0) * 2500.0 * (1.0 - 0.004 * (mod_temp - 25.0))
                # AC power with inverter conversion efficiency ~97.5%
                ac_power = dc_power * 0.975

                # Inject anomaly on INV-SOLAR-02 on Day 2 noon: Inverter tripped!
                if inv == "INV-SOLAR-02" and 32 <= step <= 36:
                    ac_power = 0.0
                    dc_power = 0.0

                energy_step_kwh = (ac_power * 0.25) # 15 min = 0.25h
                daily_yield[inv] += energy_step_kwh
                total_yield[inv] += energy_step_kwh
            else:
                dc_power = 0.0
                ac_power = 0.0

            rows.append([
                "a0000001-0000-0000-0000-000000000001",
                inv,
                curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                round(dc_power, 2),
                round(ac_power, 2),
                round(daily_yield[inv], 2),
                round(total_yield[inv], 2),
                round(amb_temp, 2),
                round(mod_temp, 2),
                round(base_irrad, 2)
            ])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {len(rows)} solar records -> {path}")

def generate_wind():
    path = BASE_DIR / "wind" / "muppandal_wind_telemetry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Wind_Farm_ID", "Turbine_ID", "Date_Time", "WIND_SPEED", "WIND_DIRECTION",
        "ROTOR_SPEED", "GENERATOR_SPEED", "ACTIVE_POWER", "REACTIVE_POWER",
        "NACELLE_TEMPERATURE", "GEARBOX_TEMPERATURE", "VIBRATION_LEVEL", "DAILY_YIELD", "TOTAL_YIELD"
    ]
    rows = []
    base_time = datetime(2024, 6, 1, 0, 0, 0)
    turbines = ["WTG-WIND-01", "WTG-WIND-02"]
    daily_yield = {t: 0.0 for t in turbines}
    total_yield = {t: 450000.0 for t in turbines}

    for step in range(288):
        curr_time = base_time + timedelta(minutes=10 * step)
        if curr_time.hour == 0 and curr_time.minute == 0:
            for t in turbines:
                daily_yield[t] = 0.0

        # Diurnal and atmospheric wind speed variation
        base_ws = 8.5 + 3.0 * math.sin(step / 20.0) + random.uniform(-1.0, 1.0)
        wind_speed = max(0.0, base_ws)
        wind_dir = (240.0 + random.uniform(-15.0, 15.0)) % 360.0

        for t in turbines:
            # Turbine Power Curve (Cut-in 3 m/s, Rated 12 m/s = 2100 kW, Cut-out 25 m/s)
            if wind_speed < 3.0 or wind_speed > 25.0:
                active_power = 0.0
                rotor_speed = 0.0
                gen_speed = 0.0
            elif wind_speed < 12.0:
                fraction = ((wind_speed - 3.0) / 9.0) ** 3
                active_power = fraction * 2100.0
                rotor_speed = 6.0 + fraction * 10.0
                gen_speed = rotor_speed * 90.0
            else:
                active_power = 2100.0 + random.uniform(-20.0, 20.0)
                rotor_speed = 16.0 + random.uniform(-0.2, 0.2)
                gen_speed = rotor_speed * 90.0

            reactive_power = active_power * 0.15 + random.uniform(-10.0, 10.0)
            nacelle_temp = 29.0 + (active_power / 2100.0) * 12.0 + random.uniform(-0.5, 0.5)
            gearbox_temp = 48.0 + (active_power / 2100.0) * 26.0 + random.uniform(-0.8, 0.8)
            vibration = 1.2 + (active_power / 2100.0) * 1.5 + random.uniform(-0.1, 0.1)

            # Inject anomaly on WTG-WIND-02: Gearbox Overheating & Vibration
            if t == "WTG-WIND-02" and 100 <= step <= 130:
                gearbox_temp += 22.0 # reaches >85 C
                vibration += 2.4     # reaches >4.5 mm/s

            energy_step = active_power * (10.0 / 60.0)
            daily_yield[t] += energy_step
            total_yield[t] += energy_step

            rows.append([
                "a0000002-0000-0000-0000-000000000002",
                t,
                curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                round(wind_speed, 2),
                round(wind_dir, 1),
                round(rotor_speed, 2),
                round(gen_speed, 1),
                round(active_power, 2),
                round(reactive_power, 2),
                round(nacelle_temp, 2),
                round(gearbox_temp, 2),
                round(vibration, 2),
                round(daily_yield[t], 2),
                round(total_yield[t], 2)
            ])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {len(rows)} wind records -> {path}")

def generate_hydro():
    path = BASE_DIR / "hydropower" / "tehri_hydro_telemetry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Plant_ID", "Turbine_ID", "Date_Time", "WATER_FLOW_RATE", "RESERVOIR_LEVEL",
        "WATER_HEAD", "TURBINE_SPEED", "GENERATOR_POWER", "WATER_PRESSURE",
        "VIBRATION_LEVEL", "GENERATOR_TEMPERATURE", "DAILY_YIELD", "TOTAL_YIELD"
    ]
    rows = []
    base_time = datetime(2024, 6, 1, 0, 0, 0)
    turbines = ["TURB-HYDRO-01", "TURB-HYDRO-02"]
    daily_yield = {t: 0.0 for t in turbines}
    total_yield = {t: 2800000.0 for t in turbines}

    for step in range(288):
        curr_time = base_time + timedelta(minutes=15 * step)
        if curr_time.hour == 0 and curr_time.minute == 0:
            for t in turbines:
                daily_yield[t] = 0.0

        # Reservoir level ~820m, Head ~188m
        reservoir_level = 822.5 - (step * 0.005) + random.uniform(-0.02, 0.02)
        water_head = 188.0 + random.uniform(-0.5, 0.5)

        for t in turbines:
            # Water flow 145 m3/s per 250 MW turbine
            flow_rate = 145.0 + random.uniform(-3.0, 3.0)
            # P = rho * g * Q * H * eta (kW = 1000 * 9.81 * Q * H * 0.92 / 1000)
            power_mw = (9.81 * flow_rate * water_head * 0.92) / 1000.0
            power_kw = power_mw * 1000.0
            turbine_speed = 250.0 + random.uniform(-0.5, 0.5)
            water_pressure = 18.4 + random.uniform(-0.2, 0.2)
            vibration = 1.1 + random.uniform(-0.05, 0.05)
            gen_temp = 54.0 + random.uniform(-0.5, 0.5)

            # Anomaly injection on TURB-HYDRO-01: Penstock Pressure Drop
            if t == "TURB-HYDRO-01" and 80 <= step <= 95:
                water_pressure -= 2.2
                flow_rate -= 18.0
                power_kw *= 0.82

            energy_step = power_kw * 0.25
            daily_yield[t] += energy_step
            total_yield[t] += energy_step

            rows.append([
                "a0000003-0000-0000-0000-000000000003",
                t,
                curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                round(flow_rate, 2),
                round(reservoir_level, 2),
                round(water_head, 2),
                round(turbine_speed, 1),
                round(power_kw, 2),
                round(water_pressure, 2),
                round(vibration, 2),
                round(gen_temp, 2),
                round(daily_yield[t], 2),
                round(total_yield[t], 2)
            ])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {len(rows)} hydro records -> {path}")

def generate_geothermal():
    path = BASE_DIR / "geothermal" / "olkaria_geothermal_telemetry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Plant_ID", "Well_ID", "Date_Time", "STEAM_TEMPERATURE", "STEAM_PRESSURE",
        "BRINE_TEMPERATURE", "WELL_DEPTH", "MASS_FLOW_RATE", "TURBINE_SPEED",
        "GENERATOR_POWER", "COOLING_TEMPERATURE", "PRESSURE_DROP", "DAILY_YIELD", "TOTAL_YIELD"
    ]
    rows = []
    base_time = datetime(2024, 6, 1, 0, 0, 0)
    wells = ["WELL-GEO-01", "WELL-GEO-02"]
    daily_yield = {w: 0.0 for w in wells}
    total_yield = {w: 890000.0 for w in wells}

    for step in range(288):
        curr_time = base_time + timedelta(minutes=15 * step)
        if curr_time.hour == 0 and curr_time.minute == 0:
            for w in wells:
                daily_yield[w] = 0.0

        for w in wells:
            steam_temp = 245.0 + random.uniform(-1.5, 1.5)
            steam_pressure = 8.5 + random.uniform(-0.15, 0.15)
            brine_temp = 168.0 + random.uniform(-1.0, 1.0)
            well_depth = 2800.0
            mass_flow = 142.0 + random.uniform(-2.0, 2.0) # t/h
            turb_speed = 3000.0 + random.uniform(-1.0, 1.0)
            cooling_temp = 32.0 + random.uniform(-0.8, 0.8)
            pressure_drop = 0.45 + random.uniform(-0.02, 0.02)
            gen_power_kw = mass_flow * 350.0 + random.uniform(-50.0, 50.0)

            # Anomaly on WELL-GEO-01: Mass flow rate reduction
            if w == "WELL-GEO-01" and 150 <= step <= 170:
                mass_flow -= 28.0
                gen_power_kw = mass_flow * 350.0
                pressure_drop += 0.35

            energy_step = gen_power_kw * 0.25
            daily_yield[w] += energy_step
            total_yield[w] += energy_step

            rows.append([
                "a0000004-0000-0000-0000-000000000004",
                w,
                curr_time.strftime("%Y-%m-%d %H:%M:%S"),
                round(steam_temp, 2),
                round(steam_pressure, 2),
                round(brine_temp, 2),
                round(well_depth, 1),
                round(mass_flow, 2),
                round(turb_speed, 1),
                round(gen_power_kw, 2),
                round(cooling_temp, 2),
                round(pressure_drop, 2),
                round(daily_yield[w], 2),
                round(total_yield[w], 2)
            ])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {len(rows)} geothermal records -> {path}")

def generate_biomass():
    path = BASE_DIR / "biomass" / "ironbridge_biomass_telemetry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Plant_ID", "Date_Time", "BIOMASS_TYPE", "FUEL_INPUT_KG", "MOISTURE_CONTENT",
        "CALORIFIC_VALUE", "BOILER_TEMPERATURE", "STEAM_PRESSURE", "COMBUSTION_EFFICIENCY",
        "GENERATOR_POWER", "EMISSIONS_LEVEL", "ASH_CONTENT", "DAILY_YIELD", "TOTAL_YIELD"
    ]
    rows = []
    base_time = datetime(2024, 6, 1, 0, 0, 0)
    daily_yield = 0.0
    total_yield = 1450000.0

    for step in range(288):
        curr_time = base_time + timedelta(minutes=15 * step)
        if curr_time.hour == 0 and curr_time.minute == 0:
            daily_yield = 0.0

        fuel_kg = 28000.0 + random.uniform(-500.0, 500.0) # per 15 min
        moisture = 18.5 + random.uniform(-1.0, 1.0)
        calorific_mj = 17.8 - (moisture - 18.5) * 0.15 # MJ/kg
        boiler_temp = 890.0 + random.uniform(-10.0, 10.0)
        steam_pressure = 135.0 + random.uniform(-2.0, 2.0)
        combustion_eff = 87.5 + random.uniform(-0.8, 0.8)
        emissions = 42.0 + random.uniform(-3.0, 3.0) # mg/Nm3
        ash_pct = 4.2 + random.uniform(-0.2, 0.2)

        # Thermal energy input in MJ: fuel_kg * calorific_mj
        # Electrical conversion efficiency ~34%
        power_kw = ((fuel_kg * calorific_mj * (combustion_eff / 100.0) * 0.35) / 900.0) * 1000.0

        # Anomaly at step 180 to 205: high moisture and drop in combustion efficiency
        if 180 <= step <= 205:
            moisture = 41.5 + random.uniform(-1.0, 1.0)
            calorific_mj = 13.2
            combustion_eff = 72.0
            boiler_temp = 790.0
            emissions = 85.0
            power_kw *= 0.75

        energy_step = power_kw * 0.25
        daily_yield += energy_step
        total_yield += energy_step

        rows.append([
            "a0000005-0000-0000-0000-000000000005",
            curr_time.strftime("%Y-%m-%d %H:%M:%S"),
            "Wood Pellets & Agro Residues",
            round(fuel_kg, 1),
            round(moisture, 2),
            round(calorific_mj, 2),
            round(boiler_temp, 1),
            round(steam_pressure, 2),
            round(combustion_eff, 2),
            round(power_kw, 2),
            round(emissions, 2),
            round(ash_pct, 2),
            round(daily_yield, 2),
            round(total_yield, 2)
        ])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Generated {len(rows)} biomass records -> {path}")

if __name__ == "__main__":
    generate_solar()
    generate_wind()
    generate_hydro()
    generate_geothermal()
    generate_biomass()
    print("All 5 renewable source operational sample datasets generated successfully!")
