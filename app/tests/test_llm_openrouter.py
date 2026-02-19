import unittest
from unittest.mock import patch

import httpx

from app.core.llm_openrouter import generate_text


class _FakeResponse:
    def __init__(self, status_code: int, data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text
        self.request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code} error",
                request=self.request,
                response=self,
            )

    def json(self):
        return self._data


class _FakeAsyncClient:
    posted_models: list[str] = []

    def __init__(self, timeout=None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers):
        model = json.get("model")
        self.__class__.posted_models.append(model)

        if model == "invalid/model":
            return _FakeResponse(status_code=404, text='{"error":{"message":"Model not found"}}')

        return _FakeResponse(
            status_code=200,
            data={"choices": [{"message": {"content": "ok"}}]},
        )


class TestOpenRouterFallback(unittest.IsolatedAsyncioTestCase):
    @patch("app.core.llm_openrouter.httpx.AsyncClient", new=_FakeAsyncClient)
    @patch("app.core.llm_openrouter.get_app_config")
    async def test_404_model_falls_back_to_default_model(self, mock_get_app_config):
        _FakeAsyncClient.posted_models = []
        mock_get_app_config.return_value = {
            "llm": {
                "model": "fallback/model",
                "temperature": 0.7,
                "max_tokens": 300,
                "timeout_sec": 10,
            }
        }

        result = await generate_text(
            messages=[{"role": "user", "content": "hi"}],
            model="invalid/model",
            timeout_sec=1,
        )

        self.assertEqual(result, "ok")
        self.assertEqual(_FakeAsyncClient.posted_models, ["invalid/model", "fallback/model"])


if __name__ == "__main__":
    unittest.main()
