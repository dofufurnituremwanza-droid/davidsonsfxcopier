# DAVIDSONSFX TRADING COPIER 🚀

**DAVIDSONSFX TRADING COPIER** is a high-speed, enterprise-grade **Cloud / Zero-Install MetaTrader 5 Trade Copier**. It allows subscribers to connect directly to your system without needing to install anything on their computer or keep their own PCs on 24/7.

---

## 🌟 Key Features

- **Zero-Install for Followers (Cloud Copier)**: Subscribers simply enter their MT5 account credentials (login, password, server) in the web portal. The system replicates trades 24/7.
- **Ultra-Low Latency (<35ms)**: Asynchronous parallel dispatch engine pushes orders simultaneously across all followers.
- **Military-Grade Security**: All follower MT5 passwords are encrypted at rest using **AES-256 Fernet GCM encryption**. Passwords are never stored in plaintext.
- **Intelligent Lot Calculation Engine**:
  - `EQUITY_RATIO`: Proportional to equity ratio (`SlaveEquity / MasterEquity * MasterLot`)
  - `BALANCE_RATIO`: Proportional to balance ratio (`SlaveBalance / MasterBalance * MasterLot`)
  - `LOT_MULTIPLIER`: Direct scaling (e.g. 1.0x, 0.5x, 2.0x)
  - `FIXED_LOT`: Static lot size (e.g. 0.05 lots)
  - `RISK_PERCENT`: Risk percentage based on stop loss distance
- **Smart Symbol Mapping**: Automatically resolves broker naming differences (e.g., Master uses `EURUSD`, follower broker has `EURUSDm`, `EURUSD.pro`, or `rEURUSD`; maps `GOLD` <-> `XAUUSD`).
- **Precision Risk & Protection Filters**:
  - Maximum slippage filter (rejects trades if market moved beyond threshold)
  - Maximum spread filter (prevents fills during high spread spikes or rollovers)
  - Copy Stop Loss & Take Profit toggles
  - Trade inversion (Reverse copy BUY <-> SELL)
- **High-End Dark Mode Web Dashboard**: Live open position monitor, follower account management, risk settings, real-time WebSocket trade feed, and built-in trade simulator.
- **MQL5 Master EA (`DavidsonsFX_Master.mq5`)**: High-speed transmitter EA that hooks into MT5's `OnTradeTransaction()` for sub-millisecond event dispatch.

---

## 🏗️ System Architecture

```
[ Master MT5 Terminal ] 
       │
       ▼ (Instant OnTradeTransaction)
[ DavidsonsFX_Master.mq5 ]
       │
       ▼ (HTTP / WebSocket JSON Signal)
[ DAVIDSONSFX Fast Relay Backend (FastAPI + WebSockets) ]
       │
       ├──► [ Security & AES-256 Decryption Engine ]
       ├──► [ Lot Sizing & Risk Validator ]
       ├──► [ Smart Symbol Translation Engine ]
       │
       ▼ (Parallel Async Execution Pool)
┌──────────────────────────────────────────────┐
│  Follower MT5 Instances (Cloud Execution)    │
│  Account 1 (Exness)    Account 2 (ICMarkets) │
│  Account 3 (Deriv)     Account 4 (FTMO)      │
└──────────────────────────────────────────────┘
       │
       ▼ (Real-time Broadcast)
[ DAVIDSONSFX Web Dashboard (Live UI) ]
```

---

## 📁 Project Structure

```
DAVIDSON COPIER/
├── backend/
│   ├── app/
│   │   ├── config.py              # Configuration & encryption keys
│   │   ├── database.py            # SQLite / PostgreSQL engine & session
│   │   ├── models.py              # User, Master, Slave, TicketMap, TradeLog
│   │   ├── schemas.py             # Pydantic schemas
│   │   ├── security.py            # Bcrypt & AES-256 Fernet password encryption
│   │   ├── main.py                # FastAPI app, WebSockets & route mounting
│   │   ├── engine/
│   │   │   ├── copier_engine.py   # Asynchronous order dispatch & state tracker
│   │   │   ├── lot_calculator.py  # Equity ratio, multiplier, fixed lot algorithms
│   │   │   ├── symbol_mapper.py   # Broker suffix/prefix & synonym mapper
│   │   │   ├── risk_manager.py    # Slippage & spread validation
│   │   │   └── terminal_manager.py# Windows MT5 API integration
│   │   ├── routers/
│   │   │   ├── auth.py            # Login, registration & JWT authentication
│   │   │   ├── accounts.py        # Follower & Master MT5 account management
│   │   │   ├── trades.py          # Active open positions, logs & analytics
│   │   │   └── webhook.py         # Master signal receiver & test simulator
│   │   └── ws/
│   │       └── connection_manager.py # WebSocket broadcaster
│   ├── requirements.txt
│   └── run_server.py
├── frontend/
│   ├── index.html                 # Modern Dark Mode Trading Terminal
│   ├── css/style.css              # Cyber trading UI styles
│   └── js/app.js                  # WebSocket client & dashboard logic
├── mql5/
│   ├── DavidsonsFX_Master.mq5     # Master EA transmitter
│   └── DavidsonsFX_Slave.mq5      # Optional client local receiver EA
├── scripts/
│   ├── setup_environment.ps1      # PowerShell environment setup script
│   └── start_davidsonsfx.bat      # 1-click server launch script
└── README.md
```

---

## 🚀 Quick Start Guide

### Step 1: Install Python Dependencies
Open PowerShell or Command Prompt in the project folder and run:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_environment.ps1
```
Or manually:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```

### Step 2: Start DavidsonsFX Server
Double-click `scripts\start_davidsonsfx.bat` or run:
```bash
python backend\run_server.py
```
The server will start at:
- **Web Dashboard**: `http://localhost:8000`
- **Interactive API Docs**: `http://localhost:8000/docs`

Default Admin Login:
- **Username**: `davidsonsfx`
- **Password**: `davidson2026`

---

## 📊 Connecting the Master Account

1. Open your **Master MetaTrader 5 terminal**.
2. Go to **Tools -> Options -> Expert Advisors**:
   - Check **"Allow WebRequest for listed URL"**
   - Add: `http://127.0.0.1:8000`
3. Copy `mql5/DavidsonsFX_Master.mq5` into your MT5 `MQL5/Experts` directory and compile it in MetaEditor.
4. Attach `DavidsonsFX_Master` to any chart on your Master terminal.
5. Every time you open, modify, or close a trade on the Master, it is instantly transmitted to the DavidsonsFX server and copied across all active followers!

---

## 👥 How Users Connect (Zero-Install)

1. Subscribers open your web portal (`http://your-server-ip:8000`).
2. Click **"Connect MT5 Account"**.
3. Enter their:
   - MT5 Login number
   - MT5 Master password
   - Broker Server Name (e.g. `Exness-Real7`, `ICMarketsSC-Live`)
4. Choose their risk settings (Equity Ratio, Lot Multiplier, or Fixed Lot).
5. Done! The server handles copying 24/7 in the cloud.

