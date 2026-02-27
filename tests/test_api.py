"""Tests for ConnectionManager and /ws/live WebSocket endpoint."""
import sys
sys.path.insert(0, "/workspace/AIAlphaPulse2026")

import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Import ConnectionManager from api.main; guard against import-time side effects
# by patching heavy ingestor imports before loading the module.
import importlib


@pytest.fixture
def manager():
    """Fresh ConnectionManager for each test."""
    from api.main import ConnectionManager
    return ConnectionManager()


class TestConnectionManager:
    def test_initial_state_empty(self, manager):
        assert manager.active_connections == []

    @pytest.mark.asyncio
    async def test_connect_adds_websocket(self, manager):
        ws = AsyncMock()
        await manager.connect(ws)
        assert ws in manager.active_connections
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_websocket(self, manager):
        ws = AsyncMock()
        await manager.connect(ws)
        manager.disconnect(ws)
        assert ws not in manager.active_connections

    def test_disconnect_unknown_websocket_is_safe(self, manager):
        ws = AsyncMock()
        # Should not raise even if ws was never connected
        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_broadcast_empty_list_does_not_raise(self, manager):
        """broadcast() on zero connections must not raise."""
        await manager.broadcast({"type": "scores_update", "timestamp": "2026-02-27T12:00:00Z", "scores": []})

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self, manager):
        ws1, ws2 = AsyncMock(), AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)

        payload = {"type": "scores_update", "timestamp": "2026-02-27T12:00:00Z", "scores": []}
        await manager.broadcast(payload)

        expected = json.dumps(payload)
        ws1.send_text.assert_awaited_once_with(expected)
        ws2.send_text.assert_awaited_once_with(expected)

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self, manager):
        """If send_text raises, the dead connection is silently removed."""
        ws_dead = AsyncMock()
        ws_dead.send_text.side_effect = RuntimeError("connection closed")
        ws_alive = AsyncMock()

        await manager.connect(ws_dead)
        await manager.connect(ws_alive)

        payload = {"type": "scores_update", "timestamp": "2026-02-27T12:00:00Z", "scores": []}
        await manager.broadcast(payload)

        assert ws_dead not in manager.active_connections
        ws_alive.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_multiple_connect_disconnect_cycle(self, manager):
        ws1, ws2 = AsyncMock(), AsyncMock()
        await manager.connect(ws1)
        await manager.connect(ws2)
        assert len(manager.active_connections) == 2

        manager.disconnect(ws1)
        assert len(manager.active_connections) == 1
        assert ws2 in manager.active_connections

        manager.disconnect(ws2)
        assert manager.active_connections == []
