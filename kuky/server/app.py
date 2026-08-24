"""aiohttp server: MJPEG stream + WebSocket control + mDNS advertisement."""

import asyncio
import json
import logging
import socket
import time
from typing import Callable, Optional

import cv2
import numpy as np
from aiohttp import web, WSMsgType

log = logging.getLogger(__name__)

_BOUNDARY = b"frame"
_MAX_STREAM_FPS = 8


class RobotServer:
    """
    Exposes two endpoints:
      GET /stream  — multipart MJPEG stream with segmentation overlay
      GET /ws      — WebSocket for bidirectional control + telemetry
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        self._host = host
        self._port = port

        self._app = web.Application()
        self._app.router.add_get("/stream", self._stream_handler)
        self._app.router.add_get("/ws", self._ws_handler)

        # Latest annotated JPEG shared between the vision thread and stream clients
        self._latest_jpeg: Optional[bytes] = None
        self._frame_event = asyncio.Event()

        # Connected WebSocket clients
        self._ws_clients: set[web.WebSocketResponse] = set()

        # Shared control state (read by the robot loop)
        self.mode: str = "auto"          # "manual" | "auto"
        self.manual_dir: str = "stop"    # "forward"|"backward"|"left"|"right"|"stop"
        self.manual_speed: float = 1.0

        # Optional callback invoked on every control message
        self._on_command: Optional[Callable[[str, str], None]] = None

    # ------------------------------------------------------------------
    # Public API called by the robot loop
    # ------------------------------------------------------------------

    def set_command_callback(self, cb: Callable[[str, str], None]) -> None:
        """cb(mode, direction) is called whenever the client sends a command."""
        self._on_command = cb

    def push_jpeg(self, jpeg: bytes) -> None:
        """Called from the vision thread to publish a new annotated frame."""
        self._latest_jpeg = jpeg
        # Signal async waiters from a non-async context safely
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(self._frame_event.set)
        except RuntimeError:
            pass

    async def broadcast_telemetry(self, data: dict) -> None:
        msg = json.dumps({"type": "telemetry", **data})
        dead: set[web.WebSocketResponse] = set()
        for ws in self._ws_clients:
            try:
                await ws.send_str(msg)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        await site.start()
        log.info("Server listening on %s:%d", self._host, self._port)
        asyncio.create_task(self._advertise_mdns())

    # ------------------------------------------------------------------
    # MJPEG stream handler
    # ------------------------------------------------------------------

    async def _stream_handler(self, request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={
            "Content-Type": f"multipart/x-mixed-replace; boundary={_BOUNDARY.decode()}",
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        })
        await response.prepare(request)
        min_interval = 1.0 / _MAX_STREAM_FPS
        last_sent = 0.0

        try:
            while True:
                await self._frame_event.wait()
                self._frame_event.clear()
                jpeg = self._latest_jpeg
                if jpeg is None:
                    continue

                now = time.monotonic()
                if now - last_sent < min_interval:
                    continue
                last_sent = now

                header = (
                    b"--" + _BOUNDARY + b"\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                )
                await response.write(header + jpeg + b"\r\n")
        except (ConnectionResetError, asyncio.CancelledError):
            pass

        return response

    # ------------------------------------------------------------------
    # WebSocket control handler
    # ------------------------------------------------------------------

    async def _ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.add(ws)

        # Send current state immediately on connect
        await ws.send_str(json.dumps({
            "type": "state",
            "mode": self.mode,
            "dir": self.manual_dir,
            "speed": self.manual_speed,
        }))

        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")
                if msg_type == "move":
                    self.manual_dir = data.get("dir", "stop")
                    if self._on_command:
                        self._on_command(self.mode, self.manual_dir)
                elif msg_type == "mode":
                    self.mode = data.get("value", "auto")
                    if self._on_command:
                        self._on_command(self.mode, self.manual_dir)
                elif msg_type == "speed":
                    raw = data.get("value", 1.0)
                    if isinstance(raw, (int, float)):
                        self.manual_speed = float(max(0.0, min(1.0, raw)))
        finally:
            self._ws_clients.discard(ws)

        return ws

    # ------------------------------------------------------------------
    # mDNS / Bonjour advertisement
    # ------------------------------------------------------------------

    async def _advertise_mdns(self) -> None:
        try:
            from zeroconf.asyncio import AsyncZeroconf
            from zeroconf import ServiceInfo

            ip = _local_ip()
            info = ServiceInfo(
                "_http._tcp.local.",
                "kuky._http._tcp.local.",
                addresses=[socket.inet_aton(ip)],
                port=self._port,
                properties={"path": "/"},
                server="kuky.local.",
            )
            zc = AsyncZeroconf()
            await zc.async_register_service(info)
            log.info("mDNS: kuky.local advertised at %s:%d", ip, self._port)
        except Exception as exc:
            log.warning("mDNS registration skipped: %s", exc)


def _local_ip() -> str:
    """Return the machine's outward-facing LAN IP (best effort)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
