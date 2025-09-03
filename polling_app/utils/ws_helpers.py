import json
from typing import Any, Optional

from fastapi import WebSocket

from polling_app import constants as C


async def send_error(ws: WebSocket, code: str, message: str):
    await ws.send_text(
        json.dumps({"type": C.TYPE_ERROR, "code": code, "message": message})
    )


async def send_success(
    ws: WebSocket, action: str, payload: Optional[dict[str, Any]] = None
):
    response: dict[str, Any] = {"type": C.TYPE_SUCCESS, "action": action}
    if payload:
        response["data"] = payload
    await ws.send_text(json.dumps(response))
