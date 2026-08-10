import json
import os

DEFAULT_MODEL = "deepseek-chat"


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.getenv("LDE_LLM_API_KEY")
        self.base_url = base_url or os.getenv("LDE_LLM_BASE_URL")
        self.model = model or os.getenv("LDE_LLM_MODEL") or DEFAULT_MODEL
        self._client = None
        self.available = False
        if not self.api_key:
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.available = True
        except ImportError:
            self.available = False

    def chat_json(self, system: str, user: str) -> dict | None:
        if not self.available or self._client is None:
            return None
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return json.loads(resp.choices[0].message.content or "{}")
        except Exception:
            return None
