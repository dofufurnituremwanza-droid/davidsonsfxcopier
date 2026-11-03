// DAVIDSONSFX TRADING COPIER — Real-Time Frontend Engine
let ws = null;
let authToken = localStorage.getItem("dfx_token") || "";

document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) lucide.createIcons();
  setupNavigation();
  await ensureAuthentication();
  initWebSocket();
  loadDashboardData();
  fetchLiveMarketQuotes();

  // Periodically refresh stats, active positions, and quotes
  setInterval(loadDashboardData, 4000);
  setInterval(fetchLiveMarketQuotes, 5000);
});

// ==================== AUTHENTICATION ====================
async function ensureAuthentication() {
  if (authToken) return;

  try {
    const formData = new URLSearchParams();
    formData.append("username", "admin");
    formData.append("password", "admin1234");

    const res = await fetch("/api/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("dfx_token", authToken);
    }
  } catch (err) {
    console.warn("Authentication notice:", err);
  }
}

function getAuthHeaders() {
  return {
    "Content-Type": "application/json",
    ...(authToken ? { "Authorization": `Bearer ${authToken}` } : {})
  };
}

// ==================== NAVIGATION ====================
function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      navButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const tabId = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
      const activePane = document.getElementById(`tab-${tabId}`);
      if (activePane) activePane.classList.add("active");

      const titleMap = {
        overview: "Trading Copier Dashboard",
        accounts: "Follower MT5 Accounts",
        master: "Master Signal Provider",
        trades: "Active Copied Positions",
        logs: "Execution Audit Trail",
        system: "Host & Terminal Diagnostics"
      };
      document.getElementById("page-title-text").textContent = titleMap[tabId] || "Trading Copier";
    });
  });
}

// ==================== WEBSOCKET ====================
function initWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    document.getElementById("ws-pulse").style.backgroundColor = "#10b981";
    document.getElementById("ws-status-text").textContent = "Cloud Relay Live";
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    } catch (e) {
      console.log("WS message:", event.data);
    }
  };

  ws.onclose = () => {
    document.getElementById("ws-pulse").style.backgroundColor = "#f43f5e";
    document.getElementById("ws-status-text").textContent = "Connecting...";
    setTimeout(initWebSocket, 3000);
  };
}

function handleWebSocketMessage(msg) {
  if (msg.type === "SIGNAL_PROCESSED" || msg.type === "TRADE_OPENED" || msg.type === "TRADE_CLOSED") {
    loadDashboardData();
  }
}

// ==================== LIVE MARKET QUOTES ====================
async function fetchLiveMarketQuotes() {
  try {
    const res = await fetch("/api/trades/quotes", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const quotes = await res.json();

    if (quotes.XAUUSD && quotes.XAUUSD.ask) {
      document.getElementById("ticker-gold").textContent = quotes.XAUUSD.ask.toLocaleString(undefined, {minimumFractionDigits: 2});
    }
    if (quotes.EURUSD && quotes.EURUSD.ask) {
      document.getElementById("ticker-eur").textContent = quotes.EURUSD.ask.toFixed(5);
    }
    if (quotes.US30 && quotes.US30.ask) {
      document.getElementById("ticker-us30").textContent = quotes.US30.ask.toLocaleString(undefined, {minimumFractionDigits: 1});
    }
    if (quotes.BTCUSD && quotes.BTCUSD.ask) {
      document.getElementById("ticker-btc").textContent = quotes.BTCUSD.ask.toLocaleString(undefined, {minimumFractionDigits: 2});
    }
  } catch (err) {
    // Quotes will update once MT5 is active
  }
}

// ==================== DATA LOADERS ====================
async function loadDashboardData() {
  await Promise.all([
    loadStats(),
    loadActivePositions(),
    loadSlaveAccounts(),
    loadMasterAccounts(),
    loadTradeLogs()
  ]);
}

async function loadStats() {
  try {
    const res = await fetch("/api/trades/stats", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const stats = await res.json();

    document.getElementById("stat-followers").textContent = stats.active_followers;
    document.getElementById("stat-master-equity").textContent = `$${stats.master_equity.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    document.getElementById("stat-total-trades").textContent = stats.total_copied_trades;
    document.getElementById("stat-avg-latency").textContent = `${stats.avg_latency_ms} ms`;
    document.getElementById("live-latency").textContent = stats.total_copied_trades > 0 ? `${stats.avg_latency_ms} ms` : "Live";
    
    const rate = stats.total_copied_trades > 0 
      ? Math.round((stats.successful_trades / stats.total_copied_trades) * 100) 
      : 100;
    document.getElementById("stat-success-rate").textContent = `${rate}% Success`;
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

async function loadActivePositions() {
  try {
    const res = await fetch("/api/trades/active", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const trades = await res.json();

    const tbody = document.getElementById("tbody-active-trades");
    const tbodyAll = document.getElementById("tbody-all-active");

    if (trades.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No active open positions.</td></tr>`;
      if (tbodyAll) tbodyAll.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">No active open positions.</td></tr>`;
      return;
    }

    const rows = trades.map(t => `
      <tr>
        <td><strong>#${t.master_ticket}</strong></td>
        <td>#${t.slave_ticket}</td>
        <td><strong>${t.symbol}</strong></td>
        <td><span class="badge ${t.order_type === 'BUY' ? 'badge-info' : 'badge-danger'}">${t.order_type}</span></td>
        <td>${t.volume.toFixed(2)}</td>
        <td>${t.open_price.toFixed(5)}</td>
        <td class="text-muted">${t.created_at ? new Date(t.created_at).toLocaleTimeString() : '--'}</td>
      </tr>
    `).join("");

    tbody.innerHTML = rows;
    if (tbodyAll) {
      tbodyAll.innerHTML = trades.map(t => `
        <tr>
          <td>${t.id}</td>
          <td><strong>#${t.master_ticket}</strong></td>
          <td>#${t.slave_ticket}</td>
          <td><strong>${t.symbol}</strong></td>
          <td><span class="badge ${t.order_type === 'BUY' ? 'badge-info' : 'badge-danger'}">${t.order_type}</span></td>
          <td>${t.volume.toFixed(2)}</td>
          <td>${t.open_price.toFixed(5)}</td>
          <td><span class="badge badge-success">ACTIVE</span></td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load active positions:", err);
  }
}

async function loadSlaveAccounts() {
  try {
    const res = await fetch("/api/accounts/slave", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const accounts = await res.json();

    const tbody = document.getElementById("tbody-slave-accounts");
    if (accounts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No follower accounts added yet. Click 'Add Follower Account' to connect one.</td></tr>`;
      return;
    }

    tbody.innerHTML = accounts.map(a => `
      <tr>
        <td><strong>${a.name}</strong></td>
        <td>${a.login}</td>
        <td class="text-muted">${a.server}</td>
        <td><strong>$${a.balance.toFixed(2)}</strong> / $${a.equity.toFixed(2)}</td>
        <td>
          <span class="badge ${a.status === 'CONNECTED' ? 'badge-success' : 'badge-danger'}">
            ${a.status}
          </span>
        </td>
        <td><span class="badge badge-gold">Cloud 24/7</span></td>
        <td>
          <div style="display: flex; gap: 8px;">
            <button class="btn-sm btn-outline" onclick="openSettingsModal(${a.id})">Risk Settings</button>
            <button class="btn-sm btn-outline" onclick="testAccount(${a.id})">Verify</button>
            <button class="btn-sm btn-danger" onclick="deleteAccount(${a.id})">&times;</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load slave accounts:", err);
  }
}

async function loadMasterAccounts() {
  try {
    const res = await fetch("/api/accounts/master", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const masters = await res.json();

    const tbody = document.getElementById("tbody-master-accounts");
    if (masters.length > 0) {
      document.getElementById("stat-master-login").textContent = `Login: ${masters[0].login} (${masters[0].server})`;
    } else {
      document.getElementById("stat-master-login").textContent = "No Master Connected";
    }

    if (masters.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">No master account registered. Click 'Add Master Account' to register your master MT5 account.</td></tr>`;
      return;
    }

    tbody.innerHTML = masters.map(m => `
      <tr>
        <td><strong>${m.name}</strong></td>
        <td>${m.login}</td>
        <td class="text-muted">${m.broker || m.server}</td>
        <td>$${m.balance.toFixed(2)}</td>
        <td><strong>$${m.equity.toFixed(2)}</strong></td>
        <td><span class="badge badge-success">ACTIVE</span></td>
        <td><span class="text-gold">Primary Master</span></td>
        <td>
          <button class="btn-sm btn-danger" onclick="deleteMasterAccount(${m.id})">&times;</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load master accounts:", err);
  }
}

async function loadTradeLogs() {
  try {
    const res = await fetch("/api/trades/logs?limit=30", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById("tbody-trade-logs");
    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted py-4">No execution logs recorded yet. Trades will appear here when the Master executes an order.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => `
      <tr>
        <td class="text-muted">${new Date(l.timestamp).toLocaleTimeString()}</td>
        <td>#${l.master_ticket || '--'}</td>
        <td>#${l.slave_ticket || '--'}</td>
        <td><span class="badge ${l.action === 'OPEN' ? 'badge-info' : l.action === 'CLOSE' ? 'badge-warning' : 'badge-danger'}">${l.action}</span></td>
        <td><strong>${l.symbol}</strong></td>
        <td>${l.master_lot ? l.master_lot.toFixed(2) : '--'}</td>
        <td><strong>${l.slave_lot ? l.slave_lot.toFixed(2) : '--'}</strong></td>
        <td class="text-emerald">${l.execution_ms.toFixed(1)} ms</td>
        <td>${l.slippage_pips.toFixed(1)} pips</td>
        <td><span class="badge ${l.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}">${l.status}</span></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load trade logs:", err);
  }
}

// ==================== FOLLOWER ACCOUNT ACTIONS ====================
function openAddAccountModal() {
  document.getElementById("modal-add-account").classList.add("show");
}

function closeAddAccountModal() {
  document.getElementById("modal-add-account").classList.remove("show");
}

async function submitAddAccount(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-save-account");
  btn.disabled = true;
  btn.textContent = "Verifying MT5...";

  const payload = {
    name: document.getElementById("acc-name").value,
    login: parseInt(document.getElementById("acc-login").value),
    password: document.getElementById("acc-password").value,
    server: document.getElementById("acc-server").value
  };

  try {
    const res = await fetch("/api/accounts/slave", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeAddAccountModal();
      document.getElementById("form-add-account").reset();
      loadSlaveAccounts();
      loadStats();
    } else {
      const err = await res.json();
      alert("Verification Notice: " + (err.detail || "Could not register account. Ensure MT5 terminal is reachable."));
    }
  } catch (err) {
    alert("Connection error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="check"></i> Connect & Verify Account`;
    if (window.lucide) lucide.createIcons();
  }
}

async function testAccount(id) {
  try {
    const res = await fetch(`/api/accounts/slave/${id}/test`, {
      method: "POST",
      headers: getAuthHeaders()
    });
    const data = await res.json();
    alert(`MT5 Account #${id}: ${data.success ? 'CONNECTED (Live Balance: $' + data.balance + ')' : 'FAILED (' + data.error + ')'}`);
    loadSlaveAccounts();
  } catch (e) {
    alert("Test failed: " + e.message);
  }
}

async function deleteAccount(id) {
  if (!confirm("Are you sure you want to disconnect this MT5 follower account?")) return;
  try {
    await fetch(`/api/accounts/slave/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    loadSlaveAccounts();
    loadStats();
  } catch (e) {
    alert("Delete failed: " + e.message);
  }
}

// ==================== MASTER ACCOUNT ACTIONS ====================
function openAddMasterModal() {
  document.getElementById("modal-add-master").classList.add("show");
}

function closeAddMasterModal() {
  document.getElementById("modal-add-master").classList.remove("show");
}

async function submitAddMaster(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-save-master");
  btn.disabled = true;
  btn.textContent = "Connecting Master MT5...";

  const payload = {
    name: document.getElementById("master-name").value,
    login: parseInt(document.getElementById("master-login").value),
    password: document.getElementById("master-password").value || null,
    server: document.getElementById("master-server").value
  };

  try {
    const res = await fetch("/api/accounts/master", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeAddMasterModal();
      document.getElementById("form-add-master").reset();
      loadMasterAccounts();
      loadStats();
    } else {
      const err = await res.json();
      alert("Notice: " + (err.detail || "Failed to register master account"));
    }
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="check"></i> Save Master Account`;
    if (window.lucide) lucide.createIcons();
  }
}

async function deleteMasterAccount(id) {
  if (!confirm("Are you sure you want to remove this Master account?")) return;
  try {
    await fetch(`/api/accounts/master/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    loadMasterAccounts();
    loadStats();
  } catch (e) {
    alert("Delete failed: " + e.message);
  }
}

// ==================== SETTINGS MODAL ====================
async function openSettingsModal(slaveId) {
  document.getElementById("setting-slave-id").value = slaveId;
  try {
    const res = await fetch(`/api/accounts/slave/${slaveId}/settings`, { headers: getAuthHeaders() });
    if (res.ok) {
      const s = await res.json();
      document.getElementById("set-risk-mode").value = s.risk_mode;
      document.getElementById("set-multiplier").value = s.lot_multiplier;
      document.getElementById("set-fixed-lot").value = s.fixed_lot;
      document.getElementById("set-max-lot").value = s.max_lot;
      document.getElementById("set-max-slippage").value = s.max_slippage_pips;
      document.getElementById("set-max-spread").value = s.max_spread_pips;
      document.getElementById("set-copy-sl").checked = s.copy_sl;
      document.getElementById("set-copy-tp").checked = s.copy_tp;
      document.getElementById("set-invert").checked = s.invert_trade;
    }
  } catch (e) {
    console.error(e);
  }
  document.getElementById("modal-settings").classList.add("show");
}

function closeSettingsModal() {
  document.getElementById("modal-settings").classList.remove("show");
}

async function submitSettings(e) {
  e.preventDefault();
  const slaveId = document.getElementById("setting-slave-id").value;
  const payload = {
    risk_mode: document.getElementById("set-risk-mode").value,
    lot_multiplier: parseFloat(document.getElementById("set-multiplier").value),
    fixed_lot: parseFloat(document.getElementById("set-fixed-lot").value),
    max_lot: parseFloat(document.getElementById("set-max-lot").value),
    max_slippage_pips: parseFloat(document.getElementById("set-max-slippage").value),
    max_spread_pips: parseFloat(document.getElementById("set-max-spread").value),
    copy_sl: document.getElementById("set-copy-sl").checked,
    copy_tp: document.getElementById("set-copy-tp").checked,
    invert_trade: document.getElementById("set-invert").checked
  };

  try {
    const res = await fetch(`/api/accounts/slave/${slaveId}/settings`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeSettingsModal();
    } else {
      alert("Failed to update settings");
    }
  } catch (e) {
    alert("Error saving settings: " + e.message);
  }
}
