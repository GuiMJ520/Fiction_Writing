"""OpenAI 兼容客户端 - 调用 /v1/chat/completions 端点"""
import json
from typing import AsyncGenerator

import httpx

from app.utils import estimate_tokens
from .base import LLMClient, ChatMessage, GenerateParams


class OpenAICompatClient(LLMClient):
    """OpenAI 兼容客户端（llama-server 默认提供此端点）"""

    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0)
        )

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_payload(
        self, messages: list[ChatMessage], params: GenerateParams | None, stream: bool
    ) -> dict:
        p = params or GenerateParams()
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": p.temperature,
            "max_tokens": p.max_tokens,
            "top_p": p.top_p,
            "stream": stream,
        }
        # llama-server 扩展参数
        if p.top_k != 40:
            payload["top_k"] = p.top_k
        if p.repeat_penalty != 1.1:
            payload["repeat_penalty"] = p.repeat_penalty
        if p.seed != -1:
            payload["seed"] = p.seed
        if p.stop:
            payload["stop"] = p.stop
        if p.response_format:
            payload["response_format"] = p.response_format
        # 启用 KV 缓存（llama-server 支持）
        payload["cache_prompt"] = True
        return payload

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        params: GenerateParams | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式对话：解析 SSE，yield delta.content"""
        payload = self._build_payload(messages, params, stream=True)
        url = f"{self.base_url}/v1/chat/completions"
        async with self._client.stream(
            "POST", url, json=payload, headers=self._headers()
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    return
                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        if content := delta.get("content"):
                            yield content
                except json.JSONDecodeError:
                    continue

    async def chat(
        self,
        messages: list[ChatMessage],
        params: GenerateParams | None = None,
    ) -> str:
        """非流式对话：返回完整文本"""
        payload = self._build_payload(messages, params, stream=False)
        url = f"{self.base_url}/v1/chat/completions"
        resp = await self._client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def health_check(self) -> bool:
        """检查服务是否可用：GET /health"""
        try:
            resp = await self._client.get(
                f"{self.base_url}/health", timeout=5.0
            )
            return resp.status_code == 200
        except (httpx.RequestError, httpx.HTTPStatusError):
            return False

    async def count_tokens(self, text: str) -> int:
        """token 计数：优先用 /tokenize 端点，失败则降级估算"""
        try:
            resp = await self._client.post(
                f"{self.base_url}/tokenize",
                json={"content": text},
                headers=self._headers(),
                timeout=10.0,
            )
            if resp.status_code == 200:
                tokens = resp.json().get("tokens", [])
                if isinstance(tokens, list):
                    return len(tokens)
        except (httpx.RequestError, httpx.HTTPStatusError):
            pass
        return estimate_tokens(text)

    async def close(self) -> None:
        await self._client.aclose()
