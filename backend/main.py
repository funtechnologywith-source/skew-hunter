"""FastAPI backend for Skew Hunter web application."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from models import (
    TokenValidationRequest, TokenValidationResponse,
    DhanValidationRequest,
    EngineStartRequest, EngineStatusResponse,
    ModeChangeRequest, ConfigUpdateRequest,
    SessionStatsResponse, OrphanCheckResponse, OrphanActionRequest,
    TradeResponse
)
from websocket_manager import WebSocketManager
from engine import SkewHunterEngine
from brokers import UpstoxAPI, DhanAPI
from utils import load_config, save_config, load_session_state, DataCache


# ═══════════════════════════════════════════════════════════════════════════════
# App Initialization
# ═══════════════════════════════════════════════════════════════════════════════

# Global state
ws_manager = WebSocketManager()
engine: Optional[SkewHunterEngine] = None
engine_task: Optional[asyncio.Task] = None
config = load_config("config.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("Skew Hunter API starting...")
    DataCache.load_from_disk()
    yield
    # Shutdown
    global engine, engine_task
    if engine:
        await engine.stop()
    if engine_task:
        engine_task.cancel()
        try:
            await engine_task
        except asyncio.CancelledError:
            pass
    print("Skew Hunter API stopped")


app = FastAPI(
    title="Skew Hunter API",
    description="NIFTY 50 Options Trading Engine",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════════
# REST API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engine_running": engine is not None and engine.running,
        "ws_clients": ws_manager.get_connection_count()
    }


@app.post("/api/validate-token", response_model=TokenValidationResponse)
async def validate_token(request: TokenValidationRequest):
    """Validate Upstox access token."""
    api = UpstoxAPI(request.token)
    valid, result = api.validate_token()

    if valid:
        return TokenValidationResponse(
            valid=True,
            user_name=result,
            message="Token validated successfully"
        )
    else:
        return TokenValidationResponse(
            valid=False,
            user_name=None,
            message=result
        )


@app.post("/api/validate-dhan")
async def validate_dhan(request: DhanValidationRequest):
    """Validate DHAN credentials and load security IDs."""
    api = DhanAPI(request.access_token, request.client_id)
    loaded = api.load_security_ids(request.expiry)

    if loaded:
        return {
            "valid": True,
            "message": f"DHAN credentials valid, loaded security IDs for {request.expiry}"
        }
    else:
        return {
            "valid": False,
            "message": "Failed to load DHAN security IDs"
        }


@app.post("/api/engine/start", response_model=EngineStatusResponse)
async def start_engine(request: EngineStartRequest):
    """Start the trading engine."""
    global engine, engine_task, config

    if engine and engine.running:
        raise HTTPException(status_code=400, detail="Engine already running")

    # Validate token first
    upstox_api = UpstoxAPI(request.token)
    valid, result = upstox_api.validate_token()
    if not valid:
        raise HTTPException(status_code=401, detail=f"Invalid token: {result}")

    # Setup DHAN if needed
    dhan_api = None
    if request.broker == "DHAN" and request.dhan_token and request.dhan_client_id:
        dhan_api = DhanAPI(request.dhan_token, request.dhan_client_id)
        expiry = config.get('EXPIRY', '')
        if expiry:
            dhan_api.load_security_ids(expiry)

    # Load current config
    config = load_config("config.json")

    # Create engine
    engine = SkewHunterEngine(
        config=config,
        upstox_api=upstox_api,
        capital=request.capital,
        execution_mode=request.execution_mode,
        broker=request.broker,
        dhan_api=dhan_api,
        ws_manager=ws_manager
    )

    # Start engine in background task
    engine_task = asyncio.create_task(engine.run())

    return EngineStatusResponse(
        running=True,
        mode=config['ACTIVE_MODE'],
        execution_mode=request.execution_mode,
        broker=request.broker,
        trades_today=engine.session_stats['trades_today'],
        daily_pnl=engine.session_stats['daily_pnl']
    )


@app.post("/api/engine/stop")
async def stop_engine():
    """Stop the trading engine gracefully."""
    global engine, engine_task

    if not engine or not engine.running:
        raise HTTPException(status_code=400, detail="Engine not running")

    await engine.stop()

    if engine_task:
        engine_task.cancel()
        try:
            await engine_task
        except asyncio.CancelledError:
            pass

    return {"status": "stopped", "message": "Engine stopped successfully"}


@app.post("/api/trade/exit")
async def request_trade_exit():
    """Request manual trade exit."""
    if not engine or not engine.running:
        raise HTTPException(status_code=400, detail="Engine not running")

    if not engine.active_trade:
        raise HTTPException(status_code=400, detail="No active trade")

    engine.request_exit("manual_exit")
    return {"status": "exit_requested", "message": "Trade exit requested"}


@app.post("/api/trade/emergency-exit")
async def emergency_exit():
    """Request emergency trade exit (immediate market order)."""
    if not engine or not engine.running:
        raise HTTPException(status_code=400, detail="Engine not running")

    if not engine.active_trade:
        raise HTTPException(status_code=400, detail="No active trade")

    engine.request_exit("emergency_stop")
    return {"status": "emergency_exit_requested", "message": "Emergency exit requested"}


@app.post("/api/mode/cycle")
async def cycle_mode():
    """Cycle through trading modes (STRICT -> BALANCED -> RELAXED)."""
    global config

    if not engine:
        raise HTTPException(status_code=400, detail="Engine not initialized")

    if engine.active_trade:
        raise HTTPException(status_code=400, detail="Cannot change mode during active trade")

    # Cycle mode
    mode_order = ['STRICT', 'BALANCED', 'RELAXED']
    current_idx = mode_order.index(config['ACTIVE_MODE'])
    new_mode = mode_order[(current_idx + 1) % len(mode_order)]

    config['ACTIVE_MODE'] = new_mode
    save_config(config, "config.json")
    engine.config = config

    return {"mode": new_mode, "message": f"Mode changed to {new_mode}"}


@app.post("/api/mode/set")
async def set_mode(request: ModeChangeRequest):
    """Set specific trading mode."""
    global config

    if request.mode not in ['STRICT', 'BALANCED', 'RELAXED']:
        raise HTTPException(status_code=400, detail="Invalid mode")

    if engine and engine.active_trade:
        raise HTTPException(status_code=400, detail="Cannot change mode during active trade")

    config['ACTIVE_MODE'] = request.mode
    save_config(config, "config.json")
    if engine:
        engine.config = config

    return {"mode": request.mode, "message": f"Mode set to {request.mode}"}


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    return config


@app.post("/api/config")
async def update_config(request: ConfigUpdateRequest):
    """Update configuration."""
    global config

    # Deep merge the update
    from utils import deep_merge
    deep_merge(config, request.config)
    save_config(config, "config.json")

    if engine:
        engine.config = config

    return {"status": "updated", "config": config}


@app.get("/api/state")
async def get_state():
    """Get current engine state (fallback for WebSocket)."""
    if not engine:
        return {
            "status": "STOPPED",
            "mode": config['ACTIVE_MODE'],
            "execution_mode": "OFF",
            "broker": "UPSTOX",
            "trades_today": 0,
            "daily_pnl": 0.0
        }

    return engine.get_state()


@app.get("/api/trades")
async def get_trades():
    """Get trade history."""
    # Load from session state and trade logger
    session = load_session_state()
    trades = []

    # If engine is running, get closed trades from it
    if engine:
        trades = [t.to_dict() for t in engine.closed_trades]

    return {
        "trades": trades,
        "total_pnl": sum(t.get('pnl_rupees', 0) for t in trades),
        "count": len(trades)
    }


@app.get("/api/session", response_model=SessionStatsResponse)
async def get_session():
    """Get current session statistics."""
    session = load_session_state()

    if engine:
        return SessionStatsResponse(
            trades_today=engine.session_stats['trades_today'],
            daily_pnl=engine.session_stats['daily_pnl'],
            peak_session_mtm=engine.session_stats['peak_session_mtm'],
            max_trades_reached=engine.session_stats.get('max_trades_reached', False),
            capital=engine.capital
        )

    return SessionStatsResponse(
        trades_today=session.get('trades_today', 0),
        daily_pnl=session.get('daily_pnl', 0.0),
        peak_session_mtm=session.get('peak_session_mtm', 0.0),
        max_trades_reached=session.get('max_trades_reached', False),
        capital=100000.0
    )


@app.get("/api/orphan", response_model=OrphanCheckResponse)
async def check_orphan():
    """Check for orphaned positions from crash."""
    session = load_session_state()
    active_trade = session.get('active_trade')

    if active_trade:
        return OrphanCheckResponse(
            has_orphan=True,
            trade_data=active_trade,
            message="Found orphaned trade from previous session"
        )

    return OrphanCheckResponse(
        has_orphan=False,
        trade_data=None,
        message="No orphaned positions found"
    )


@app.post("/api/orphan/recover")
async def recover_orphan(request: OrphanActionRequest):
    """Recover orphaned position."""
    if not engine:
        raise HTTPException(status_code=400, detail="Engine not running")

    if request.action == "RECOVER" and request.trade_data:
        # Reconstruct trade from saved data
        engine.recover_trade(request.trade_data)
        return {"status": "recovered", "message": "Trade recovered successfully"}

    elif request.action == "EXIT":
        # Exit the orphaned position
        if request.trade_data:
            engine.exit_orphan(request.trade_data)
        return {"status": "exited", "message": "Orphan position exited"}

    elif request.action == "IGNORE":
        # Clear the orphan from session state
        from utils import save_session_state
        session = load_session_state()
        session['active_trade'] = None
        save_session_state(session)
        return {"status": "ignored", "message": "Orphan cleared from session"}

    raise HTTPException(status_code=400, detail="Invalid action")


# ═══════════════════════════════════════════════════════════════════════════════
# WebSocket Endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time state streaming."""
    await ws_manager.connect(websocket)

    try:
        # Send initial state
        if engine:
            await ws_manager.send_personal_message(engine.get_state(), websocket)
        else:
            await ws_manager.send_personal_message({
                "status": "STOPPED",
                "mode": config['ACTIVE_MODE'],
                "execution_mode": "OFF",
                "message": "Engine not running"
            }, websocket)

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (ping/pong, commands)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                # Handle client commands if needed
                if data == "ping":
                    await ws_manager.send_personal_message({"type": "pong"}, websocket)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text('{"type": "ping"}')
                except:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════════
# Static File Serving (Production)
# ═══════════════════════════════════════════════════════════════════════════════

# Serve React frontend build in production
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA for all non-API routes."""
        # Skip API routes
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Check if it's a file request
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Return index.html for SPA routing
        return FileResponse(FRONTEND_DIST / "index.html")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
