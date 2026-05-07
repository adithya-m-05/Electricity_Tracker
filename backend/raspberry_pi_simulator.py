"""
Electricity Tracker — IoT Sensor Simulator
============================================
Simulates a Raspberry Pi / IoT device reading power consumption from
household appliances. Models realistic patterns including:

- Per-appliance power profiles with realistic wattage ranges
- Time-of-day usage patterns (AC peaks in afternoon, TV in evening, etc.)
- Refrigerator compressor ON/OFF cycling
- Indian grid voltage fluctuations (220V ± 10V)
- Random noise for realism
- Accelerated time mode for demos (1 second = 1 minute)
"""

import requests
import random
import time
import math
from datetime import datetime, timedelta

# ─── Configuration ────────────────────────────────────────────────────────────
SERVER_URL = "http://127.0.0.1:5000/pi_status"
SEND_INTERVAL = 5          # Seconds between data transmissions
ACCELERATED = True         # If True, time runs at 60x speed for demo
TIME_MULTIPLIER = 60       # 1 real second = 60 simulated seconds

# ─── Appliance Power Profiles ────────────────────────────────────────────────
# Each appliance has a base wattage, variation range, and a schedule
# defining probability of being ON during each hour block.

APPLIANCE_PROFILES = {
    "Air Conditioner": {
        "base_watts": 1400,
        "variation": 200,       # ±200W random variation
        "schedule": {
            # hour_range: probability of being ON
            (0, 5): 0.3,       # Nighttime — sometimes on
            (6, 8): 0.2,       # Early morning — usually off
            (9, 12): 0.5,      # Late morning — picking up
            (13, 17): 0.85,    # Afternoon peak — almost always on
            (18, 21): 0.6,     # Evening — often on
            (22, 23): 0.4,     # Late night — winding down
        },
    },
    "Refrigerator": {
        "base_watts": 140,
        "variation": 20,
        "always_on": True,      # Fridge runs 24/7
        "compressor_cycle": {
            "on_minutes": 15,   # Compressor runs for 15 minutes
            "off_minutes": 30,  # Then off for 30 minutes
        },
    },
    "Washing Machine": {
        "base_watts": 500,
        "variation": 100,
        "schedule": {
            (0, 6): 0.0,       # Never at night
            (7, 9): 0.4,       # Morning wash
            (10, 16): 0.1,     # Rare during day
            (17, 19): 0.3,     # Evening wash
            (20, 23): 0.05,    # Rare at night
        },
        "run_duration_minutes": 45,  # A wash cycle lasts ~45 minutes
    },
    "Television": {
        "base_watts": 90,
        "variation": 30,
        "schedule": {
            (0, 5): 0.05,
            (6, 8): 0.2,       # Morning news
            (9, 16): 0.1,      # Usually off during day
            (17, 18): 0.3,     # Starting to watch
            (19, 22): 0.8,     # Prime time!
            (23, 23): 0.3,     # Late night
        },
    },
    "Fan": {
        "base_watts": 65,
        "variation": 15,
        "schedule": {
            (0, 5): 0.4,       # Sleeping with fan on
            (6, 8): 0.3,
            (9, 12): 0.5,
            (13, 17): 0.7,     # Hot afternoon
            (18, 21): 0.5,
            (22, 23): 0.5,
        },
    },
}


# ─── Simulator State ─────────────────────────────────────────────────────────
class SimulatorState:
    def __init__(self):
        self.simulated_time = datetime.now()
        self.appliance_states = {name: False for name in APPLIANCE_PROFILES}
        # Fridge always starts ON
        self.appliance_states["Refrigerator"] = True
        self.fridge_compressor_on = True
        self.fridge_cycle_timer = 0  # minutes into current cycle
        self.washer_run_timer = 0    # minutes left in wash cycle
        self.tick_count = 0

    def get_simulated_hour(self):
        return self.simulated_time.hour

    def advance_time(self, real_seconds):
        if ACCELERATED:
            simulated_seconds = real_seconds * TIME_MULTIPLIER
        else:
            simulated_seconds = real_seconds
        self.simulated_time += timedelta(seconds=simulated_seconds)
        return simulated_seconds

    def get_schedule_probability(self, profile, hour):
        """Get the ON-probability for an appliance at the given hour."""
        schedule = profile.get("schedule", {})
        for (start_h, end_h), prob in schedule.items():
            if start_h <= hour <= end_h:
                return prob
        return 0.1  # Default low probability

    def update_appliance_states(self):
        """Decide which appliances are ON based on time-of-day schedules."""
        hour = self.get_simulated_hour()
        simulated_minutes = self.simulated_time.minute

        for name, profile in APPLIANCE_PROFILES.items():
            # ── Refrigerator: compressor cycling ──
            if name == "Refrigerator":
                cycle = profile["compressor_cycle"]
                total_cycle = cycle["on_minutes"] + cycle["off_minutes"]
                cycle_position = (self.tick_count * (SEND_INTERVAL * TIME_MULTIPLIER / 60 if ACCELERATED else SEND_INTERVAL / 60)) % total_cycle
                self.fridge_compressor_on = cycle_position < cycle["on_minutes"]
                self.appliance_states[name] = self.fridge_compressor_on
                continue

            # ── Washing Machine: runs for fixed duration ──
            if name == "Washing Machine":
                if self.washer_run_timer > 0:
                    elapsed_min = (SEND_INTERVAL * TIME_MULTIPLIER / 60) if ACCELERATED else (SEND_INTERVAL / 60)
                    self.washer_run_timer -= elapsed_min
                    self.appliance_states[name] = True
                    continue
                else:
                    self.appliance_states[name] = False
                    # Check if a new wash cycle should start
                    prob = self.get_schedule_probability(profile, hour)
                    # Roll dice less frequently (only every ~15 min simulated)
                    if self.tick_count % 3 == 0 and random.random() < prob * 0.1:
                        self.washer_run_timer = profile.get("run_duration_minutes", 45)
                        self.appliance_states[name] = True
                    continue

            # ── Other appliances: probabilistic ON/OFF ──
            prob = self.get_schedule_probability(profile, hour)
            # Don't toggle every tick — add inertia (only toggle ~20% of ticks)
            if self.tick_count % 5 == 0:
                self.appliance_states[name] = random.random() < prob

    def get_voltage(self):
        """Simulate Indian grid voltage with time-of-day sag."""
        hour = self.get_simulated_hour()
        base = 220
        # Voltage dips during peak hours (6-9pm)
        if 18 <= hour <= 21:
            base = 212
        elif 13 <= hour <= 17:
            base = 216
        # Add random fluctuation
        noise = random.gauss(0, 3)
        return round(base + noise, 1)

    def get_appliance_power(self, name):
        """Get current power draw for an appliance (0 if OFF)."""
        if not self.appliance_states.get(name, False):
            return 0
        profile = APPLIANCE_PROFILES[name]
        base = profile["base_watts"]
        var = profile["variation"]
        # Sinusoidal variation + noise for realism
        t = self.tick_count * 0.1
        variation = math.sin(t + hash(name) % 10) * var * 0.5
        noise = random.gauss(0, var * 0.2)
        return max(0, base + variation + noise)

    def generate_reading(self):
        """Generate a complete sensor reading."""
        self.update_appliance_states()

        total_watts = 0
        appliance_power = {}
        for name in APPLIANCE_PROFILES:
            power = self.get_appliance_power(name)
            appliance_power[name] = round(power, 1)
            total_watts += power

        voltage = self.get_voltage()
        current_amps = round(total_watts / voltage, 2) if voltage > 0 else 0

        statuses = {}
        for name, is_on in self.appliance_states.items():
            statuses[name] = "ON" if is_on else "OFF"

        return {
            "power_watts": round(total_watts, 1),
            "voltage": voltage,
            "current_amps": current_amps,
            "seconds_elapsed": SEND_INTERVAL * TIME_MULTIPLIER if ACCELERATED else SEND_INTERVAL,
            "simulated_time": self.simulated_time.isoformat(),
            "appliance_power": appliance_power,
            "appliance_statuses": statuses,
        }


# ─── Console Display ─────────────────────────────────────────────────────────

def print_reading(state, reading):
    """Pretty-print the current sensor reading to console."""
    sim_time = state.simulated_time.strftime("%Y-%m-%d %H:%M")
    print(f"\n{'-' * 60}")
    print(f"  [T] Simulated Time: {sim_time}")
    print(f"  [P] Total Power:    {reading['power_watts']:>8.1f} W")
    print(f"  [V] Voltage:        {reading['voltage']:>8.1f} V")
    print(f"  [A] Current:        {reading['current_amps']:>8.2f} A")
    print(f"{'-' * 60}")
    for name, power in reading["appliance_power"].items():
        status = "[ON] " if state.appliance_states.get(name) else "[OFF]"
        bar_len = int(power / 50) if power > 0 else 0
        bar = "#" * min(bar_len, 30)
        print(f"  {status}  {name:<20s}  {power:>7.1f} W  {bar}")
    print(f"{'-' * 60}")


# ─── Main Loop ───────────────────────────────────────────────────────────────

def run_simulator():
    state = SimulatorState()

    print("=" * 60)
    print("  [*] Electricity Tracker - IoT Sensor Simulator")
    print(f"  [>] Target: {SERVER_URL}")
    print(f"  [>] Mode: {'ACCELERATED (1s = 1min)' if ACCELERATED else 'REAL-TIME'}")
    print(f"  [>] Interval: {SEND_INTERVAL}s")
    print("=" * 60)

    while True:
        state.tick_count += 1
        sim_seconds = state.advance_time(SEND_INTERVAL)

        reading = state.generate_reading()
        print_reading(state, reading)

        try:
            response = requests.post(SERVER_URL, json=reading, timeout=5)
            if response.status_code == 200:
                resp_data = response.json()
                kwh = resp_data.get("kwh_added", 0)
                total = resp_data.get("total_month_kwh", 0)
                print(f"  [>] Sent! +{kwh:.4f} kWh  |  Month total: {total:.2f} kWh")

                # Print any recommendations from server
                recs = resp_data.get("recommendations", [])
                for rec in recs:
                    sev = rec.get("severity", "info")
                    msg = rec.get("message", "")
                    if sev in ("critical", "warning"):
                        print(f"  [!] {msg}")
            else:
                print(f"  [WARN] Server returned {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("  [ERR] Cannot connect to backend. Is app.py running?")
        except requests.exceptions.Timeout:
            print("  [TIMEOUT] Request timed out")
        except Exception as e:
            print(f"  [ERR] Error: {e}")

        time.sleep(SEND_INTERVAL)


if __name__ == "__main__":
    run_simulator()
