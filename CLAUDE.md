# Skew Hunter Web App - Implementation Memory

**Created:** 2026-02-04

## Overview

Transformed the terminal-based Python trading engine (`skew_hunter_live.py` - 4719 lines) into a full-stack web application with React dashboard and FastAPI backend.

## Architecture

```
skew-hunter/
├── backend/                 # FastAPI + Python
│   ├── brokers/            # UpstoxAPI, DhanAPI
│   ├── signals/            # Alpha calculations, entry detection
│   ├── trading/            # Trade management, exits, risk
│   ├── execution/          # Order execution (paper/live)
│   ├── utils/              # Config, cache, helpers, session
│   ├── main.py             # FastAPI app + endpoints
│   ├── engine.py           # Async trading engine
│   ├── models.py           # Pydantic models
│   ├── websocket_manager.py
│   ├── run.py              # Entry point
│   └── requirements.txt
├── frontend/               # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/ui/  # Badge, Card, ProgressBar, StatusDot, AnimatedNumber, ConditionRow
│   │   ├── components/layout/ # TopBar
│   │   ├── pages/          # Setup, Dashboard, TradeTracker, History, Settings
│   │   ├── hooks/          # useWebSocket, useEngine
│   │   ├── lib/            # constants, formatters
│   │   ├── App.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── start.py                # Multi-mode launcher
└── CLAUDE.md               # This file
```

## How to Run

```bash
# Install backend deps
cd skew-hunter/backend
pip install -r requirements.txt

# Install frontend deps
cd ../frontend
npm install

# Build frontend
npm run build

# Run server
cd ../backend
py run.py
```

**Access:** http://localhost:8000

## Key Features

### Backend (FastAPI)
- **WebSocket** `/ws/live` - Real-time state streaming
- **REST API:**
  - `POST /api/validate-token` - Validate Upstox token
  - `POST /api/engine/start` - Start trading engine
  - `POST /api/engine/stop` - Stop engine
  - `POST /api/trade/exit` - Manual exit
  - `POST /api/mode/cycle` - Cycle STRICT/BALANCED/RELAXED
  - `GET /api/config` - Get config
  - `POST /api/config` - Update config
  - `GET /api/trades` - Trade history
  - `GET /api/state` - Current state (fallback)

### Frontend (React)
- **Setup Wizard** - Token validation, config, execution mode
- **Dashboard** - Live signals, PCR, OI flow, confluence factors
- **Trade Tracker** - P&L, trailing stop, exit button
- **History** - Trade table with filters
- **Settings** - All config parameters

### Design System (Tailwind)
```js
colors: {
  background: '#09090B',
  card: '#111113',
  border: '#1E1E22',
  primary: '#FAFAFA',
  secondary: '#71717A',
  profit: '#22C55E',
  loss: '#EF4444',
  warning: '#F59E0B'
}
fonts: ['Inter', 'JetBrains Mono']
```

## Important Files

| File | Purpose |
|------|---------|
| `backend/run.py` | Start server with `py run.py` |
| `backend/engine.py` | Main trading loop, state broadcast |
| `backend/main.py` | FastAPI routes + static file serving |
| `backend/utils/cache.py` | DataCache with disk persistence |
| `frontend/src/hooks/useWebSocket.ts` | WebSocket connection + reconnect |
| `frontend/src/hooks/useEngine.ts` | API hooks for engine control |

## Import Fix (Critical)

Backend uses **absolute imports** (not relative) for cross-package references:
```python
# Correct
from utils.cache import DataCache
from trading.risk import get_vix_regime

# Wrong (causes ImportError)
from ..utils.cache import DataCache
from .risk import get_vix_regime
```

Files fixed:
- `engine.py`
- `main.py`
- `signals/entry.py`
- `trading/trade.py`
- `utils/helpers.py`

## Cache Persistence

`backend/utils/cache.py` saves to `cache_data.json`:
- `last_spot_price`
- `last_vix`
- `last_atm_strike`
- `pcr_history`
- `price_history`

Loaded on startup via `DataCache.load_from_disk()` in `main.py` lifespan.

## API Data Fetching

- **Always fetch** from Upstox API (even when market closed)
- API returns last closing price after hours
- `is_market_open()` only determines if data is "live" vs "cached"
- VIX defaults to 15.0 if API fails
- Spot price returns None if API fails (falls back to cache)

## Trading Logic Preserved

All signal detection and trade management copied exactly from original:
- Alpha 1/2 calculations
- PCR (contrarian interpretation)
- Confluence factors (6 total)
- VIX-adaptive trailing stops (Golden Rule)
- BUYING vs WRITING signal paths
- Priority-based exit system

## Session State

`session_state.json` stores:
- `trades_today`
- `daily_pnl`
- `peak_session_mtm`
- `active_trade` (for crash recovery)

## Known Issues / TODOs

1. **Token not persisted** - Must re-enter after server restart
2. **No price chart** - TradingView integration pending
3. **Cache empty on first run** - Need market hours to populate

## Keyboard Shortcuts

| Key | Action | Where |
|-----|--------|-------|
| M | Cycle mode | Dashboard (no active trade) |
| E | Exit trade | Trade Tracker |
| Escape | Close modal | Trade Tracker |

## Dependencies

### Backend
```
fastapi>=0.100.0
uvicorn>=0.23.0
websockets>=11.0
pydantic>=2.0
requests>=2.28.0
numpy>=1.24.0
openpyxl>=3.1.0
python-multipart>=0.0.6
```

### Frontend
```
react@18
react-router-dom@6
framer-motion@10
lucide-react
tailwindcss@3
typescript@5
vite@5
clsx
```
