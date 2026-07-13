"""对话生成服务 - 编排上下文管理 + LLM 调用 + 消息存储"""
from typing import AsyncGenerator

from app.storage import FileStorage
from app.llm.base import LLMClient, ChatMessage, GenerateParams
from app.config import ContextConfig
from app.utils import estimate_tokens
from app.models import Message
from .context_manager import ContextManager


class ChatService:
    """对话生成服务"""

    def __init__(
        self,
        storage: FileStorage,
        llm_client: LLMClient,
        context_manager: ContextManager,
        context_config: ContextConfig,
    ):
        self.storage = storage
        self.llm_client = llm_client
        self.context_manager = context_manager
        self.context_config = context_config

    async def generate(
        self,
        project_id: int,
        user_message: str,
        chapter_id: int | None = None,
        params: GenerateParams | None = None,
        context_window: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式生成回复

        流程：存用户消息 → 压缩检查 → 获取最近消息 → 构建上下文 → 流式生成 → 存AI回复
        context_window: 覆盖默认滑动窗口大小（消息条数）
        """
        # 1. 存用户消息
        await self.storage.add_message(
            project_id,
            chapter_id,
            "user",
            user_message,
            estimate_tokens(user_message),
        )

        # 2. 压缩检查
        await self.context_manager.maybe_compress(project_id, chapter_id)

        # 3. 获取最近消息（滑动窗口）
        recent = await self._get_recent_messages(project_id, chapter_id, context_window)

        # 4. 构建完整上下文
        context = await self.context_manager.build_context(
            project_id, chapter_id, recent
        )

        # 5. 流式生成
        full_response: list[str] = []
        try:
            async for chunk in self.llm_client.chat_stream(context, params):
                full_response.append(chunk)
                yield chunk
        except Exception as e:
            yield f"\n\n[生成出错: {e}]"
            return

        # 6. 存 AI 回复
        response_text = "".join(full_response)
        await self.storage.add_message(
            project_id,
            chapter_id,
            "assistant",
            response_text,
            estimate_tokens(response_text),
        )

    async def _get_recent_messages(
        self, project_id: int, chapter_id: int | None, context_window: int | None = None
    ) -> list[ChatMessage]:
        """获取最近 N 条消息（滑动窗口），按时间正序返回"""
        limit = context_window if context_window else self.context_config.window_size
        rows = await self.storage.get_recent_messages(project_id, chapter_id, limit)
        return [ChatMessage(r["role"], r["content"]) for r in rows]

    async def get_history(
        self, project_id: int, chapter_id: int | None = None, limit: int = 50
    ) -> list[Message]:
        """获取对话历史"""
        rows = await self.storage.get_messages(project_id, chapter_id, limit)
        return [Message(**r) for r in rows]

    async def clear_history(
        self, project_id: int, chapter_id: int | None = None
    ) -> int:
        """清空对话历史，返回删除的消息数"""
        return await self.storage.clear_messages(project_id, chapter_id)
