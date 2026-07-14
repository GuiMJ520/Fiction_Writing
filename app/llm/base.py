"""LLM 客户端抽象层 - 定义所有客户端实现的统一接口"""
import re
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


class ThinkFilter:
    """流式输出中的 <think>...</think> 标签过滤器

    解决 Qwen3、QwQ、DeepSeek-R1 等带思维链模型在生成时输出
    <think>...</think> 推理块的问题。状态机设计，能够正确处理
    标签被 SSE chunk 边界切分的情况。

    用法:
        f = ThinkFilter()
        for chunk in llm_stream:
            for piece in f.feed(chunk):
                yield piece
        for piece in f.flush():
            yield piece
    """

    _THINK_RE = re.compile(r"<think>|</think>", re.IGNORECASE)
    _TAG_OPEN = "<think>"
    _TAG_CLOSE = "</think>"

    def __init__(self) -> None:
        self._in_think = False
        self._buf = ""

    def feed(self, chunk: str) -> list[str]:
        """送入一个 chunk，返回过滤后的纯正文片段列表（可能为空）

        关键设计：buf 末尾可能是 <think> 或 </think> 标签的"前缀片段"，
        这种情况下不能贸然输出整个 buf，需要保留等待下一个 chunk。
        例如 buf = "<thin" 时，输出空字符串 + 保留 buf，
        等到下一个 chunk "k>推理" 来后才能判断是不是完整标签。
        """
        self._buf += chunk
        out: list[str] = []
        while self._buf:
            if self._in_think:
                # 在 think 块内：寻找 </think>
                idx = self._buf.lower().find(self._TAG_CLOSE)
                if idx == -1:
                    # 还没看到结束标签，保留 buffer 等待下一个 chunk
                    # 但为了防止极端情况下的 buffer 爆炸，限制最大长度
                    if len(self._buf) > 1024:
                        self._buf = self._buf[-1024:]
                    break
                # 跳过 </think> 标签及其之前的内容
                self._buf = self._buf[idx + len(self._TAG_CLOSE):]
                self._in_think = False
                # 继续循环处理 </think> 后的部分
            else:
                # 在正文部分：先找完整标签
                m = self._THINK_RE.search(self._buf)
                if m is not None:
                    out.append(self._buf[:m.start()])
                    tag = self._buf[m.start():m.end()].lower()
                    self._buf = self._buf[m.end():]
                    if tag == self._TAG_OPEN:
                        self._in_think = True
                    # 孤立的 </think> 直接忽略，继续处理后续
                    continue
                # 没有完整标签。检查 buf 末尾是否可能是 <think> / </think> 的前缀
                # 找到最后一个 '<'，如果从那里开始的子串是任一标签的前缀，保留
                last_lt = self._buf.rfind("<")
                if last_lt != -1:
                    tail = self._buf[last_lt:].lower()
                    if self._TAG_OPEN.startswith(tail) or self._TAG_CLOSE.startswith(tail):
                        # 可能是标签前缀：输出 < 之前的部分，保留从 < 开始的尾部
                        out.append(self._buf[:last_lt])
                        self._buf = self._buf[last_lt:]
                        break
                # 不是任何标签的前缀：安全输出整个 buffer
                out.append(self._buf)
                self._buf = ""
                break
        return out

    def flush(self) -> list[str]:
        """流结束时调用，输出 buffer 中残留的正文（仅当不在 think 中时）"""
        if self._in_think:
            # 模型忘了闭合 think 块，丢弃残留内容
            self._buf = ""
            return []
        out = [self._buf] if self._buf else []
        self._buf = ""
        return out
