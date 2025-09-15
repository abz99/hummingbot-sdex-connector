from typing import Any, Optional


class WSAssistant:
    async def connect(self, url: str) -> None:
        pass

    async def disconnect(self) -> None:
        pass


class WebAssistantsFactory:
    def __init__(self, throttler: Any = None, auth: Any = None) -> None:
        self._throttler = throttler
        self._auth = auth

    @property
    def throttler(self) -> Any:
        return self._throttler

    @property
    def auth(self) -> Any:
        return self._auth

    async def get_ws_assistant(self) -> WSAssistant:
        return WSAssistant()
