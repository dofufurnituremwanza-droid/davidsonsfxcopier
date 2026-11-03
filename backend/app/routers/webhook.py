from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas import TradeSignal
from app.engine.copier_engine import CopierEngine

router = APIRouter(prefix="/api/webhook", tags=["Signal Webhook"])

@router.post("/signal")
async def receive_trade_signal(signal: TradeSignal):
    """
    Ingestion endpoint for Master signals sent from DavidsonsFX_Master.mq5 or external provider.
    Executes copier engine in async background pipeline.
    """
    try:
        result = await CopierEngine.process_signal(signal)
        return {"status": "SUCCESS", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process trade signal: {str(e)}")

@router.post("/test-signal")
async def simulate_test_signal(
    symbol: str = "EURUSD",
    order_type: str = "BUY",
    volume: float = 0.1,
    action: str = "OPEN"
):
    """Simulate a test trade signal to verify end-to-end copying without needing a live master."""
    import random
    master_ticket = random.randint(100000, 999999)
    test_signal = TradeSignal(
        action=action,
        master_ticket=master_ticket,
        symbol=symbol,
        order_type=order_type,
        volume=volume,
        price=1.0850,
        sl=1.0800,
        tp=1.0950,
        comment="DavidsonsFX Test Trade"
    )
    result = await CopierEngine.process_signal(test_signal)
    return {
        "status": "SUCCESS",
        "message": f"Simulated test trade #{master_ticket} dispatched successfully",
        "result": result
    }

