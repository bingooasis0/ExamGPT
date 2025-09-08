# openai_client.py
from __future__ import annotations
import os, json, requests

class ChatGPTClient:
    def __init__(self, api_env: str = "OPENAI_API_KEY", model: str = "gpt-5", max_tokens: int = 256):
        self.api_env = api_env
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = os.environ.get(api_env, "")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def reconfigure(self, api_env: str, model: str, max_tokens: int):
        self.api_env = api_env
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = os.environ.get(api_env, "")

    def _headers(self):
        if not self.api_key:
            raise RuntimeError(f"Missing API key in env var {self.api_env}")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict):
        r = requests.post(self.base_url, headers=self._headers(), data=json.dumps(payload), timeout=60)
        if r.status_code >= 400:
            try:
                msg = r.json()
            except Exception:
                msg = r.text
            r.raise_for_status()
        return r.json()

    def _token_param(self) -> dict:
        # Some newer models expect max_completion_tokens
        key = "max_completion_tokens" if self.model.startswith("gpt-5") else "max_tokens"
        return {key: int(self.max_tokens)}

    def ask(self, system: str, user: str, max_tokens: int | None = None) -> str:
        if max_tokens is not None:
            self.max_tokens = max_tokens

        token_key = "max_completion_tokens" if str(self.model).startswith("gpt-5") else "max_tokens"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system or "You are a helpful assistant."},
                {"role": "user", "content": user},
            ],
            token_key: int(self.max_tokens),
        }
        data = self._post(payload)

        # Be defensive about the shape
        choices = (data or {}).get("choices") or []
        if not choices:
            return ""
        msg = choices[0].get("message") or {}
        content = (msg.get("content") or "").strip()
        refusal = (msg.get("refusal") or "").strip()
        return content or refusal or ""
    
    def test_poem(self) -> str:
        return self.ask("Write a two-line poem.", "About a kite.")
