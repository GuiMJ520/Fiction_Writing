"""LLM 客户端抽象层 - 定义所有客户端实现的统一接口"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class ChatMessage:
    """统一的对话消息格式"""
    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class GenerateParams:
    """生成参数 - 两种客户端共用，不支持的字段会被对应客户端忽略"""
    temperature: float = 0.8
    max_tokens: int = 2048        # 最大生成 token 数，-1 为不限制
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    seed: int = -1                # -1 为随机
    stop: list[str] | None = None  # 停止序列
    # 高级字段（仅特定客户端支持）
    grammar: str | None = None     # GBNF 语法，仅 llama_native 支持
    response_format: dict | None = None  # {"type":"json_object"}，仅 openai_compat 支持


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        params: GenerateParams | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式对话生成，逐个 yield 文本片段"""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        params: GenerateParams | None = None,
    ) -> str:
        """非流式对话生成，返回完整文本"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """检查 LLM 服务是否可用"""
        ...

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """估算文本 token 数（优先用 /tokenize 端点，降级为字符估算）"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """释放底层 HTTP 连接"""
        ...
