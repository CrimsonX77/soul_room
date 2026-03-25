"""
RoomConnector — Drop-in module for any interface to join a Soul Room.

Any application, script, or UI can become a participant in a running 
Soul Room by importing this module and wiring up a response handler.

Usage:
    from soul_room.connector import RoomConnector

    connector = RoomConnector(
        participant_name="Analyst",
        endpoint_port=7711,
        room_url="http://127.0.0.1:7700"
    )

    def my_respond(message, context, participants):
        return my_model.generate(message)

    connector.set_response_handler(my_respond)
    connector.connect()

    # Send messages to the room:
    connector.send_message("I have a thought on this...")

    # Send media to shared gallery:
    connector.send_media("/path/to/image.png", media_type="image")
"""

import asyncio
import json
import logging
import socket
import threading
import time
from typing import Callable, Optional, Tuple

logger = logging.getLogger("RoomConnector")

# Default port range for participant local endpoints
PORT_RANGE_START = 7710
PORT_RANGE_END = 7749


class RoomConnector:
    """
    Connects any interface to a Soul Room server.
    
    Starts a local HTTP endpoint that the room can call to request responses,
    and provides methods to push messages and media to the room.
    """

    def __init__(
        self,
        participant_name: str,
        endpoint_port: int = 0,
        room_url: str = "http://127.0.0.1:7700",
        pfp_path: str = "",
        voice: str = "",
        color: str = "",
        metadata: Optional[dict] = None,
        port_range: Tuple[int, int] = (PORT_RANGE_START, PORT_RANGE_END),
    ):
        """
        Args:
            participant_name: Display name in the room
            endpoint_port: Preferred port for local endpoint (0 = auto-scan)
            room_url: URL of the Soul Room server
            pfp_path: Path to profile picture
            voice: TTS voice identifier
            color: Display color (hex or name)
            metadata: Additional metadata dict (model name, backend, etc.)
            port_range: Range to scan for free ports
        """
        self.name = participant_name
        self.room_url = room_url.rstrip("/")
        self.pfp_path = pfp_path
        self.voice = voice
        self.color = color
        self.metadata = metadata or {}
        self.port_range = port_range

        # Resolve port
        if endpoint_port and not self._is_port_in_use(endpoint_port):
            self.port = endpoint_port
        elif endpoint_port:
            self.port = self._find_free_port(preferred=endpoint_port)
        else:
            self.port = self._find_free_port()

        self._response_handler: Optional[Callable] = None
        self._connected = False
        self._loop = asyncio.new_event_loop()
        self._runner = None

        self._server_thread = threading.Thread(
            target=self._run_local_server,
            daemon=True,
            name=f"RoomConnector-{participant_name}"
        )

    def set_response_handler(self, handler: Callable):
        """
        Set the function that generates responses when the room asks.
        
        Handler signature:
            def respond(message: str, context: str, participants: list) -> str
        
        Return the response string. Return empty string to stay silent.
        Handler can be sync or async.
        """
        self._response_handler = handler

    def connect(self):
        """Register with the room server and start local endpoint."""
        self._server_thread.start()
        time.sleep(0.5)
        self._register()

    def disconnect(self):
        """Unregister from the room."""
        try:
            import requests
            requests.post(
                f"{self.room_url}/api/disconnect",
                json={"name": self.name},
                timeout=3
            )
        except Exception:
            pass
        self._connected = False

    def send_message(self, content: str, media_ref: Optional[str] = None):
        """Push a message to the room."""
        if not self._connected:
            logger.warning(f"{self.name}: not connected, message not sent")
            return
        try:
            import requests
            requests.post(
                f"{self.room_url}/api/message",
                json={
                    "participant": self.name,
                    "content": content,
                    "media": media_ref
                },
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to send message: {e}")

    def send_media(
        self,
        path: str,
        media_type: str = "image",
        metadata: Optional[dict] = None,
        action: str = "append"
    ):
        """Push media to the room's shared display."""
        if not self._connected:
            return
        try:
            import requests
            requests.post(
                f"{self.room_url}/api/media",
                json={
                    "participant": self.name,
                    "path": path,
                    "type": media_type,
                    "metadata": metadata or {},
                    "action": action
                },
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to send media: {e}")

    def get_room_status(self) -> dict:
        """Fetch current room status including all participants."""
        try:
            import requests
            r = requests.get(f"{self.room_url}/api/status", timeout=3)
            return r.json()
        except Exception:
            return {}

    def get_history(self, limit: int = 20) -> list:
        """Fetch conversation history from room."""
        try:
            import requests
            r = requests.get(
                f"{self.room_url}/api/history",
                params={"limit": limit},
                timeout=3
            )
            return r.json().get("history", [])
        except Exception:
            return []

    def is_connected(self) -> bool:
        return self._connected

    # ─────────────────────────────────────────────
    # Port management
    # ─────────────────────────────────────────────

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    def _find_free_port(self, preferred: int = 0) -> int:
        start, end = self.port_range
        if preferred and start <= preferred <= end:
            if not self._is_port_in_use(preferred):
                return preferred
        for port in range(start, end + 1):
            if port == preferred:
                continue
            if not self._is_port_in_use(port):
                if preferred:
                    logger.info(
                        f"{self.name}: preferred port {preferred} busy, using {port}"
                    )
                return port
        raise RuntimeError(
            f"No free port in range {start}-{end} for {self.name}. "
            f"Free some ports or expand the range."
        )

    # ─────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────

    def _register(self):
        try:
            import requests
            r = requests.post(
                f"{self.room_url}/api/connect",
                json={
                    "name": self.name,
                    "endpoint": f"http://127.0.0.1:{self.port}",
                    "pfp_path": self.pfp_path,
                    "voice": self.voice,
                    "color": self.color,
                    "metadata": self.metadata,
                },
                timeout=5
            )
            if r.status_code == 200:
                self._connected = True
                data = r.json()
                logger.info(
                    f"{self.name} connected to room "
                    f"(slot {data.get('slot', '?')}, port {self.port})"
                )
            else:
                logger.error(f"Failed to connect: HTTP {r.status_code}")
        except Exception as e:
            logger.error(f"Could not reach room server: {e}")

    def _run_local_server(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_local_server())
        self._loop.run_forever()

    async def _start_local_server(self):
        from aiohttp import web

        async def handle_respond(request):
            try:
                data = await request.json()
                message = data.get("message", "")
                context = data.get("context", "")
                participants = data.get("participants_in_room", [])

                response_text = ""
                if self._response_handler:
                    try:
                        result = self._response_handler(message, context, participants)
                        if asyncio.iscoroutine(result):
                            result = await result
                        response_text = result or ""
                    except Exception as e:
                        logger.error(f"Response handler error: {e}")

                return web.json_response({"response": response_text})
            except Exception as e:
                return web.json_response({"response": "", "error": str(e)})

        async def handle_ping(request):
            return web.json_response({
                "status": "ok",
                "name": self.name,
                "metadata": self.metadata
            })

        app = web.Application()
        app.router.add_post("/respond", handle_respond)
        app.router.add_get("/ping", handle_ping)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", self.port)
        await site.start()
        logger.info(f"{self.name} local endpoint started on port {self.port}")
