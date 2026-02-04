"""WebSocket connection manager for real-time state broadcasting."""

import asyncio
import json
from typing import List, Dict, Any
from fastapi import WebSocket


class WebSocketManager:
    """Manages WebSocket connections and broadcasts state updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        print(f"WebSocket client connected. Total: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        print(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients (parallel for low latency)."""
        if not self.active_connections:
            return

        # Serialize once
        data = json.dumps(message, separators=(',', ':'))  # Compact JSON

        # Send to all connections in parallel for lower latency
        async def send_to_client(connection: WebSocket):
            try:
                await connection.send_text(data)
                return None
            except Exception:
                return connection

        # Run all sends concurrently
        results = await asyncio.gather(
            *[send_to_client(conn) for conn in self.active_connections],
            return_exceptions=True
        )

        # Remove dead connections
        dead_connections = [r for r in results if r is not None and not isinstance(r, Exception)]
        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    if dead in self.active_connections:
                        self.active_connections.remove(dead)

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Failed to send personal message: {e}")

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
