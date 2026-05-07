/* ─── Electricity Tracker — Dashboard Controller ───────────────────────── */

const API = "http://127.0.0.1:5000";
const POLL_INTERVAL = 3000; // ms

// ─── Appliance Icons ──────────────────────────────────────────────────────
const ICONS = {
  "Air Conditioner": "❄️",
  "Refrigerator": "🧊",
  "Washing Machine": "🫧",
  "Television": "📺",
  "Fan": "🌀",
};

// ─── State ────────────────────────────────────────────────────────────────
let isConnected = false;
let previousValues = {};
let chartData = [];
let animFrameId = null;

// ─── Animated Number Counter ──────────────────────────────────────────────
function animateValue(element, newValue, decimals = 0, duration = 600) {
  const key = element.id || element.textContent;
  const start = previousValues[key] || 0;
  const end = parseFloat(newValue) || 0;
  previousValues[key] = end;

  if (Math.abs(start - end) < 0.01) {
    element.textContent = end.toFixed(decimals);
    return;
  }

  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = start + (end - start) * eased;
    element.textContent = current.toFixed(decimals);
    if (progress < 1) requestAnimationFrame(update);
  }

  requestAnimationFrame(update);
}

// ─── Toast Notification ──────────────────────────────────────────────────
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "toastOut 0.3s ease-out forwards";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ─── Connection Status ───────────────────────────────────────────────────
function setConnectionStatus(connected) {
  isConnected = connected;
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  if (connected) {
    dot.className = "status-dot";
    text.textContent = "Connected";
  } else {
    dot.className = "status-dot offline";
    text.textContent = "Offline";
  }
}

// ─── Live Clock ──────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
  document.getElementById("live-clock").textContent = time;
}
setInterval(updateClock, 1000);
updateClock();

// ─── Gauge Update ────────────────────────────────────────────────────────
function updateGauge(percentage) {
  const fill = document.getElementById("gauge-fill");
  const circumference = 2 * Math.PI * 52; // r=52
  const offset = circumference - (percentage / 100) * circumference;
  fill.style.strokeDashoffset = offset;

  // Color based on percentage
  let color;
  if (percentage >= 90) color = "#ef4444";
  else if (percentage >= 70) color = "#f59e0b";
  else if (percentage >= 50) color = "#3b82f6";
  else color = "#10b981";

  fill.style.stroke = color;

  document.getElementById("gauge-pct").textContent = `${Math.round(percentage)}%`;
  document.getElementById("gauge-pct").style.color = color;
  document.getElementById("gauge-badge").textContent = `${Math.round(percentage)}%`;
}

// ─── Chart Drawing ───────────────────────────────────────────────────────
function drawChart(history) {
  const canvas = document.getElementById("power-chart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.parentElement.getBoundingClientRect();

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  canvas.style.width = rect.width + "px";
  canvas.style.height = rect.height + "px";
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;
  const padding = { top: 20, right: 20, bottom: 35, left: 55 };
  const chartW = w - padding.left - padding.right;
  const chartH = h - padding.top - padding.bottom;

  // Clear
  ctx.clearRect(0, 0, w, h);

  if (!history || history.length < 2) {
    ctx.fillStyle = "#484f58";
    ctx.font = "13px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("Waiting for data from the simulator...", w / 2, h / 2);
    ctx.fillText("Start raspberry_pi_simulator.py to see live data", w / 2, h / 2 + 22);
    return;
  }

  const values = history.map((d) => d.power_watts);
  const maxVal = Math.max(...values, 100);
  const minVal = 0;
  const range = maxVal - minVal || 1;

  // Grid lines
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  ctx.lineWidth = 1;
  const gridLines = 5;
  for (let i = 0; i <= gridLines; i++) {
    const y = padding.top + (chartH / gridLines) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(w - padding.right, y);
    ctx.stroke();

    // Y-axis labels
    const val = maxVal - (range / gridLines) * i;
    ctx.fillStyle = "#484f58";
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(`${Math.round(val)}W`, padding.left - 8, y + 4);
  }

  // X-axis labels
  ctx.textAlign = "center";
  const labelInterval = Math.max(1, Math.floor(history.length / 8));
  for (let i = 0; i < history.length; i += labelInterval) {
    const x = padding.left + (i / (history.length - 1)) * chartW;
    ctx.fillStyle = "#484f58";
    ctx.font = "10px Inter, sans-serif";
    ctx.fillText(history[i].time, x, h - padding.bottom + 18);
  }

  // Build path
  const points = values.map((v, i) => ({
    x: padding.left + (i / (values.length - 1)) * chartW,
    y: padding.top + chartH - ((v - minVal) / range) * chartH,
  }));

  // Gradient fill
  const gradient = ctx.createLinearGradient(0, padding.top, 0, h - padding.bottom);
  gradient.addColorStop(0, "rgba(59, 130, 246, 0.25)");
  gradient.addColorStop(1, "rgba(59, 130, 246, 0.0)");

  ctx.beginPath();
  ctx.moveTo(points[0].x, h - padding.bottom);
  ctx.lineTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    // Smooth curve using quadratic bezier
    const cx = (points[i - 1].x + points[i].x) / 2;
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, cx, (points[i - 1].y + points[i].y) / 2);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  ctx.lineTo(points[points.length - 1].x, h - padding.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    const cx = (points[i - 1].x + points[i].x) / 2;
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, cx, (points[i - 1].y + points[i].y) / 2);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  ctx.strokeStyle = "#3b82f6";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Last point glow
  if (points.length > 0) {
    const last = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#3b82f6";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(last.x, last.y, 8, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(59, 130, 246, 0.3)";
    ctx.fill();
  }
}

// ─── Appliance Cards ─────────────────────────────────────────────────────
function renderAppliances(appliances) {
  const grid = document.getElementById("appliance-grid");
  const activeCount = appliances.filter((a) => a.status === "ON").length;
  document.getElementById("appliance-count").textContent = `${activeCount} active`;

  // Only rebuild if count changed (avoid flicker)
  if (grid.children.length !== appliances.length) {
    grid.innerHTML = "";
    appliances.forEach((appliance) => {
      const card = document.createElement("div");
      card.className = `appliance-card ${appliance.status === "ON" ? "on" : ""}`;
      card.id = `appliance-${appliance.name.replace(/\s+/g, "-")}`;

      card.innerHTML = `
        <div class="appliance-icon">${ICONS[appliance.name] || "🔌"}</div>
        <div class="appliance-name">${appliance.name}</div>
        <div class="appliance-wattage">${appliance.wattage} W</div>
        <label class="toggle-switch">
          <input type="checkbox" ${appliance.status === "ON" ? "checked" : ""}
                 onchange="toggleAppliance('${appliance.name}', this.checked)">
          <span class="toggle-slider"></span>
        </label>
        <div class="appliance-status-text">${appliance.status}</div>
        <div class="appliance-hours">Can run ${appliance.remaining_hours || 0}h more</div>
      `;
      grid.appendChild(card);
    });
  } else {
    // Update existing cards without rebuilding
    appliances.forEach((appliance) => {
      const card = document.getElementById(`appliance-${appliance.name.replace(/\s+/g, "-")}`);
      if (!card) return;
      card.className = `appliance-card ${appliance.status === "ON" ? "on" : ""}`;
      const checkbox = card.querySelector('input[type="checkbox"]');
      if (checkbox && checkbox.checked !== (appliance.status === "ON")) {
        checkbox.checked = appliance.status === "ON";
      }
      card.querySelector(".appliance-status-text").textContent = appliance.status;
      card.querySelector(".appliance-hours").textContent = `Can run ${appliance.remaining_hours || 0}h more`;
    });
  }
}

// ─── Recommendations ─────────────────────────────────────────────────────
function renderRecommendations(recs) {
  const list = document.getElementById("rec-list");
  if (!recs || recs.length === 0) return;

  list.innerHTML = "";
  recs.forEach((rec) => {
    const item = document.createElement("div");
    item.className = `rec-item ${rec.severity}`;

    let icon = "ℹ️";
    if (rec.severity === "good") icon = "✅";
    else if (rec.severity === "warning") icon = "⚠️";
    else if (rec.severity === "critical") icon = "🚨";

    item.innerHTML = `
      <span class="rec-icon">${icon}</span>
      <span class="rec-text">${rec.message}</span>
    `;
    list.appendChild(item);
  });
}

// ─── API: Fetch Usage Data ───────────────────────────────────────────────
async function fetchUsage() {
  try {
    const res = await fetch(`${API}/get_usage`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    setConnectionStatus(true);

    // Animate stat values
    animateValue(document.getElementById("stat-power"), data.current_power_watts, 0);
    animateValue(document.getElementById("stat-today"), data.today_kwh, 2);
    animateValue(document.getElementById("stat-month"), data.current_month_kwh, 2);
    animateValue(document.getElementById("stat-cost"), data.estimated_cost, 0);

    // Sub-text
    document.getElementById("stat-power-sub").textContent = `Peak: ${data.peak_power_watts} W`;
    document.getElementById("stat-today-sub").textContent = `Updated just now`;
    document.getElementById("stat-month-sub").textContent = `of ${data.monthly_limit} kWh limit`;
    document.getElementById("stat-cost-sub").textContent = `Projected: ₹${data.projected_cost || 0}`;

    // Gauge
    updateGauge(data.budget_percentage || 0);
    document.getElementById("gauge-remaining").textContent = `${data.remaining_budget} kWh`;
    document.getElementById("gauge-projected").textContent = `${data.projected_monthly || 0} kWh`;
    const activeCount = data.appliances.filter((a) => a.status === "ON").length;
    document.getElementById("gauge-active").textContent = activeCount;

    // Settings inputs (don't override if user is typing)
    const limitInput = document.getElementById("input-limit");
    if (document.activeElement !== limitInput) {
      limitInput.value = data.monthly_limit;
    }
    const rateInput = document.getElementById("input-rate");
    if (document.activeElement !== rateInput) {
      rateInput.value = data.electricity_rate;
    }

    // Appliances
    renderAppliances(data.appliances);

    // Recommendations
    renderRecommendations(data.recommendations);
  } catch (err) {
    setConnectionStatus(false);
    console.error("Fetch error:", err);
  }
}

// ─── API: Fetch History for Chart ────────────────────────────────────────
async function fetchHistory() {
  try {
    const res = await fetch(`${API}/get_history`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    chartData = data.hourly_history || [];
    drawChart(chartData);
  } catch (err) {
    // Silently fail — chart just stays empty
  }
}

// ─── API: Toggle Appliance ───────────────────────────────────────────────
async function toggleAppliance(name, isOn) {
  try {
    const res = await fetch(`${API}/toggle_appliance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ appliance: name, status: isOn ? "ON" : "OFF" }),
    });
    const data = await res.json();
    showToast(`${name} turned ${isOn ? "ON" : "OFF"}`, "success");
    fetchUsage(); // Refresh immediately
  } catch (err) {
    showToast(`Failed to toggle ${name}`, "error");
  }
}

// ─── API: Save Settings ──────────────────────────────────────────────────
async function saveSettings() {
  const limit = parseFloat(document.getElementById("input-limit").value);
  const rate = parseFloat(document.getElementById("input-rate").value);

  if (isNaN(limit) || limit <= 0) {
    showToast("Please enter a valid monthly limit", "error");
    return;
  }
  if (isNaN(rate) || rate <= 0) {
    showToast("Please enter a valid electricity rate", "error");
    return;
  }

  try {
    await fetch(`${API}/set_limit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ monthly_limit: limit, electricity_rate: rate }),
    });
    showToast("Settings saved!", "success");
    fetchUsage();
  } catch (err) {
    showToast("Failed to save settings", "error");
  }
}

// ─── API: Reset Data ─────────────────────────────────────────────────────
async function resetData() {
  if (!confirm("Reset all energy data? This cannot be undone.")) return;
  try {
    await fetch(`${API}/reset`, { method: "POST" });
    showToast("All data has been reset", "info");
    fetchUsage();
    fetchHistory();
  } catch (err) {
    showToast("Failed to reset data", "error");
  }
}

// ─── Responsive Chart Resize ─────────────────────────────────────────────
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => drawChart(chartData), 200);
});

// ─── Init ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  fetchUsage();
  fetchHistory();

  // Auto-poll
  setInterval(fetchUsage, POLL_INTERVAL);
  setInterval(fetchHistory, POLL_INTERVAL * 3); // Chart updates less frequently
});
