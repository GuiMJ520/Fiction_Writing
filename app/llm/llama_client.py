"""llama.cpp 原生客户端 - 调用 /completion 端点，支持 grammar 约束"""
import json
from typing import AsyncGenerator

import httpx

from app.utils import estimate_tokens
from .base import LLMClient, ChatMessage, GenerateParams


class LlamaNativeClient(LLMClient):
    """llama.cpp 原生客户端
    调用 /completion 端点，支持 GBNF grammar 约束等高级功能。
    需要将 messages 列表转换为 prompt 字符串（默认用 ChatML 格式）。
    """

    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=10.0)
        )

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _messages_to_prompt(self, messages: list[ChatMessage]) -> str:
        """将消息列表转为 ChatML 格式的 prompt
        ChatML 格式被 Qwen/GLM/Llama3 等主流模型支持。
        如需其他格式，可扩展为从配置读取 chat template。
        """
        parts = []
        for msg in messages:
            parts.append(f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>")
        # 末尾添加 assistant 起始标记，引导模型生成回复
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    def _build_payload(
        self, prompt: str, params: GenerateParams | None, stream: bool
    ) -> dict:
        p = params or GenerateParams()
        payload = {
            "prompt": prompt,
            "temperature": p.temperature,
            "n_predict": p.max_tokens,  # llama.cpp 用 n_predict 而非 max_tokens
            "top_p": p.top_p,
            "top_k": p.top_k,
            "repeat_penalty": p.repeat_penalty,
            "stream": stream,
            "cache_prompt": True,  # 启用 KV 缓存
        }
        if p.seed != -1:
            payload["seed"] = p.seed
        if p.stop:
            payload["stop"] = p.stop
        # grammar 约束（llama.cpp 原生支持，GBNF 格式）
        if p.grammar:
            payload["grammar"] = p.grammar
        return payload

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        params: GenerateParams | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式对话：解析 SSE，yield content 字段"""
        prompt = self._messages_to_prompt(messages)
        payload = self._build_payload(prompt, params, stream=True)
        url = f"{self.base_url}/completion"
        async with self._client.stream(
            "POST", url, json=payload, headers=self._headers()
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                    if content := data.get("content"):
                        yield content
                    if data.get("stop"):
                        return
                except json.JSONDecodeError:
                    continue

    async def chat(
        self,
        messages: list[ChatMessage],
        params: GenerateParams | None = None,
    ) -> str:
        """非流式对话：返回完整 content"""
        prompt = self._messages_to_prompt(messages)
        payload = self._build_payload(prompt, params, stream=False)
        url = f"{self.base_url}/completion"
        resp = await self._client.post(url, json=payload, headers=self._headers())
        resp.raise_for_status()
        return resp.json().get("content", "")

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
        """token 计数：用 /tokenize 端点"""
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
