from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import threading
import time

app = Flask(__name__)
CORS(app)

# ─── Data File Path ───────────────────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")

# ─── Default State ────────────────────────────────────────────────────────────
DEFAULT_DATA = {
    "monthly_limit": 500,
    "electricity_rate": 8.0,
    "current_month_kwh": 0.0,
    "today_kwh": 0.0,
    "current_power_watts": 0.0,
    "last_update_time": None,
    "peak_power_watts": 0.0,
    "appliances": [
        {"name": "Air Conditioner", "wattage": 1500, "voltage": 220, "status": "OFF", "icon": "ac"},
        {"name": "Refrigerator", "wattage": 150, "voltage": 230, "status": "OFF", "icon": "fridge"},
        {"name": "Washing Machine", "wattage": 500, "voltage": 220, "status": "OFF", "icon": "washer"},
        {"name": "Television", "wattage": 100, "voltage": 220, "status": "OFF", "icon": "tv"},
        {"name": "Fan", "wattage": 75, "voltage": 220, "status": "OFF", "icon": "fan"},
    ],
    "hourly_history": [],
    "daily_totals": [],
}

# ─── In-Memory State ─────────────────────────────────────────────────────────
energy_data = {}
data_lock = threading.Lock()


def load_data():
    """Load persisted data from JSON file, falling back to defaults."""
    global energy_data
    try:
        if os.path.exists(DATA_FILE) and os.path.getsize(DATA_FILE) > 10:
            with open(DATA_FILE, "r") as f:
                energy_data = json.load(f)
            # Ensure all keys exist (upgrade path)
            for key, value in DEFAULT_DATA.items():
                if key not in energy_data:
                    energy_data[key] = value if not isinstance(value, list) else list(value)
            # Ensure all appliances have required fields
            for appliance in energy_data.get("appliances", []):
                if "icon" not in appliance:
                    appliance["icon"] = appliance["name"].lower().replace(" ", "_")
        else:
            energy_data = json.loads(json.dumps(DEFAULT_DATA))
    except (json.JSONDecodeError, IOError):
        energy_data = json.loads(json.dumps(DEFAULT_DATA))


def save_data():
    """Persist current state to JSON file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(energy_data, f, indent=2, default=str)
    except IOError as e:
        print(f"⚠️ Could not save data: {e}")


def get_remaining_budget():
    """Calculate remaining kWh budget for the month."""
    return max(0, energy_data["monthly_limit"] - energy_data["current_month_kwh"])


def get_budget_percentage():
    """How much of the monthly budget has been used (0-100)."""
    if energy_data["monthly_limit"] <= 0:
        return 100
    return min(100, round((energy_data["current_month_kwh"] / energy_data["monthly_limit"]) * 100, 1))


def get_estimated_cost():
    """Calculate estimated monthly electricity cost."""
    return round(energy_data["current_month_kwh"] * energy_data["electricity_rate"], 2)


def get_projected_monthly():
    """Project total monthly usage based on current rate."""
    now = datetime.now()
    day_of_month = now.day
    hour_of_day = now.hour + (now.minute / 60)
    hours_elapsed = ((day_of_month - 1) * 24) + hour_of_day
    if hours_elapsed <= 0:
        return energy_data["current_month_kwh"]
    # Days in current month (approximate)
    days_in_month = 30
    total_hours_in_month = days_in_month * 24
    rate_per_hour = energy_data["current_month_kwh"] / hours_elapsed
    return round(rate_per_hour * total_hours_in_month, 2)


def calculate_remaining_hours(appliance):
    """How many more hours an appliance can run within remaining budget."""
    remaining = get_remaining_budget()
    wattage_kw = appliance["wattage"] / 1000
    if wattage_kw <= 0:
        return 0
    return round(remaining / wattage_kw, 1)


def ai_recommendation():
    """Generate intelligent recommendations based on usage patterns."""
    budget_pct = get_budget_percentage()
    remaining = get_remaining_budget()
    projected = get_projected_monthly()
    on_appliances = [a for a in energy_data["appliances"] if a["status"] == "ON"]
    recommendations = []

    # Critical: over 90% of budget
    if budget_pct >= 90:
        recommendations.append({
            "severity": "critical",
            "message": "⚠️ Critical: You've used 90% of your monthly budget! Consider turning off non-essential appliances immediately."
        })
        # Suggest turning off the highest consumer
        if on_appliances:
            top = max(on_appliances, key=lambda a: a["wattage"])
            savings = round(top["wattage"] / 1000 * 24, 1)
            recommendations.append({
                "severity": "critical",
                "message": f"💡 Turn off {top['name']} ({top['wattage']}W) to save ~{savings} kWh/day."
            })

    # Warning: over 70% of budget
    elif budget_pct >= 70:
        recommendations.append({
            "severity": "warning",
            "message": f"⚡ Warning: {budget_pct}% of monthly budget used. {remaining:.1f} kWh remaining."
        })
        if projected > energy_data["monthly_limit"]:
            overshoot = round(projected - energy_data["monthly_limit"], 1)
            recommendations.append({
                "severity": "warning",
                "message": f"📈 At current rate, you'll exceed your limit by ~{overshoot} kWh this month."
            })

    # Advisory: over 50%
    elif budget_pct >= 50:
        recommendations.append({
            "severity": "info",
            "message": f"📊 You've used {budget_pct}% of your monthly budget. Usage is moderate."
        })

    # All good
    else:
        recommendations.append({
            "severity": "good",
            "message": "✅ Energy usage is optimal. You're well within your monthly budget."
        })

    # Time-based tips
    hour = datetime.now().hour
    ac_on = any(a["name"] == "Air Conditioner" and a["status"] == "ON" for a in energy_data["appliances"])
    if ac_on and (0 <= hour <= 6):
        recommendations.append({
            "severity": "info",
            "message": "🌙 Tip: It's nighttime — consider switching AC to fan mode to save energy."
        })

    return recommendations


def record_hourly_snapshot():
    """Record a snapshot of current power for the 24-hour chart."""
    now = datetime.now()
    snapshot = {
        "time": now.strftime("%H:%M"),
        "timestamp": now.isoformat(),
        "power_watts": energy_data["current_power_watts"],
    }
    energy_data["hourly_history"].append(snapshot)
    # Keep only last 288 entries (~24 hours at 5-min intervals)
    if len(energy_data["hourly_history"]) > 288:
        energy_data["hourly_history"] = energy_data["hourly_history"][-288:]


def record_daily_total():
    """Record today's usage for daily tracking."""
    today = datetime.now().strftime("%Y-%m-%d")
    # Check if today's entry already exists
    for entry in energy_data["daily_totals"]:
        if entry["date"] == today:
            entry["kwh"] = energy_data["today_kwh"]
            return
    energy_data["daily_totals"].append({
        "date": today,
        "kwh": energy_data["today_kwh"],
    })
    # Keep last 31 days
    if len(energy_data["daily_totals"]) > 31:
        energy_data["daily_totals"] = energy_data["daily_totals"][-31:]


def accumulate_energy(power_watts, seconds_elapsed):
    """Convert instantaneous power + time into kWh and accumulate."""
    if seconds_elapsed <= 0 or power_watts <= 0:
        return 0
    kwh = (power_watts * seconds_elapsed) / 3_600_000  # W·s → kWh
    energy_data["current_month_kwh"] = round(energy_data["current_month_kwh"] + kwh, 4)
    energy_data["today_kwh"] = round(energy_data["today_kwh"] + kwh, 4)
    if power_watts > energy_data["peak_power_watts"]:
        energy_data["peak_power_watts"] = power_watts
    return kwh


# ─── Background Snapshot Thread ──────────────────────────────────────────────
def snapshot_loop():
    """Runs in background to periodically record snapshots and save data."""
    while True:
        time.sleep(30)  # Every 30 seconds
        with data_lock:
            record_hourly_snapshot()
            record_daily_total()
            save_data()


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route("/get_usage", methods=["GET"])
def get_usage():
    """Returns comprehensive electricity usage data."""
    with data_lock:
        remaining = get_remaining_budget()
        budget_pct = get_budget_percentage()
        estimated_cost = get_estimated_cost()
        projected = get_projected_monthly()
        recs = ai_recommendation()

        # Add remaining hours to each appliance
        appliances_with_info = []
        for a in energy_data["appliances"]:
            appliance_info = {**a}
            appliance_info["remaining_hours"] = calculate_remaining_hours(a)
            appliance_info["daily_kwh"] = round(a["wattage"] / 1000 * 24, 2)
            appliances_with_info.append(appliance_info)

        return jsonify({
            "monthly_limit": energy_data["monthly_limit"],
            "electricity_rate": energy_data["electricity_rate"],
            "current_month_kwh": round(energy_data["current_month_kwh"], 2),
            "today_kwh": round(energy_data["today_kwh"], 2),
            "current_power_watts": round(energy_data["current_power_watts"], 1),
            "peak_power_watts": round(energy_data["peak_power_watts"], 1),
            "remaining_budget": round(remaining, 2),
            "budget_percentage": budget_pct,
            "estimated_cost": estimated_cost,
            "projected_monthly": projected,
            "projected_cost": round(projected * energy_data["electricity_rate"], 2),
            "appliances": appliances_with_info,
            "recommendations": recs,
        })


@app.route("/get_history", methods=["GET"])
def get_history():
    """Returns hourly usage history for charting."""
    with data_lock:
        return jsonify({
            "hourly_history": energy_data.get("hourly_history", []),
            "daily_totals": energy_data.get("daily_totals", []),
        })


@app.route("/get_stats", methods=["GET"])
def get_stats():
    """Returns summary statistics."""
    with data_lock:
        on_appliances = [a for a in energy_data["appliances"] if a["status"] == "ON"]
        total_active_wattage = sum(a["wattage"] for a in on_appliances)

        return jsonify({
            "total_appliances": len(energy_data["appliances"]),
            "active_appliances": len(on_appliances),
            "total_active_wattage": total_active_wattage,
            "peak_power_watts": energy_data["peak_power_watts"],
            "current_month_kwh": round(energy_data["current_month_kwh"], 2),
            "today_kwh": round(energy_data["today_kwh"], 2),
            "estimated_cost": get_estimated_cost(),
            "budget_percentage": get_budget_percentage(),
        })


@app.route("/set_limit", methods=["POST"])
def set_limit():
    """Updates the monthly electricity limit and/or rate."""
    data = request.json
    with data_lock:
        new_limit = data.get("monthly_limit")
        new_rate = data.get("electricity_rate")

        if new_limit is not None and new_limit > 0:
            energy_data["monthly_limit"] = float(new_limit)
        if new_rate is not None and new_rate > 0:
            energy_data["electricity_rate"] = float(new_rate)

        save_data()
        return jsonify({"message": "Settings updated successfully!", "monthly_limit": energy_data["monthly_limit"], "electricity_rate": energy_data["electricity_rate"]}), 200


@app.route("/toggle_appliance", methods=["POST"])
def toggle_appliance():
    """Turns an appliance ON/OFF and updates usage tracking."""
    data = request.json
    appliance_name = data.get("appliance")
    status = data.get("status")

    with data_lock:
        found = False
        for appliance in energy_data["appliances"]:
            if appliance["name"] == appliance_name:
                appliance["status"] = status
                found = True
                break

        if not found:
            return jsonify({"error": f"Appliance '{appliance_name}' not found"}), 404

        # Recalculate current total power draw
        total_watts = sum(a["wattage"] for a in energy_data["appliances"] if a["status"] == "ON")
        energy_data["current_power_watts"] = total_watts

        save_data()
        return jsonify({
            "message": f"{appliance_name} turned {status}",
            "current_power_watts": total_watts,
        })


@app.route("/pi_status", methods=["POST"])
def pi_status():
    """Receives sensor data from the IoT simulator and accumulates energy usage."""
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    with data_lock:
        power_watts = data.get("power_watts", 0)
        seconds_elapsed = data.get("seconds_elapsed", 5)
        voltage = data.get("voltage", 220)
        current_amps = data.get("current_amps", 0)

        # Update current instantaneous readings
        energy_data["current_power_watts"] = round(power_watts, 1)

        # Accumulate energy
        kwh_added = accumulate_energy(power_watts, seconds_elapsed)

        # Update appliance statuses from simulator
        appliance_statuses = data.get("appliance_statuses", {})
        for appliance in energy_data["appliances"]:
            if appliance["name"] in appliance_statuses:
                appliance["status"] = appliance_statuses[appliance["name"]]

        # Record snapshot
        record_hourly_snapshot()
        record_daily_total()

        energy_data["last_update_time"] = datetime.now().isoformat()
        save_data()

        return jsonify({
            "message": "Sensor data received",
            "kwh_added": round(kwh_added, 6),
            "total_month_kwh": round(energy_data["current_month_kwh"], 4),
            "recommendations": ai_recommendation(),
        })


@app.route("/reset", methods=["POST"])
def reset_data():
    """Reset all energy data (for demo/testing)."""
    global energy_data
    with data_lock:
        energy_data = json.loads(json.dumps(DEFAULT_DATA))
        save_data()
    return jsonify({"message": "All data has been reset."})


# ─── Startup ──────────────────────────────────────────────────────────────────

load_data()

# Start background snapshot thread
snapshot_thread = threading.Thread(target=snapshot_loop, daemon=True)
snapshot_thread.start()

if __name__ == "__main__":
    print("[*] Electricity Tracker Backend Starting...")
    print(f"[>] Data file: {DATA_FILE}")
    print(f"[>] Monthly limit: {energy_data['monthly_limit']} kWh")
    print(f"[>] Rate: Rs.{energy_data['electricity_rate']}/kWh")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
