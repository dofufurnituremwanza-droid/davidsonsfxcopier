import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import User, MasterAccount
from app.security import get_password_hash
from app.routers import auth, accounts, trades, webhook
from app.ws.connection_manager import ws_manager

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Seed default admin & master if not exists
def seed_initial_data():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@davidsonsfx.com",
                hashed_password=get_password_hash("admin1234"),
                is_admin=True
            )
            db.add(admin)
            db.commit()
            print("[DavidsonsFX] Default admin account seeded: admin / admin1234")

        master = db.query(MasterAccount).first()
        if not master:
            master = MasterAccount(
                name="DavidsonsFX Master Primary",
                login=99887766,
                server="MetaQuotes-Demo",
                broker="MetaQuotes Software Corp.",
                balance=25000.0,
                equity=25000.0,
                currency="USD"
            )
            db.add(master)
            db.commit()
            print("[DavidsonsFX] Default master account seeded.")
    finally:
        db.close()

seed_initial_data()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="High-Speed Cloud MetaTrader 5 Copier System"
)

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(trades.router)
app.include_router(webhook.router)

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Respond to ping or client echo
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        ws_manager.disconnect(websocket)

# Mount Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_dashboard():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/api/health")
def health_check():
    return {
        "status": "ONLINE",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mt5_ready": True
    }

