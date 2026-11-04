// DAVIDSONSFX TRADING COPIER — Real-Time Production Engine
const API_BASE = (function() {
  if (window.DFX_BACKEND_URL) return window.DFX_BACKEND_URL.replace(/\/$/, '');
  const stored = localStorage.getItem('dfx_backend_url');
  if (stored) return stored.replace(/\/$/, '');
  return '';
})();

function apiUrl(path) {
  if (!path.startsWith('/')) path = '/' + path;
  return API_BASE + path;
}
let ws = null;
let authToken = localStorage.getItem("dfx_token") || "";
let currentUser = null;

document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) lucide.createIcons();
  
  if (authToken) {
    await checkAuthAndLoad();
  } else {
    showView("landing");
  }

  fetchLiveMarketQuotes();
  setInterval(fetchLiveMarketQuotes, 5000);
});

// ==================== VIEW ROUTER ====================
function showView(viewName) {
  document.querySelectorAll(".page-view").forEach(v => v.classList.remove("active"));
  const viewElem = document.getElementById(`view-${viewName}`);
  if (viewElem) viewElem.classList.add("active");
  if (window.lucide) lucide.createIcons();
}

async function checkAuthAndLoad() {
  try {
    const res = await fetch(apiUrl("/api/auth/me", { headers: getAuthHeaders() });
    if (res.ok) {
      currentUser = await res.json();
      setupDashboardForUser(currentUser);
      showView("dashboard");
      initWebSocket();
      loadDashboardData();
    } else {
      logoutUser();
    }
  } catch (err) {
    console.error("Auth check failed:", err);
    showView("landing");
  }
}

function getAuthHeaders() {
  return {
    "Content-Type": "application/json",
    ...(authToken ? { "Authorization": `Bearer ${authToken}` } : {})
  };
}

// ==================== DASHBOARD SETUP BY ROLE ====================
function setupDashboardForUser(user) {
  document.getElementById("user-display-name").textContent = user.username;
  const menuContainer = document.getElementById("nav-menu-container");
  const headerActions = document.getElementById("header-actions-container");
  const roleBadgeText = document.getElementById("role-badge-text");
  const sidebarPillText = document.getElementById("sidebar-pill-text");
  const portalRoleTag = document.getElementById("portal-role-tag");

  if (user.is_admin) {
    // ADMIN DASHBOARD
    roleBadgeText.textContent = "ADMIN";
    sidebarPillText.textContent = "OWNER / ADMIN";
    portalRoleTag.textContent = "ADMINISTRATOR COMMAND CENTER";
    document.getElementById("page-title-text").textContent = "DavidsonsFX Admin Command Center";
    document.getElementById("page-subtitle-text").textContent = "Manage subscriber approvals, master signal providers, and live replication";

    menuContainer.innerHTML = `
      <button class="nav-item active" data-tab="admin-pending">
        <i data-lucide="user-check"></i>
        <span>Pending Approvals</span>
      </button>
      <button class="nav-item" data-tab="admin-followers">
        <i data-lucide="users"></i>
        <span>All Followers</span>
      </button>
      <button class="nav-item" data-tab="admin-master">
        <i data-lucide="award"></i>
        <span>Master Account</span>
      </button>
      <button class="nav-item" data-tab="admin-logs">
        <i data-lucide="activity"></i>
        <span>Execution Audit</span>
      </button>
    `;

    headerActions.innerHTML = `
      <button class="btn btn-secondary" onclick="openAddMasterModal()">
        <i data-lucide="award"></i> Add Master MT5
      </button>
      <button class="btn btn-primary" onclick="openAddAccountModal()">
        <i data-lucide="plus"></i> Add Follower Direct
      </button>
    `;

    setupNavigation();
    switchTab("admin-pending");

  } else {
    // SUBSCRIBER / CLIENT DASHBOARD
    roleBadgeText.textContent = "CLIENT PORTAL";
    sidebarPillText.textContent = "VIP SUBSCRIBER";
    portalRoleTag.textContent = "SUBSCRIBER DASHBOARD";
    document.getElementById("page-title-text").textContent = "My Trading Copier";
    document.getElementById("page-subtitle-text").textContent = "Manage your connected MT5 account and live copied positions";

    menuContainer.innerHTML = `
      <button class="nav-item active" data-tab="client-home">
        <i data-lucide="layout-dashboard"></i>
        <span>My Account</span>
      </button>
    `;

    headerActions.innerHTML = `
      <button class="btn btn-primary" onclick="openAddAccountModal()">
        <i data-lucide="link"></i> Connect MT5 Account
      </button>
    `;

    setupNavigation();
    switchTab("client-home");
  }

  if (window.lucide) lucide.createIcons();
}

function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      navButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
  const activePane = document.getElementById(`tab-${tabId}`);
  if (activePane) activePane.classList.add("active");
}

// ==================== AUTH ACTIONS ====================
function openAuthModal(tab = "login") {
  switchAuthTab(tab);
  document.getElementById("modal-auth").classList.add("show");
  if (window.lucide) lucide.createIcons();
}

function closeAuthModal() {
  document.getElementById("modal-auth").classList.remove("show");
}

function switchAuthTab(tab) {
  const isLogin = tab === "login";
  document.getElementById("tab-btn-login").classList.toggle("active", isLogin);
  document.getElementById("tab-btn-register").classList.toggle("active", !isLogin);
  document.getElementById("form-login").style.display = isLogin ? "block" : "none";
  document.getElementById("form-register").style.display = !isLogin ? "block" : "none";
  document.getElementById("auth-modal-title").textContent = isLogin ? "Client Sign In" : "Create Subscriber Account";
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-login-submit");
  btn.disabled = true;
  btn.textContent = "Signing In...";

  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;

  try {
    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    const res = await fetch(apiUrl("/api/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("dfx_token", authToken);
      closeAuthModal();
      await checkAuthAndLoad();
    } else {
      const err = await res.json();
      alert("Sign In Failed: " + (err.detail || "Invalid credentials"));
    }
  } catch (err) {
    alert("Connection Error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Sign In to Dashboard";
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-register-submit");
  btn.disabled = true;
  btn.textContent = "Creating Account...";

  const payload = {
    full_name: document.getElementById("reg-fullname").value,
    email: document.getElementById("reg-email").value,
    username: document.getElementById("reg-username").value,
    phone: document.getElementById("reg-phone").value,
    telegram: document.getElementById("reg-telegram").value,
    password: document.getElementById("reg-password").value
  };

  try {
    const res = await fetch(apiUrl("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      const data = await res.json();
      authToken = data.access_token;
      localStorage.setItem("dfx_token", authToken);
      closeAuthModal();
      await checkAuthAndLoad();
    } else {
      const err = await res.json();
      alert("Registration Failed: " + (err.detail || "Error creating account"));
    }
  } catch (err) {
    alert("Error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Create Account & Proceed";
  }
}

function logoutUser() {
  authToken = "";
  currentUser = null;
  localStorage.removeItem("dfx_token");
  if (ws) ws.close();
  showView("landing");
}

// ==================== WEBSOCKET ====================
function initWebSocket() {
  let wsUrl;
  if (API_BASE) {
    const wsProto = API_BASE.startsWith('https') ? 'wss:' : 'ws:';
    const host = API_BASE.replace(/^https?:\/\//, '');
    wsUrl = `${wsProto}//${host}/ws`;
  } else {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    wsUrl = `${protocol}//${window.location.host}/ws`;
  }

  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    const pulse = document.getElementById("ws-pulse");
    if (pulse) pulse.style.backgroundColor = "#10b981";
    const text = document.getElementById("ws-status-text");
    if (text) text.textContent = "Cloud Relay Live";
  };
  ws.onmessage = () => {
    loadDashboardData();
  };
  ws.onclose = () => {
    const pulse = document.getElementById("ws-pulse");
    if (pulse) pulse.style.backgroundColor = "#f43f5e";
    setTimeout(initWebSocket, 4000);
  };
}

// ==================== DATA LOADERS ====================
async function loadDashboardData() {
  if (!currentUser) return;

  if (currentUser.is_admin) {
    await Promise.all([
      loadPendingAccounts(),
      loadAdminFollowers(),
      loadAdminMasters(),
      loadTradeLogs()
    ]);
  } else {
    await Promise.all([
      loadClientAccountView(),
      loadActivePositions()
    ]);
  }
}

// ==================== CLIENT SPECIFIC DATA ====================
async function loadClientAccountView() {
  try {
    const res = await fetch(apiUrl("/api/accounts/slave", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const accounts = await res.json();

    const pendingBanner = document.getElementById("client-pending-banner");
    const activeBanner = document.getElementById("client-active-banner");
    const detailsContainer = document.getElementById("client-account-details");
    const statusPill = document.getElementById("client-status-pill");
    const connectBtn = document.getElementById("btn-client-connect");

    if (accounts.length === 0) {
      pendingBanner.style.display = "none";
      activeBanner.style.display = "none";
      statusPill.textContent = "Not Connected";
      statusPill.className = "text-muted";
      connectBtn.style.display = "inline-flex";
      detailsContainer.innerHTML = `
        <div style="padding: 30px; text-align: center;">
          <i data-lucide="shield-alert" style="width: 48px; height: 48px; color: var(--gold-400); margin-bottom: 12px;"></i>
          <h4 style="font-size: 1.1rem; margin-bottom: 6px;">No MT5 Account Linked Yet</h4>
          <p class="text-muted" style="max-width: 400px; margin: 0 auto 18px;">Connect your MetaTrader 5 account and provide your payment reference to start copying.</p>
          <button class="btn btn-primary" onclick="openAddAccountModal()">
            <i data-lucide="plus"></i> Connect MT5 Trading Account
          </button>
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    const acc = accounts[0];
    connectBtn.style.display = "none";

    if (!acc.is_approved) {
      pendingBanner.style.display = "flex";
      activeBanner.style.display = "none";
      statusPill.textContent = "Pending Admin Approval";
      statusPill.className = "text-gold";
    } else {
      pendingBanner.style.display = "none";
      activeBanner.style.display = "flex";
      statusPill.textContent = "Live & Approved";
      statusPill.className = "text-emerald";
    }

    detailsContainer.innerHTML = `
      <div class="risk-info-list">
        <div class="risk-info-item">
          <span>Account Label:</span>
          <strong>${acc.name}</strong>
        </div>
        <div class="risk-info-item">
          <span>MT5 Login:</span>
          <strong class="text-gold">#${acc.login}</strong>
        </div>
        <div class="risk-info-item">
          <span>Broker Server:</span>
          <strong>${acc.server}</strong>
        </div>
        <div class="risk-info-item">
          <span>Live Balance / Equity:</span>
          <strong>$${acc.balance.toFixed(2)} / $${acc.equity.toFixed(2)} ${acc.currency}</strong>
        </div>
        <div class="risk-info-item">
          <span>Payment Reference:</span>
          <code>${acc.payment_reference || 'N/A'} (${acc.payment_method || 'M-Pesa'})</code>
        </div>
        <div class="risk-info-item">
          <span>Approval Status:</span>
          <span class="badge ${acc.is_approved ? 'badge-success' : 'badge-gold'}">
            ${acc.approval_status}
          </span>
        </div>
      </div>
    `;

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error("Failed to load client account:", err);
  }
}

// ==================== ADMIN SPECIFIC DATA ====================
async function loadPendingAccounts() {
  try {
    const res = await fetch(apiUrl("/api/accounts/pending", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const pending = await res.json();

    const tbody = document.getElementById("tbody-admin-pending");
    if (pending.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">No pending accounts in queue. All subscribers are approved!</td></tr>`;
      return;
    }

    tbody.innerHTML = pending.map(a => `
      <tr>
        <td><strong>${a.name}</strong></td>
        <td><strong>#${a.login}</strong></td>
        <td class="text-muted">${a.server}</td>
        <td><span class="badge badge-gold">${a.payment_method || 'M-Pesa'}</span></td>
        <td><code>${a.payment_reference || 'Awaiting'}</code></td>
        <td>${a.telegram_handle || '--'}</td>
        <td>$${a.balance.toFixed(2)}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn-sm btn-success" onclick="approveAccount(${a.id})">
              <i data-lucide="check"></i> Approve & Connect
            </button>
            <button class="btn-sm btn-danger" onclick="rejectAccount(${a.id})">
              &times; Reject
            </button>
          </div>
        </td>
      </tr>
    `).join("");

    if (window.lucide) lucide.createIcons();

  } catch (err) {
    console.error("Failed to load pending accounts:", err);
  }
}

async function approveAccount(id) {
  if (!confirm("Confirm payment received and approve this MT5 subscriber account for live copying?")) return;
  try {
    const res = await fetch(apiUrl(`/api/accounts/slave/${id}/approve`, {
      method: "POST",
      headers: getAuthHeaders()
    });
    if (res.ok) {
      alert("Subscriber account approved and connected to Master!");
      loadPendingAccounts();
      loadAdminFollowers();
    } else {
      alert("Error approving account");
    }
  } catch (e) {
    alert("Approval error: " + e.message);
  }
}

async function rejectAccount(id) {
  if (!confirm("Are you sure you want to reject this subscriber's application?")) return;
  try {
    const res = await fetch(apiUrl(`/api/accounts/slave/${id}/reject`, {
      method: "POST",
      headers: getAuthHeaders()
    });
    if (res.ok) {
      alert("Account rejected.");
      loadPendingAccounts();
      loadAdminFollowers();
    }
  } catch (e) {
    alert("Reject error: " + e.message);
  }
}

async function loadAdminFollowers() {
  try {
    const res = await fetch(apiUrl("/api/accounts/slave", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const accounts = await res.json();

    const tbody = document.getElementById("tbody-admin-followers");
    if (accounts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No follower accounts registered yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = accounts.map(a => `
      <tr>
        <td><strong>${a.name}</strong></td>
        <td>#${a.login}</td>
        <td class="text-muted">${a.server}</td>
        <td>$${a.balance.toFixed(2)} / $${a.equity.toFixed(2)}</td>
        <td>
          <span class="badge ${a.is_approved ? 'badge-success' : 'badge-gold'}">
            ${a.approval_status}
          </span>
        </td>
        <td>
          <span class="badge ${a.status === 'CONNECTED' ? 'badge-success' : 'badge-danger'}">
            ${a.status}
          </span>
        </td>
        <td>
          <div style="display: flex; gap: 6px;">
            <button class="btn-sm btn-outline" onclick="openSettingsModal(${a.id})">Risk</button>
            <button class="btn-sm btn-danger" onclick="deleteAccount(${a.id})">&times;</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load admin followers:", err);
  }
}

async function loadAdminMasters() {
  try {
    const res = await fetch(apiUrl("/api/accounts/master", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const masters = await res.json();

    const tbody = document.getElementById("tbody-admin-master");
    if (masters.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No master registered. Click 'Register Master MT5' to add one.</td></tr>`;
      return;
    }

    tbody.innerHTML = masters.map(m => `
      <tr>
        <td><strong>${m.name}</strong></td>
        <td>#${m.login}</td>
        <td class="text-muted">${m.server}</td>
        <td>$${m.balance.toFixed(2)}</td>
        <td><strong>$${m.equity.toFixed(2)}</strong></td>
        <td><span class="badge badge-success">ACTIVE</span></td>
        <td>
          <button class="btn-sm btn-danger" onclick="deleteMasterAccount(${m.id})">&times;</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load masters:", err);
  }
}

async function loadActivePositions() {
  try {
    const res = await fetch(apiUrl("/api/trades/active", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const trades = await res.json();

    const tbody = document.getElementById("tbody-client-trades");
    if (!tbody) return;

    if (trades.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No active open positions.</td></tr>`;
      return;
    }

    tbody.innerHTML = trades.map(t => `
      <tr>
        <td>#${t.slave_ticket}</td>
        <td><strong>${t.symbol}</strong></td>
        <td><span class="badge ${t.order_type === 'BUY' ? 'badge-info' : 'badge-danger'}">${t.order_type}</span></td>
        <td>${t.volume.toFixed(2)}</td>
        <td>${t.open_price.toFixed(5)}</td>
        <td class="text-muted">${t.created_at ? new Date(t.created_at).toLocaleTimeString() : '--'}</td>
        <td><span class="badge badge-success">ACTIVE</span></td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Failed to load active positions:", err);
  }
}

async function loadTradeLogs() {
  try {
    const res = await fetch(apiUrl("/api/trades/logs?limit=30", { headers: getAuthHeaders() });
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById("tbody-trade-logs");
    if (!tbody) return;

    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted py-4">No trade logs recorded yet.</td></tr>`;
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

// ==================== LIVE MARKET QUOTES (GOLD FOCUSED) ====================
async function fetchLiveMarketQuotes() {
  try {
    const res = await fetch(apiUrl("/api/trades/quotes"), { headers: getAuthHeaders() });
    if (!res.ok) return;
    const quotes = await res.json();

    if (quotes.XAUUSD && quotes.XAUUSD.ask) {
      const q = quotes.XAUUSD.ask.toLocaleString(undefined, {minimumFractionDigits: 2});
      const el1 = document.getElementById("ticker-gold");
      const el2 = document.getElementById("landing-gold");
      if (el1) el1.textContent = q;
      if (el2) el2.textContent = q;

      const elSpread = document.getElementById("landing-gold-spread");
      if (elSpread && quotes.XAUUSD.bid) {
        const spreadPips = ((quotes.XAUUSD.ask - quotes.XAUUSD.bid) * 10).toFixed(1);
        elSpread.textContent = spreadPips + " Pips";
      }
    }
  } catch (e) {}
}

// ==================== FOLLOWER ACCOUNT MODAL ====================
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
    server: document.getElementById("acc-server").value,
    payment_method: document.getElementById("acc-payment-method").value,
    payment_reference: document.getElementById("acc-payment-ref").value,
    telegram_handle: document.getElementById("acc-telegram").value
  };

  try {
    const res = await fetch(apiUrl("/api/accounts/slave", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeAddAccountModal();
      document.getElementById("form-add-account").reset();
      alert("Your MT5 account has been submitted! It is now pending approval by DavidsonsFX Admin.");
      loadDashboardData();
    } else {
      const err = await res.json();
      alert("Verification Notice: " + (err.detail || "Could not connect account. Ensure login and server are correct."));
    }
  } catch (err) {
    alert("Connection error: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="send"></i> Submit Account for Approval`;
    if (window.lucide) lucide.createIcons();
  }
}

async function deleteAccount(id) {
  if (!confirm("Are you sure you want to remove this account?")) return;
  try {
    await fetch(apiUrl(`/api/accounts/slave/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    loadDashboardData();
  } catch (e) {
    alert("Delete failed: " + e.message);
  }
}

// ==================== MASTER ACCOUNT MODAL ====================
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
    const res = await fetch(apiUrl("/api/accounts/master", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      closeAddMasterModal();
      document.getElementById("form-add-master").reset();
      loadAdminMasters();
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
  if (!confirm("Are you sure you want to delete this master account?")) return;
  try {
    await fetch(apiUrl(`/api/accounts/master/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });
    loadAdminMasters();
  } catch (e) {
    alert("Delete failed: " + e.message);
  }
}

// ==================== RISK SETTINGS MODAL ====================
async function openSettingsModal(slaveId) {
  document.getElementById("setting-slave-id").value = slaveId;
  try {
    const res = await fetch(apiUrl(`/api/accounts/slave/${slaveId}/settings`, { headers: getAuthHeaders() });
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
    const res = await fetch(apiUrl(`/api/accounts/slave/${slaveId}/settings`, {
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
