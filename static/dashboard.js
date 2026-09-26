const MAX_POINTS = 40;

const tempEl = document.getElementById("temp-value");
const pressureEl = document.getElementById("pressure-value");
const cycleEl = document.getElementById("cycle-value");
const statusBadge = document.getElementById("status-badge");
const restartBtn = document.getElementById("restart-btn");
const restartFeedback = document.getElementById("restart-feedback");
const alarmsTableBody = document.querySelector("#alarms-table tbody");

const ctx = document.getElementById("trend-chart").getContext("2d");
const chart = new Chart(ctx, {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        label: "Teplota (°C)",
        data: [],
        borderColor: "#4fa3ff",
        tension: 0.3,
        pointRadius: 0,
      },
      {
        label: "Tlak (bar)",
        data: [],
        borderColor: "#f2b134",
        tension: 0.3,
        pointRadius: 0,
      },
    ],
  },
  options: {
    responsive: true,
    animation: false,
    scales: {
      x: { ticks: { color: "#8b96ab" } },
      y: { ticks: { color: "#8b96ab" } },
    },
    plugins: {
      legend: { labels: { color: "#e8ecf4" } },
    },
  },
});

function setStatusBadge(status) {
  statusBadge.textContent = status;
  statusBadge.className = "badge status-" + status.toLowerCase();
}

function formatTime(ts) {
  return new Date(ts * 1000).toLocaleTimeString();
}

function applyReading(data) {
  tempEl.textContent = data.temperature_c;
  pressureEl.textContent = data.pressure_bar;
  cycleEl.textContent = data.cycle_count;
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

async function loadInitialData() {
  const [historyRes, alarmsRes] = await Promise.all([
    fetch("/api/history?limit=" + MAX_POINTS),
    fetch("/api/alarms"),
  ]);
  const history = await historyRes.json();
  const alarms = await alarmsRes.json();
  history.forEach(applyReading);
  renderAlarms(alarms);
}

function connectWebSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${location.host}/ws`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "reading") {
      applyReading(data);
    }
    if (data.type === "restart_ack") {
      fetch("/api/alarms")
        .then((r) => r.json())
        .then(renderAlarms);
    }
  };

  ws.onclose = () => {
    restartFeedback.textContent = "Spojenie prerušené, obnovujem...";
    setTimeout(connectWebSocket, 2000);
  };
}

restartBtn.addEventListener("click", async () => {
  restartFeedback.textContent = "Posielam príkaz na reštart...";
  const res = await fetch("/api/restart", { method: "POST" });
  const data = await res.json();
  restartFeedback.textContent = `Hotovo. Nový stav: ${data.status}`;
  setTimeout(() => (restartFeedback.textContent = ""), 4000);
});

loadInitialData();
connectWebSocket();
