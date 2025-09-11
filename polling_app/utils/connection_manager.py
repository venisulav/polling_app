import asyncio
from typing import Dict, List, Set

from fastapi import WebSocket
from sqlalchemy.orm import Session

from polling_app import constants as C
from polling_app.utils.ws_helpers import send_error, send_success

from .. import crud, models
from ..database import SessionLocal


class ConnectionManager:
    """Manages WebSocket connections for real-time poll updates."""

    def __init__(self):
        # Maps poll_id to list of WebSocket connections
        self._connections: Dict[str, List[WebSocket]] = {}
        # Maps WebSocket to set of subscribed poll_ids for cleanup
        self._subscriptions: Dict[WebSocket, Set[str]] = {}

    def poll_exists(self, poll_id: str) -> bool:
        """Check if a poll exists in the database."""
        db: Session = SessionLocal()
        try:
            return (
                db.query(models.Poll).filter(models.Poll.id == poll_id).first()
                is not None
            )
        finally:
            db.close()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self._subscriptions[websocket] = set()
        await send_success(websocket, C.ACTION_CONNECT, {"message": "connected"})

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection and cleanup all subscriptions."""
        if websocket in self._subscriptions:
            subscribed_polls = self._subscriptions[websocket].copy()
            for poll_id in subscribed_polls:
                await self._unsubscribe_from_poll(websocket, poll_id)
            del self._subscriptions[websocket]
        await send_success(websocket, C.ACTION_DISCONNECT)
        await websocket.close()

    async def subscribe_to_poll(
        self, websocket: WebSocket, poll_id: str, db: Session
    ) -> bool:
        """Subscribe a WebSocket to a specific poll's updates."""
        # Check if poll exists
        if not self.poll_exists(poll_id):
            await send_error(
                websocket, C.ERR_POLL_NOT_FOUND, f"Poll {poll_id} does not exist"
            )
            return False

        # Check if already subscribed
        if (
            websocket in self._subscriptions
            and poll_id in self._subscriptions[websocket]
        ):
            await send_error(
                websocket, C.ERR_ALREADY_SUBSCRIBED, f"Already subscribed to {poll_id}"
            )
            return False

        # Add connection to poll
        if poll_id not in self._connections:
            self._connections[poll_id] = []
        self._connections[poll_id].append(websocket)

        # Track subscription for this websocket
        if websocket not in self._subscriptions:
            self._subscriptions[websocket] = set()
        self._subscriptions[websocket].add(poll_id)

        # Send current poll results
        results = crud.get_poll_results(db, poll_id)
        await send_success(
            websocket, C.ACTION_SUBSCRIBE, {"poll_id": poll_id, "results": results}
        )
        return True

    async def unsubscribe_from_poll(self, websocket: WebSocket, poll_id: str) -> bool:
        """Unsubscribe a WebSocket from a specific poll's updates."""
        if (
            websocket not in self._subscriptions
            or poll_id not in self._subscriptions[websocket]
        ):
            await send_error(
                websocket, C.ERR_NOT_SUBSCRIBED, f"Not subscribed to {poll_id}"
            )
            return False

        await self._unsubscribe_from_poll(websocket, poll_id)
        await send_success(websocket, C.ACTION_UNSUBSCRIBE, {"poll_id": poll_id})
        return True

    async def _unsubscribe_from_poll(self, websocket: WebSocket, poll_id: str) -> None:
        """Internal method to unsubscribe without sending response."""
        # Remove from connections
        if poll_id in self._connections and websocket in self._connections[poll_id]:
            self._connections[poll_id].remove(websocket)
            # Clean up empty poll connection lists
            if not self._connections[poll_id]:
                del self._connections[poll_id]

        # Remove from subscriptions
        if websocket in self._subscriptions:
            self._subscriptions[websocket].discard(poll_id)

    async def broadcast_to_poll(self, poll_id: str, action: str, data: dict) -> None:
        """Broadcast a message to all subscribers of a specific poll."""
        if poll_id not in self._connections:
            return

        # Create tasks for all broadcasts to avoid blocking
        tasks = []
        for websocket in self._connections[
            poll_id
        ].copy():  # Copy to avoid modification during iteration
            task = asyncio.create_task(send_success(websocket, action, data))
            tasks.append(task)

        # Wait for all broadcasts to complete (optional, for error handling)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def cleanup_poll(self, poll_id: str) -> None:
        """Clean up all connections for a deleted poll and notify subscribers."""
        if poll_id not in self._connections:
            return

        websockets = self._connections[poll_id].copy()

        # Notify all subscribers that the poll was deleted
        for websocket in websockets:
            try:
                await send_error(
                    websocket, C.ERR_POLL_DELETED, f"Poll {poll_id} has been deleted"
                )
                # Remove from subscriptions
                if websocket in self._subscriptions:
                    self._subscriptions[websocket].discard(poll_id)
            except Exception:
                # WebSocket might be closed, ignore errors
                pass

        # Remove all connections for this poll
        del self._connections[poll_id]

    def get_connection_count(self, poll_id: str) -> int:
        """Get the number of active connections for a poll."""
        return len(self._connections.get(poll_id, []))

    def get_total_connections(self) -> int:
        """Get the total number of active WebSocket connections."""
        return len(self._subscriptions)

    def get_subscribed_polls(self, websocket: WebSocket) -> Set[str]:
        """Get the set of poll IDs a WebSocket is subscribed to."""
        return self._subscriptions.get(websocket, set()).copy()


# Global connection manager instance
connection_manager = ConnectionManager()
