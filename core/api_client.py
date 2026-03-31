import requests
from core.config_manager import load_agent_config


class ApiClient:
    def __init__(self):
        self.config = load_agent_config()
        self.base_url = self.config.get("server", "url", fallback="http://localhost:8000")

    def get(self, path):
        try:
            res = requests.get(f"{self.base_url}{path}", timeout=5)
            return res.json()
        except Exception:
            return None

    def post(self, path, payload):
        try:
            res = requests.post(f"{self.base_url}{path}", json=payload, timeout=5)
            return res.json()
        except Exception:
            return None