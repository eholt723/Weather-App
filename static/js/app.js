const form = document.getElementById("search");
const zipEl = document.getElementById("zip");
const unitsEl = document.getElementById("units");
const statusEl = document.getElementById("status");
const histEl = document.getElementById("history");
let chart;

function pushHistory(zip, units) {
  const key = "history";
  const arr = JSON.parse(localStorage.getItem(key) || "[]");
  const entry = { zip, units };
  const filtered = [entry, ...arr.filter(a => a.zip !== zip)].slice(0, 6);
  localStorage.setItem(key, JSON.stringify(filtered));
  renderHistory();
}
function renderHistory() {
  const arr = JSON.parse(localStorage.getItem("history") || "[]");
  histEl.innerHTML = "";
  arr.forEach(({zip, units}) => {
    const b = document.createElement("button");
    b.className = "btn btn-outline-secondary btn-sm";
    b.textContent = `${zip} (${units === "metric" ? "C" : "F"})`;
    b.onclick = () => {
      zipEl.value = zip; unitsEl.value = units;
      form.dispatchEvent(new Event("submit"));
    };
    histEl.appendChild(b);
  });
}

async function fetchWeather(zip, units) {
  statusEl.textContent = "Loading...";
  try {
    const res = await fetch(`/api/weather?zip=${encodeURIComponent(zip)}&units=${units}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed.");

    // Build a simple temperature time series from forecast list
    const labels = data.forecast.list.map(p => new Date(p.dt * 1000).toLocaleString());
    const temps = data.forecast.list.map(p => p.main.temp);

    if (chart) chart.destroy();
    const ctx = document.getElementById("tempChart").getContext("2d");
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{ label: "Forecast Temp", data: temps, tension: 0.25 }]
      },
      options: {
        responsive: true,
        animation: false,
        scales: { x: { ticks: { maxRotation: 0, autoSkip: true } } }
      }
    });

    statusEl.textContent = `Current: ${data.current.name} – ${Math.round(data.current.main.temp)}°`;
    pushHistory(zip, units);
  } catch (e) {
    statusEl.textContent = `Error: ${e.message}`;
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  fetchWeather(zipEl.value.trim(), unitsEl.value);
});
renderHistory();

