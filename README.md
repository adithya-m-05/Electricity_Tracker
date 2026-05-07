# ⚡ Electricity Tracker — Smart Energy Dashboard

A real-time electricity monitoring and management dashboard designed for Indian households. Track power consumption across appliances, get AI-powered energy-saving recommendations, and manage your monthly electricity budget — all from a sleek, modern web interface.

> **Note:** This project is designed to eventually integrate with physical IoT sensors (Raspberry Pi + CT clamps) for real electricity monitoring. Currently, it ships with a **realistic IoT simulator** that models household power consumption patterns for development and demo purposes.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📊 Real-Time Dashboard** | Live power consumption updates every 3 seconds with animated counters and gauges |
| **📈 24-Hour Usage Chart** | Canvas-rendered power consumption graph showing the last 24 hours of data |
| **🏠 Appliance Control** | Toggle individual appliances ON/OFF with visual feedback and status tracking |
| **🤖 AI Recommendations** | Multi-tier energy-saving suggestions based on usage patterns and budget thresholds |
| **💰 Cost Estimation** | Real-time cost tracking with projected monthly electricity bill |
| **🎯 Budget Management** | Set monthly kWh limits with visual gauge showing utilization percentage |
| **🔋 IoT Simulator** | Realistic sensor data generator with time-of-day patterns and appliance profiles |
| **💾 Persistent Storage** | All data persists across server restarts via JSON file storage |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Browser)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Dashboard │  │  Chart   │  │  Gauge   │  │ Appliance  │  │
│  │  Stats    │  │ (Canvas) │  │  (SVG)   │  │  Controls  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       └──────────────┴─────────────┴──────────────┘         │
│                          │ HTTP REST                         │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                  Flask Backend (Python)                      │
│  ┌──────────┐  ┌────────┴────────┐  ┌───────────────────┐  │
│  │   API     │  │  Energy Engine  │  │  AI Recommender   │  │
│  │ Endpoints │  │  (kWh Tracking) │  │  (Multi-tier)     │  │
│  └────┬─────┘  └────────┬────────┘  └───────────────────┘  │
│       │                 │                                    │
│       │          ┌──────┴──────┐                            │
│       │          │  data.json  │  ← Persistent Storage      │
│       │          └─────────────┘                            │
└───────┼─────────────────────────────────────────────────────┘
        │ HTTP POST
┌───────┼─────────────────────────────────────────────────────┐
│       │        IoT Sensor Simulator                         │
│  ┌────┴─────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Sender  │  │  Appliance   │  │   Time-of-Day        │  │
│  │  Loop    │  │  Profiles    │  │   Scheduling         │  │
│  └──────────┘  └──────────────┘  └──────────────────────┘  │
│                                                             │
│  Future: Replace with Raspberry Pi + CT Clamp Sensors       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML5 / CSS3 / Vanilla JavaScript | Dashboard UI with glassmorphism design |
| **Charts** | HTML5 Canvas API | 24-hour power consumption visualization |
| **Gauges** | SVG | Animated circular budget gauge |
| **Backend** | Python 3 / Flask | REST API and energy tracking engine |
| **CORS** | Flask-CORS | Cross-origin requests from frontend |
| **Storage** | JSON file | Lightweight persistent data storage |
| **Simulator** | Python (requests) | Realistic IoT sensor data generation |

---

## 📁 Project Structure

```
Electricity Tracker/
├── backend/
│   ├── app.py                      # Flask API server & energy engine
│   ├── raspberry_pi_simulator.py   # IoT sensor data simulator
│   ├── data.json                   # Persistent data storage
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── index.html                  # Dashboard HTML structure
│   ├── styles.css                  # Premium dark-theme stylesheet
│   ├── script.js                   # Dashboard controller & charting
│   ├── thunder.jpg                 # Background asset
│   └── green.jpg                   # Background asset
└── README.md                       # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** installed
- **pip** package manager
- A modern web browser (Chrome, Firefox, Edge)

### 1. Clone / Download the Project

```bash
git clone <repo-url>
cd Electricity-Tracker
```

### 2. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Start the Backend Server

```bash
python app.py
```

The API server will start at `http://127.0.0.1:5000`.

### 4. Start the IoT Simulator *(separate terminal)*

```bash
python raspberry_pi_simulator.py
```

The simulator will begin sending realistic power consumption data to the backend every 5 seconds. In **accelerated mode** (default), 1 real second = 1 simulated minute, so a full day plays out in ~24 minutes.

### 5. Open the Dashboard

Open `frontend/index.html` in your web browser. The dashboard will automatically connect to the backend and begin displaying live data.

> **Tip:** You can also serve the frontend with any static file server:
> ```bash
> cd frontend
> python -m http.server 8080
> ```
> Then visit `http://localhost:8080`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/get_usage` | Returns comprehensive usage data, appliance states, and AI recommendations |
| `GET` | `/get_history` | Returns 24-hour hourly power history for charting |
| `GET` | `/get_stats` | Returns summary statistics (peak, averages, cost) |
| `POST` | `/set_limit` | Update monthly kWh limit and/or electricity rate |
| `POST` | `/toggle_appliance` | Turn an appliance ON or OFF |
| `POST` | `/pi_status` | Receive sensor data from IoT simulator |
| `POST` | `/reset` | Reset all energy data to defaults |

---

## 🔮 Simulator Details

The IoT simulator (`raspberry_pi_simulator.py`) models realistic Indian household electricity usage:

- **Per-Appliance Profiles:** AC (1400W), Fridge (140W with compressor cycling), Washing Machine (500W with 45-min cycles), TV (90W), Fan (65W)
- **Time-of-Day Scheduling:** AC peaks 1pm–5pm, TV peaks 7pm–10pm, Fridge runs 24/7, Fan follows temperature patterns
- **Compressor Cycling:** Refrigerator compressor runs 15 min ON → 30 min OFF (realistic duty cycle)
- **Voltage Simulation:** Indian grid voltage (220V ±10V) with peak-hour sags
- **Accelerated Mode:** Default 60× speed — a full day simulates in ~24 minutes

---

## 🔭 Future Scope

- **iOS Integration:** Native iOS app connecting to the same backend for mobile monitoring
- **Raspberry Pi Hardware:** Replace the simulator with real CT clamp sensors on a Raspberry Pi
- **Historical Analytics:** Weekly/monthly trend analysis with detailed breakdowns
- **Multi-Room Tracking:** Separate monitoring for different rooms/circuits
- **Push Notifications:** Mobile alerts when approaching budget limits
- **Cloud Deployment:** Host the backend on a cloud server for remote access

---

## 📜 License

This project is open-source and available for educational and personal use.

---

<p align="center">
  Built with ⚡ by the Electricity Tracker Team
</p>
