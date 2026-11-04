# DAVIDSONSFX TRADING COPIER — CLIENT & OPERATOR HANDBOOK

**Product:** DAVIDSONSFX TRADING COPIER  
**Version:** 1.0.0 (Cloud / Zero-Install Edition)  
**Deliverable to:** Business Owner / Operations Team  

---

## 1. System Overview

DAVIDSONSFX TRADING COPIER is a centralized cloud copy-trading platform for MetaTrader 5. It allows subscribers to replicate master trades into their personal MT5 trading accounts without downloading software or leaving their devices on.

- **Master Execution:** Sub-millisecond trade capture via `DavidsonsFX_Master.mq5`.
- **Subscriber Onboarding:** 100% web-based (Zero-Install).
- **Latency:** Parallel async dispatch (<35 ms average execution).
- **Security:** Follower credentials encrypted with AES-256 Fernet GCM.

---

## 2. Server Requirements (VPS)

To run the copier 24/7, deploy onto a Windows VPS:
- **OS:** Windows Server 2019 / 2022 or Windows 10/11 Pro 64-bit
- **CPU:** 4 vCPU or higher
- **RAM:** 8 GB RAM (handles 50–200 active accounts)
- **Disk:** 50 GB NVMe/SSD
- **Location:** London (LD4) or New York (NY4) for lowest broker latency

---

## 3. Quick Server Deployment (10 Minutes)

1. **Install Prerequisites on VPS:**
   - Download and install **Python 3.10+** from `python.org` (check **"Add python.exe to PATH"**).
   - Download and install **MetaTrader 5** terminal.

2. **Deploy the Codebase:**
   - Transfer the `DAVIDSON COPIER` folder to `C:\DAVIDSONSFX`.

3. **Install Dependencies:**
   - Open PowerShell as Administrator, navigate to `C:\DAVIDSONSFX`, and run:
     ```powershell
     powershell -ExecutionPolicy Bypass -File scripts\setup_environment.ps1
     ```

4. **Start the Copier Server:**
   - Double-click `scripts\start_davidsonsfx.bat`.
   - Access the dashboard at `http://localhost:8000` (or `http://YOUR_VPS_IP:8000`).

5. **Default Admin Login:**
   - **Username:** `davidsonsfx`
   - **Password:** `davidson2026` *(Please change after first login)*

---

## 4. Master Account Setup (One-Time)

1. Open the Master MT5 Terminal on the trader's PC or VPS.
2. In MT5, go to **Tools -> Options -> Expert Advisors**:
   - Check **"Allow WebRequest for listed URL"**.
   - Add: `http://YOUR_SERVER_IP:8000` (or your domain e.g. `https://copier.davidsonsfx.com`).
3. Copy `mql5\DavidsonsFX_Master.mq5` into the MT5 `MQL5\Experts\` folder.
4. Open MetaEditor (F4), open the file, and click **Compile**.
5. Attach **DavidsonsFX_Master** to any active chart (e.g. EURUSD).
6. Verify in the MT5 Experts log: `"DavidsonsFX Server connection test SUCCESSFUL!"`.

---

## 5. Subscriber Instructions (How Users Connect)

Send these 4 simple steps to your subscribers:

1. **Visit the Portal:** Open `https://copier.davidsonsfx.com` in any web browser.
2. **Create an Account:** Register with your email and password.
3. **Connect Your MT5 Account:** Click **"Connect MT5 Account"** and provide:
   - Account Name / Label
   - MT5 Account Number (Login)
   - MT5 Master / Trading Password
   - Broker Server Name (e.g. `Exness-Real7`, `ICMarketsSC-Live`)
4. **Choose Your Risk Level:**
   - **Equity Ratio (Recommended):** Matches risk to your balance automatically.
   - **Lot Multiplier:** Scale master lot size (e.g. 1.0x, 0.5x).
   - **Fixed Lot:** Use a constant lot size on every trade.
5. Click **"Connect & Verify Account"**.
   - When the green **CONNECTED** status appears, copying is active 24/7. Your phone or computer can be powered off.

---

## 6. Daily Monitoring & Best Practices

- **Active Trades Tab:** Check to see current positions open on the master and their corresponding follower tickets.
- **Execution Logs Tab:** Review execution latency and slippage in pips.
- **Database Backup:** Back up `backend/davidsonsfx.db` regularly (e.g. weekly).
- **Symbol Differences:** If a subscriber's broker uses non-standard symbols (e.g. `GOLD` instead of `XAUUSD` or suffixes like `EURUSD.r`), the system maps them automatically, or you can customize mappings in the account's Risk Settings modal.

---
*Created by DAVIDSONSFX TRADING COPIER Engineering Team.*

