const state = {
  token: localStorage.getItem("server-monitor-token") || "",
  autoRefresh: true,
  refreshMs: 5000,
  timer: null,
  history: {
    cpu: [],
    memory: [],
    disk: [],
  },
  lastNetwork: null,
  containers: [],
  readOnly: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDuration(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days} 天 ${hours} 小时`;
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟`;
  return `${minutes} 分钟`;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    openTokenModal();
    throw new Error("需要 API 令牌");
  }
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || response.statusText);
  }
  return data;
}

function setText(selector, value) {
  const node = $(selector);
  if (node) node.textContent = value;
}

function updateHistory(metrics) {
  const diskMax = metrics.disk?.[0]?.percent ?? 0;
  state.history.cpu.push(metrics.cpu.usage_percent);
  state.history.memory.push(metrics.memory.percent);
  state.history.disk.push(diskMax);
  for (const key of Object.keys(state.history)) {
    if (state.history[key].length > 80) state.history[key].shift();
  }
}

function drawChart() {
  const canvas = $("#resourceChart");
  const ctx = canvas.getContext("2d");
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.scale(ratio, ratio);

  const width = rect.width;
  const height = rect.height;
  const padding = 28;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "#dbe2da";
  ctx.lineWidth = 1;
  ctx.font = "12px system-ui, sans-serif";
  ctx.fillStyle = "#64706c";

  for (let i = 0; i <= 4; i += 1) {
    const y = padding + ((height - padding * 2) * i) / 4;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
    ctx.fillText(`${100 - i * 25}%`, 6, y + 4);
  }

  const series = [
    ["cpu", "#d35f2d"],
    ["memory", "#5a58b8"],
    ["disk", "#1f8c8f"],
  ];

  for (const [key, color] of series) {
    const values = state.history[key];
    if (values.length < 2) continue;
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    values.forEach((value, index) => {
      const x = padding + ((width - padding * 2) * index) / Math.max(1, values.length - 1);
      const y = padding + (height - padding * 2) * (1 - value / 100);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  }
}

function networkTotals(metrics) {
  const interfaces = metrics.network.filter((item) => item.interface !== "lo");
  return {
    timestamp: metrics.timestamp,
    rx: interfaces.reduce((sum, item) => sum + item.rx_bytes, 0),
    tx: interfaces.reduce((sum, item) => sum + item.tx_bytes, 0),
  };
}

function updateNetworkRate(metrics) {
  const current = networkTotals(metrics);
  if (!state.lastNetwork) {
    state.lastNetwork = current;
    setText("#networkRate", "--");
    return;
  }
  const seconds = Math.max(1, current.timestamp - state.lastNetwork.timestamp);
  const rxRate = Math.max(0, (current.rx - state.lastNetwork.rx) / seconds);
  const txRate = Math.max(0, (current.tx - state.lastNetwork.tx) / seconds);
  state.lastNetwork = current;
  setText("#networkRate", `↓ ${formatBytes(rxRate)}/s  ↑ ${formatBytes(txRate)}/s`);
}

function renderMetrics(metrics) {
  const disk = metrics.disk?.[0] || { percent: 0, used: 0, total: 0 };
  setText("#hostName", metrics.hostname);
  setText(
    "#systemLine",
    `${metrics.platform} · ${metrics.cpu.cores} cores · uptime ${formatDuration(metrics.uptime_seconds)} · ${metrics.process_count} processes`,
  );
  setText("#cpuValue", `${metrics.cpu.usage_percent.toFixed(1)}%`);
  setText(
    "#loadValue",
    `load ${metrics.cpu.load_average.one.toFixed(2)} / ${metrics.cpu.load_average.five.toFixed(2)} / ${metrics.cpu.load_average.fifteen.toFixed(2)}`,
  );
  setText("#memoryValue", `${metrics.memory.percent.toFixed(1)}%`);
  setText("#memoryBytes", `${formatBytes(metrics.memory.used)} / ${formatBytes(metrics.memory.total)}`);
  setText("#diskValue", `${disk.percent.toFixed(1)}%`);
  setText("#diskBytes", `${formatBytes(disk.used)} / ${formatBytes(disk.total)}`);
  setText("#lastRefresh", new Date(metrics.timestamp * 1000).toLocaleTimeString());

  updateHistory(metrics);
  updateNetworkRate(metrics);
  drawChart();
  renderDisk(metrics.disk);
  renderNetwork(metrics.network);
}

function renderDisk(disks) {
  const list = $("#diskList");
  if (!disks.length) {
    list.innerHTML = `<div class="empty-cell">没有可用磁盘数据</div>`;
    return;
  }
  list.innerHTML = disks
    .map(
      (disk) => `
        <div class="meter">
          <div class="meter-header">
            <strong>${disk.label}</strong>
            <span>${formatBytes(disk.used)} / ${formatBytes(disk.total)} · ${disk.percent.toFixed(1)}%</span>
          </div>
          <div class="meter-bar"><i style="width: ${Math.min(100, disk.percent)}%"></i></div>
        </div>
      `,
    )
    .join("");
}

function renderNetwork(interfaces) {
  const body = $("#networkTableBody");
  const visible = interfaces.filter((item) => item.interface !== "lo");
  if (!visible.length) {
    body.innerHTML = `<tr><td colspan="4" class="empty-cell">没有可用网络数据</td></tr>`;
    return;
  }
  body.innerHTML = visible
    .map(
      (item) => `
        <tr>
          <td><strong>${item.interface}</strong></td>
          <td>${formatBytes(item.rx_bytes)}</td>
          <td>${formatBytes(item.tx_bytes)}</td>
          <td>${item.rx_errors + item.tx_errors}</td>
        </tr>
      `,
    )
    .join("");
}

function stateBadge(stateName) {
  return `<span class="badge ${stateName}">${stateName}</span>`;
}

function renderContainerOverview(payload) {
  if (!payload.available) {
    setText("#dockerValue", "离线");
    setText("#dockerState", "socket 不可用");
    $("#containerStateGrid").innerHTML = `<div class="empty-cell">${payload.error || "Docker 不可用"}</div>`;
    $("#recentContainers").innerHTML = "";
    return;
  }

  const containers = payload.items || [];
  const running = payload.counts.running || 0;
  setText("#dockerValue", `${running}/${containers.length}`);
  setText("#dockerState", `${running} running`);
  $("#readOnlyBadge").textContent = state.readOnly ? "只读" : "可操作";

  const knownStates = ["running", "exited", "paused", "created"];
  $("#containerStateGrid").innerHTML = knownStates
    .map(
      (name) => `
        <div class="state-pill">
          <strong>${payload.counts[name] || 0}</strong>
          <span>${name}</span>
        </div>
      `,
    )
    .join("");

  $("#recentContainers").innerHTML = containers
    .slice(0, 5)
    .map(
      (item) => `
        <div class="compact-item">
          <strong>${item.name}</strong>
          ${stateBadge(item.state)}
        </div>
      `,
    )
    .join("");
}

function actionButtons(container) {
  const disabled = state.readOnly ? "disabled" : "";
  const start = `<button class="small-button" ${disabled} data-action="start" data-id="${container.id}">启动</button>`;
  const stop = `<button class="small-button" ${disabled} data-action="stop" data-id="${container.id}">停止</button>`;
  const restart = `<button class="small-button" ${disabled} data-action="restart" data-id="${container.id}">重启</button>`;
  const pause =
    container.state === "paused"
      ? `<button class="small-button" ${disabled} data-action="unpause" data-id="${container.id}">恢复</button>`
      : `<button class="small-button" ${disabled} data-action="pause" data-id="${container.id}">暂停</button>`;
  const remove = `<button class="danger-button" ${disabled} data-action="remove" data-id="${container.id}">删除</button>`;

  if (container.state === "running") return `${stop}${restart}${pause}`;
  if (container.state === "paused") return `${pause}${restart}`;
  return `${start}${remove}`;
}

function renderContainerTable() {
  const body = $("#containerTableBody");
  const query = $("#containerSearch").value.trim().toLowerCase();
  const filter = $("#stateFilter").value;
  const rows = state.containers.filter((item) => {
    const haystack = `${item.name} ${item.image} ${item.state} ${item.status} ${item.compose_project || ""}`.toLowerCase();
    return (filter === "all" || item.state === filter) && (!query || haystack.includes(query));
  });

  setText("#containerCount", `${rows.length} / ${state.containers.length}`);
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="6" class="empty-cell">没有匹配的容器</td></tr>`;
    return;
  }

  body.innerHTML = rows
    .map(
      (item) => `
        <tr>
          <td>
            <div class="cell-main">
              <strong title="${item.name}">${item.name}</strong>
              <small>${item.short_id}</small>
            </div>
          </td>
          <td><div class="truncate" title="${item.image}">${item.image}</div></td>
          <td>${stateBadge(item.state)}<br /><small>${item.status}</small></td>
          <td>${item.ports.length ? item.ports.join("<br />") : "<small>--</small>"}</td>
          <td>${item.compose_project ? `${item.compose_project}<br /><small>${item.compose_service || ""}</small>` : "<small>--</small>"}</td>
          <td><div class="row-actions">${actionButtons(item)}</div></td>
        </tr>
      `,
    )
    .join("");
}

async function runContainerAction(containerId, action) {
  const container = state.containers.find((item) => item.id === containerId);
  if (!container) return;
  if (action === "remove" && !window.confirm(`删除容器 ${container.name}？`)) return;
  if (["stop", "kill"].includes(action) && !window.confirm(`${action === "stop" ? "停止" : "终止"}容器 ${container.name}？`)) return;

  try {
    await api(`/api/docker/containers/${encodeURIComponent(containerId)}/actions/${action}`, {
      method: "POST",
      body: JSON.stringify({ timeout: 10, force: action === "remove" }),
    });
    showToast(`${container.name} 已执行 ${action}`);
    await refresh();
  } catch (error) {
    showToast(error.message);
  }
}

function switchTab(tab) {
  $$(".nav-tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tab));
  $$(".tab-panel").forEach((panel) => panel.classList.remove("active"));
  $(`#${tab}Panel`).classList.add("active");
}

async function refresh() {
  try {
    const data = await api("/api/overview");
    state.readOnly = data.read_only;
    state.containers = data.containers.items || [];
    renderMetrics(data.metrics);
    renderContainerOverview(data.containers);
    renderContainerTable();
  } catch (error) {
    showToast(error.message);
  }
}

function scheduleRefresh() {
  window.clearInterval(state.timer);
  if (!state.autoRefresh) return;
  state.timer = window.setInterval(refresh, state.refreshMs);
}

function openTokenModal() {
  $("#tokenInput").value = state.token;
  $("#tokenModal").hidden = false;
  $("#tokenInput").focus();
}

function closeTokenModal() {
  $("#tokenModal").hidden = true;
}

function bindEvents() {
  $$(".nav-tab").forEach((button) => button.addEventListener("click", () => switchTab(button.dataset.tab)));
  $("#refreshButton").addEventListener("click", refresh);
  $("#tokenButton").addEventListener("click", openTokenModal);
  $("#closeTokenButton").addEventListener("click", closeTokenModal);
  $("#clearTokenButton").addEventListener("click", () => {
    state.token = "";
    localStorage.removeItem("server-monitor-token");
    closeTokenModal();
    refresh();
  });
  $("#tokenForm").addEventListener("submit", (event) => {
    event.preventDefault();
    state.token = $("#tokenInput").value.trim();
    localStorage.setItem("server-monitor-token", state.token);
    closeTokenModal();
    refresh();
  });
  $("#autoRefreshToggle").addEventListener("change", (event) => {
    state.autoRefresh = event.target.checked;
    scheduleRefresh();
  });
  $("#refreshInterval").addEventListener("change", (event) => {
    state.refreshMs = Number(event.target.value);
    scheduleRefresh();
  });
  $("#containerSearch").addEventListener("input", renderContainerTable);
  $("#stateFilter").addEventListener("change", renderContainerTable);
  $("#containerTableBody").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    runContainerAction(button.dataset.id, button.dataset.action);
  });
  window.addEventListener("resize", drawChart);
}

bindEvents();
refresh();
scheduleRefresh();

