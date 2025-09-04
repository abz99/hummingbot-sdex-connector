class WebAssistantsFactory:
    def __init__(self, throttler=None, auth=None):
        self._throttler = throttler
        self._auth = auth

    async def get_ws_assistant(self):
        return WSAssistant()


class WSAssistant:
    async def connect(self, url: str):
        pass

    async def disconnect(self):
        pass
