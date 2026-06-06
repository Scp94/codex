const TOKEN = window.FUND_ADVISOR_TOKEN || "";
let state = {};
let activeChartSymbol = "";
let chartRequestSeq = 0;

function setStatus(text, ok = true) {
  const el = document.getElementById("status");
  el.textContent = text;
  el.className = ok ? "status ok" : "status danger-text";
}

function qs(params) {
  const query = new URLSearchParams({ token: TOKEN });
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value) !== "") query.set(key, value);
  });
  return query.toString();
}

async function api(path, params) {
  const response = await fetch(`${path}?${qs(params)}`);
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { detail: text }; }
  if (!response.ok) throw new Error(data.detail || response.statusText);
  return data;
}

function value(id) { return document.getElementById(id).value.trim(); }
function num(id) {
  const raw = value(id);
  return raw === "" ? "" : Number(raw);
}
function money(value) {
  const n = Number(value || 0);
  return n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function pct(value) {
  if (value === undefined || value === null || value === "") return "-";
  const n = Number(value);
  const cls = n >= 0 ? "up" : "down";
  return `<span class="${cls}">${n.toFixed(2)}%</span>`;
}

async function loadAll() {
  try {
    const [portfolio, overrides] = await Promise.all([
      api("/portfolio"),
      api("/market/price-overrides"),
    ]);
    state = { portfolio, overrides: overrides.price_overrides || {} };
    render();
    setStatus("已刷新");
  } catch (error) {
    setStatus(error.message, false);
  }
}

function render() {
  parkChartPanel();
  const positions = state.portfolio.positions || [];
  const universe = state.portfolio.universe || [];
  const trades = state.portfolio.transactions || [];
  document.getElementById("positionCount").textContent = positions.length;
  document.getElementById("universeCount").textContent = universe.length;
  document.getElementById("tradeCount").textContent = trades.length;
  document.getElementById("positionsBody").innerHTML = positions.map(item => `
    <tr>
      <td><b>${item.symbol}</b><br><span class="muted">${item.name || nameFor(item.symbol) || ""}</span></td>
      <td>${money(item.principal)}</td>
      <td>${Number(item.shares || 0).toFixed(4)}</td>
      <td>${Number(item.cost_basis || 0).toFixed(4)}</td>
      <td class="actions">
        <div class="action-buttons">
          <button class="secondary" onclick="editFund('${item.symbol}')">修改</button>
          <button class="danger" onclick="removeFund('${item.symbol}')">删除</button>
        </div>
      </td>
    </tr>`).join("");
  document.getElementById("positionsCards").innerHTML = positions.map(item => {
    const name = item.name || nameFor(item.symbol) || "";
    return `
    <article class="fund-card">
      <div class="fund-card-head">
        <div><b>${item.symbol}</b><span>${name}</span></div>
      </div>
      <div class="card-metrics">
        <div><span>本金</span><b>${money(item.principal)}</b></div>
        <div><span>份额</span><b>${Number(item.shares || 0).toFixed(4)}</b></div>
        <div><span>成本价</span><b>${Number(item.cost_basis || 0).toFixed(4)}</b></div>
      </div>
      <div class="card-actions">
        <button class="secondary" onclick="editFund('${item.symbol}')">修改</button>
        <button class="danger" onclick="removeFund('${item.symbol}')">删除</button>
      </div>
    </article>`;
  }).join("");
  document.getElementById("universeBody").innerHTML = universe.map(item => {
    const symbol = item.symbol || item;
    return `
    <tr onclick="loadFundChart('${symbol}')">
      <td><b>${symbol}</b><br><span class="muted">${item.name || ""}</span></td>
      <td>${item.nav ?? "-"}</td>
      <td>${pct(item.daily_return_pct)}</td>
      <td>${pct(item.return_1w_pct)}</td>
      <td>${pct(item.return_1m_pct)}</td>
      <td>${pct(item.return_3m_pct)}</td>
      <td>${pct(item.return_6m_pct)}</td>
      <td>${pct(item.return_1y_pct)}</td>
    </tr>
    <tr id="chartRow-${symbol}" class="chart-row">
      <td colspan="8"><div id="chartSlot-${symbol}" class="chart-slot"></div></td>
    </tr>`;
  }).join("");
  document.getElementById("universeCards").innerHTML = universe.map(item => {
    const symbol = item.symbol || item;
    return `
    <article class="fund-card trend-card" onclick="loadFundChart('${symbol}')">
      <div class="fund-card-head">
        <div><b>${symbol}</b><span>${item.name || ""}</span></div>
        <strong>${item.nav ?? "-"}</strong>
      </div>
      <div class="card-metrics trend-metrics">
        <div><span>日涨</span><b>${pct(item.daily_return_pct)}</b></div>
        <div><span>近1周</span><b>${pct(item.return_1w_pct)}</b></div>
        <div><span>近1月</span><b>${pct(item.return_1m_pct)}</b></div>
        <div><span>近3月</span><b>${pct(item.return_3m_pct)}</b></div>
        <div><span>近6月</span><b>${pct(item.return_6m_pct)}</b></div>
        <div><span>近1年</span><b>${pct(item.return_1y_pct)}</b></div>
      </div>
      <div id="chartCardSlot-${symbol}" class="chart-slot"></div>
    </article>`;
  }).join("");
  document.getElementById("tradesBody").innerHTML = trades.slice().reverse().map(item => `
    <tr>
      <td>${item.timestamp || ""}</td><td>${item.symbol}</td><td>${item.action}</td>
      <td>${money(item.amount)}</td><td>${Number(item.nav || 0).toFixed(4)}</td>
      <td>${Number(item.shares || 0).toFixed(4)}</td>
    </tr>`).join("");
  document.getElementById("tradesCards").innerHTML = trades.slice().reverse().map(item => `
    <article class="fund-card">
      <div class="fund-card-head">
        <div><b>${item.symbol}</b><span>${item.timestamp || ""}</span></div>
        <strong>${item.action}</strong>
      </div>
      <div class="card-metrics">
        <div><span>金额</span><b>${money(item.amount)}</b></div>
        <div><span>净值</span><b>${Number(item.nav || 0).toFixed(4)}</b></div>
        <div><span>份额</span><b>${Number(item.shares || 0).toFixed(4)}</b></div>
      </div>
    </article>`).join("");
  document.getElementById("overridesBody").innerHTML = Object.entries(state.overrides || {}).map(([symbol, item]) => `
    <tr onclick="editOverride('${symbol}')">
      <td>${symbol}</td><td>${item.price ?? ""}</td><td>${item.previous_close ?? ""}</td><td>${item.as_of_date || ""}</td>
    </tr>`).join("");
  document.getElementById("overridesCards").innerHTML = Object.entries(state.overrides || {}).map(([symbol, item]) => `
    <article class="fund-card" onclick="editOverride('${symbol}')">
      <div class="fund-card-head">
        <div><b>${symbol}</b><span>${item.as_of_date || ""}</span></div>
      </div>
      <div class="card-metrics">
        <div><span>当前净值</span><b>${item.price ?? ""}</b></div>
        <div><span>上一净值</span><b>${item.previous_close ?? ""}</b></div>
      </div>
    </article>`).join("");
}

function parkChartPanel() {
  const panel = document.getElementById("chartPanel");
  const home = document.getElementById("chartPanelHome");
  if (panel && home && !home.contains(panel)) home.appendChild(panel);
  document.querySelectorAll(".chart-row.active").forEach(row => row.classList.remove("active"));
  document.querySelectorAll(".trend-card.active").forEach(card => card.classList.remove("active"));
  if (panel) panel.classList.add("hidden");
  activeChartSymbol = "";
  chartRequestSeq += 1;
}

function nameFor(symbol) {
  const found = (state.portfolio.universe || []).find(item => (item.symbol || item) === symbol);
  return found && found.name;
}

function editFund(symbol) {
  const item = (state.portfolio.positions || []).find(row => row.symbol === symbol);
  if (!item) return;
  fundSymbol.value = item.symbol || "";
  fundName.value = item.name || nameFor(item.symbol) || "";
  fundPrincipal.value = item.principal || 0;
  fundShares.value = item.shares || 0;
  fundCostBasis.value = item.cost_basis || 0;
  fundMode.value = "edit";
  fundFormTitle.textContent = "修改原有持仓";
  saveFundButton.textContent = "保存修改";
  fundSymbol.readOnly = true;
  tradeSymbol.value = item.symbol || "";
  tradeName.value = fundName.value;
  overrideSymbol.value = item.symbol || "";
}

function clearFundForm() {
  ["fundSymbol", "fundName", "fundPrincipal", "fundShares", "fundCostBasis", "calcMarketValue", "calcNav", "calcGain"].forEach(id => {
    document.getElementById(id).value = "";
  });
  fundMode.value = "add";
  fundFormTitle.textContent = "新增持仓";
  saveFundButton.textContent = "新增持仓";
  fundSymbol.readOnly = false;
}

function fillFromHolding() {
  const amount = num("calcMarketValue");
  const nav = num("calcNav");
  const gain = num("calcGain");
  if (!amount || !nav) return setStatus("请输入持有总金额和当前净值", false);
  fundShares.value = (amount / nav).toFixed(4);
  if (gain !== "") fundPrincipal.value = (amount - gain).toFixed(2);
  if (!fundCostBasis.value && gain !== "") fundCostBasis.value = ((amount - gain) / (amount / nav)).toFixed(4);
  overrideSymbol.value = fundSymbol.value;
  overridePrice.value = nav;
}

async function lookupFund() {
  try {
    if (!value("fundSymbol")) return setStatus("请输入基金代码", false);
    setStatus("查询基金中...");
    const result = await api("/funds/lookup", { symbol: value("fundSymbol") });
    fundSymbol.value = result.symbol || fundSymbol.value;
    fundName.value = result.name || fundName.value;
    if (result.price) {
      calcNav.value = Number(result.price).toFixed(4);
      overrideSymbol.value = result.symbol;
      overridePrice.value = Number(result.price).toFixed(4);
    }
    if (result.previous_close) overridePrevious.value = Number(result.previous_close).toFixed(4);
    if (result.as_of_date) overrideDate.value = result.as_of_date;
    setStatus("基金数据已填入");
  } catch (error) { setStatus(error.message, false); }
}

async function autoLookupFund() {
  if (fundMode.value === "add" && value("fundSymbol") && !value("fundName")) {
    await lookupFund();
  }
}

async function saveFund() {
  try {
    await api("/portfolio/funds/upsert", {
      symbol: value("fundSymbol"),
      name: value("fundName"),
      principal: num("fundPrincipal") || 0,
      shares: num("fundShares") || 0,
      cost_basis: num("fundCostBasis"),
    });
    await loadAll();
    setStatus(fundMode.value === "edit" ? "修改已保存" : "持仓已新增");
    clearFundForm();
  } catch (error) { setStatus(error.message, false); }
}

async function refreshHotFunds() {
  try {
    setStatus("刷新热门基金中...");
    await api("/universe/refresh-hot", { limit: 10 });
    await loadAll();
    setStatus("候选基金池已更新");
  } catch (error) { setStatus(error.message, false); }
}

async function loadFundChart(symbol) {
  const panel = document.getElementById("chartPanel");
  if (activeChartSymbol === symbol && panel && !panel.classList.contains("hidden")) {
    closeChartPanel();
    return;
  }
  const requestId = ++chartRequestSeq;
  try {
    setStatus("加载净值趋势...");
    placeChartPanel(symbol);
    chartTitle.textContent = `净值趋势（${symbol}）`;
    chartMeta.textContent = "加载中...";
    drawChartMessage("加载净值历史...");
    const result = await api("/funds/history", { symbol, limit: 180 });
    if (requestId !== chartRequestSeq || activeChartSymbol !== symbol) return;
    const item = (state.portfolio.universe || []).find(row => (row.symbol || row) === symbol) || {};
    chartTitle.textContent = `${item.name || symbol}（${symbol}）`;
    chartMeta.textContent = `${item.date || ""}  近1月 ${formatPlainPct(item.return_1m_pct)}  近3月 ${formatPlainPct(item.return_3m_pct)}  近1年 ${formatPlainPct(item.return_1y_pct)}`;
    drawFundChart(result.history || []);
    setStatus("趋势图已更新");
  } catch (error) { setStatus(error.message, false); }
}

function placeChartPanel(symbol) {
  const panel = document.getElementById("chartPanel");
  const isMobile = window.matchMedia("(max-width: 900px)").matches;
  const slot = document.getElementById(`${isMobile ? "chartCardSlot" : "chartSlot"}-${symbol}`);
  if (!panel || !slot) return;
  document.querySelectorAll(".chart-row.active").forEach(row => row.classList.remove("active"));
  document.querySelectorAll(".trend-card.active").forEach(card => card.classList.remove("active"));
  const row = document.getElementById(`chartRow-${symbol}`);
  if (row && !isMobile) row.classList.add("active");
  const cardSlot = document.getElementById(`chartCardSlot-${symbol}`);
  const card = cardSlot && cardSlot.closest(".trend-card");
  if (card && isMobile) card.classList.add("active");
  slot.appendChild(panel);
  activeChartSymbol = symbol;
  panel.classList.remove("hidden");
  panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function closeChartPanel(event) {
  if (event) event.stopPropagation();
  parkChartPanel();
  setStatus("趋势图已关闭");
}

function formatPlainPct(value) {
  if (value === undefined || value === null || value === "") return "-";
  return `${Number(value).toFixed(2)}%`;
}

function drawFundChart(history) {
  const canvas = document.getElementById("fundChart");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  if (!history.length) {
    drawChartMessage("暂无净值历史");
    return;
  }
  const padding = { left: 56, right: 24, top: 24, bottom: 42 };
  const values = history.map(item => Number(item.nav)).filter(Number.isFinite);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const points = history.map((item, index) => {
    const x = padding.left + (history.length === 1 ? 0 : index / (history.length - 1) * plotW);
    const y = padding.top + (max - Number(item.nav)) / range * plotH;
    return { x, y, item };
  });

  ctx.strokeStyle = "#dfe3e8";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = padding.top + i / 4 * plotH;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
    const label = (max - i / 4 * range).toFixed(4);
    ctx.fillStyle = "#68707d";
    ctx.font = "12px sans-serif";
    ctx.fillText(label, 8, y + 4);
  }

  const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
  gradient.addColorStop(0, "rgba(22, 119, 255, .20)");
  gradient.addColorStop(1, "rgba(22, 119, 255, 0)");
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.lineTo(points[points.length - 1].x, height - padding.bottom);
  ctx.lineTo(points[0].x, height - padding.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.strokeStyle = "#1677ff";
  ctx.lineWidth = 2;
  ctx.stroke();

  const first = history[0];
  const last = history[history.length - 1];
  ctx.fillStyle = "#68707d";
  ctx.font = "12px sans-serif";
  ctx.fillText(first.date || "", padding.left, height - 14);
  ctx.fillText(last.date || "", width - padding.right - 90, height - 14);

  const lastPoint = points[points.length - 1];
  ctx.fillStyle = "#1677ff";
  ctx.beginPath();
  ctx.arc(lastPoint.x, lastPoint.y, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#20242b";
  ctx.font = "13px sans-serif";
  ctx.fillText(`${last.nav}`, Math.max(padding.left, lastPoint.x - 44), Math.max(18, lastPoint.y - 10));
}

function drawChartMessage(text) {
  const canvas = document.getElementById("fundChart");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#68707d";
  ctx.font = "16px sans-serif";
  ctx.fillText(text, 24, 42);
}

async function removeFund(symbol) {
  if (!confirm(`删除 ${symbol}？`)) return;
  try {
    await api("/portfolio/funds/delete", { symbol });
    await loadAll();
    setStatus("持仓已删除");
  } catch (error) { setStatus(error.message, false); }
}

function editOverride(symbol) {
  const item = state.overrides[symbol] || {};
  overrideSymbol.value = symbol;
  overridePrice.value = item.price || "";
  overridePrevious.value = item.previous_close || "";
  overrideDate.value = item.as_of_date || "";
}

async function saveOverride() {
  try {
    await api("/market/price-overrides/upsert", {
      symbol: value("overrideSymbol"),
      price: num("overridePrice"),
      previous_close: num("overridePrevious"),
      as_of_date: value("overrideDate"),
    });
    await loadAll();
    setStatus("净值已保存");
  } catch (error) { setStatus(error.message, false); }
}

async function deleteOverride() {
  try {
    await api("/market/price-overrides/delete", { symbol: value("overrideSymbol") });
    await loadAll();
    setStatus("净值覆盖已删除");
  } catch (error) { setStatus(error.message, false); }
}

async function saveTrade() {
  try {
    await api("/portfolio/trades/add", {
      symbol: value("tradeSymbol"),
      action: value("tradeAction"),
      amount: num("tradeAmount"),
      nav: num("tradeNav"),
      name: value("tradeName"),
    });
    await loadAll();
    setStatus("交易已记录");
  } catch (error) { setStatus(error.message, false); }
}

async function runAnalysis(sendDingtalk) {
  try {
    setStatus("分析中...");
    const result = await api("/analysis/run", { send_dingtalk: sendDingtalk });
    reportPreview.textContent = result.report || "";
    setStatus(sendDingtalk ? "已推送钉钉" : "报告已生成");
  } catch (error) { setStatus(error.message, false); }
}

function logout() {
  location.href = "/admin/login";
}

loadAll();
