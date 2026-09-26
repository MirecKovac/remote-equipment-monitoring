const MAX_POINTS = 40;

let currentLine = "line1";
let ws = null;

const tempEl = document.getElementById("temp-value");
const tempSetpointEl = document.getElementById("temp-setpoint");
const pressureEl = document.getElementById("pressure-value");
const pressureSetpointEl = document.getElementById("pressure-setpoint");
const cycleEl = document.getElementById("cycle-value");
const statusBadge = document.getElementById("status-badge");
const controlFeedback = document.getElementById("control-feedback");
const setpointFeedback = document.getElementById("setpoint-feedback");
const alarmsTableBody = document.querySelector("#alarms-table tbody");
const lineTabs = document.getElementById("line-tabs");
const setpointTempInput = document.getElementById("setpoint-temp-input");
const setpointPressureInput = document.getElementById("setpoint-pressure-input");

const ctx = document.getElementById("trend-chart").getContext("2d");
const chart = new Chart(ctx, {
  type: "line",
  data: {
    labels: [],
    datasets: [
      { label: "Teplota (°C)", data: [], borderColor: "#4fa3ff", tension: 0.3, pointRadius: 0 },
      { label: "Tlak (bar)", data: [], borderColor: "#f2b134", tension: 0.3, pointRadius: 0 },
    ],
  },
  options: {
    responsive: true,
    animation: false,
    scales: {
      x: { ticks: { color: "#8b96ab" } },
      y: { ticks: { color: "#8b96ab" } },
    },
    plugins: { legend: { labels: { color: "#e8ecf4" } } },
  },
});

function setStatusBadge(status) {
  statusBadge.textContent = status;
  statusBadge.className = "badge status-" + status.toLowerCase();
}

function formatTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString();
}

function resetChart() {
  chart.data.labels = [];
  chart.data.datasets[0].data = [];
  chart.data.datasets[1].data = [];
  chart.update();
}

function applyReading(data) {
  tempEl.textContent = data.temperature_c;
  pressureEl.textContent = data.pressure_bar;
  cycleEl.textContent = data.cycle_count;
  if (data.setpoint_temp !== undefined) tempSetpointEl.textContent = data.setpoint_temp;
  if (data.setpoint_pressure !== undefined) pressureSetpointEl.textContent = data.setpoint_pressure;
  setStatusBadge(data.status);

  chart.data.labels.push(formatTime(data.timestamp));
  chart.data.datasets[0].data.push(data.temperature_c);
  chart.data.datasets[1].data.push(data.pressure_bar);

  if (chart.data.labels.length > MAX_POINTS) {
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
    chart.data.datasets[1].data.shift();
  }
  chart.update();
}

function renderAlarms(alarms) {
  alarmsTableBody.innerHTML = "";
  alarms.forEach((a) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${formatTime(a.timestamp)}</td>
      <td>${a.message}</td>
      <td>${a.acknowledged ? "✅" : "⏳"}</td>
    `;
    alarmsTableBody.appendChild(row);
  });
}

async function loadLines() {
  const res = await fetch("/api/lines");
  const lineList = await res.json();
  lineTabs.innerHTML = "";
  lineList.forEach((line) => {
    const btn = document.createElement("button");
    btn.textContent = line.name;
    btn.className = "line-tab" + (line.id === currentLine ? " active" : "");
    btn.addEventListener("click", () => switchLine(line.id));
    lineTabs.appendChild(btn);
  });
}

async function loadInitialData() {
  const [statusRes, historyRes, alarmsRes] = await Promise.all([
    fetch(`/api/status?line=${currentLine}`),
    fetch(`/api/history?line=${currentLine}&limit=${MAX_POINTS}`),
    fetch(`/api/alarms?line=${currentLine}`),
  ]);
  const status = await statusRes.json();
  const history = await historyRes.json();
  const alarms = await alarmsRes.json();

  setpointTempInput.value = status.setpoint_temp;
  setpointPressureInput.value = status.setpoint_pressure;
  setStatusBadge(status.status);

  history.forEach((h) =>
    applyReading({ ...h, setpoint_temp: status.setpoint_temp, setpoint_pressure: status.setpoint_pressure })
  );
  renderAlarms(alarms);
}

function connectWebSocket() {
  if (ws) {
    ws.onclose = null;
    ws.close();
  }
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${protocol}://${location.host}/ws/${currentLine}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "reading") applyReading(data);
    if (data.type === "restart_ack") {
      fetch(`/api/alarms?line=${currentLine}`)
        .then((r) => r.json())
        .then(renderAlarms);
    }
  };

  ws.onclose = () => setTimeout(connectWebSocket, 2000);
}

async function switchLine(lineId) {
  currentLine = lineId;
  document.querySelectorAll(".line-tab").forEach((btn, i) => {
    btn.classList.toggle("active", btn.textContent === lineTabs.children[i]?.textContent);
  });
  Array.from(lineTabs.children).forEach((btn) => btn.classList.remove("active"));
  await loadLines();
  resetChart();
  await loadInitialData();
  connectWebSocket();
}

async function postControl(endpoint) {
  controlFeedback.textContent = "Posielam príkaz...";
  const res = await fetch(`/api/${endpoint}?line=${currentLine}`, { method: "POST" });
  const data = await res.json();
  controlFeedback.textContent = `Hotovo. Nový stav: ${data.status}`;
  setTimeout(() => (controlFeedback.textContent = ""), 4000);
}

document.getElementById("start-btn").addEventListener("click", () => postControl("start"));
document.getElementById("stop-btn").addEventListener("click", () => postControl("stop"));
document.getElementById("restart-btn").addEventListener("click", () => postControl("restart"));

document.getElementById("export-btn").addEventListener("click", () => {
  window.location.href = `/api/export?line=${currentLine}`;
});

document.getElementById("apply-setpoint-btn").addEventListener("click", async () => {
  setpointFeedback.textContent = "Ukladám...";
  const res = await fetch(`/api/setpoint?line=${currentLine}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      temperature: parseFloat(setpointTempInput.value),
      pressure: parseFloat(setpointPressureInput.value),
    }),
  });
  const data = await res.json();
  setpointFeedback.textContent = `Nastavené: ${data.setpoint_temp}°C / ${data.setpoint_pressure} bar`;
  setTimeout(() => (setpointFeedback.textContent = ""), 4000);
});

(async function init() {
  await loadLines();
  await loadInitialData();
  connectWebSocket();
})();
