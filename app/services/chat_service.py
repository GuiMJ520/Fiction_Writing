"""对话生成服务 - 编排上下文管理 + LLM 调用 + 消息存储"""
from typing import AsyncGenerator

from app.database import Database
from app.llm.base import LLMClient, ChatMessage, GenerateParams
from app.config import ContextConfig
from app.utils import estimate_tokens
from app.models import Message
from .context_manager import ContextManager


class ChatService:
    """对话生成服务"""

    def __init__(
        self,
        db: Database,
        llm_client: LLMClient,
        context_manager: ContextManager,
        context_config: ContextConfig,
    ):
        self.db = db
        self.llm_client = llm_client
        self.context_manager = context_manager
        self.context_config = context_config

    async def generate(
        self,
        project_id: int,
        user_message: str,
        chapter_id: int | None = None,
        params: GenerateParams | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式生成回复

        流程：存用户消息 → 压缩检查 → 获取最近消息 → 构建上下文 → 流式生成 → 存AI回复
        """
        # 1. 存用户消息
        await self.db.execute(
            """INSERT INTO messages (project_id, chapter_id, role, content, token_count)
               VALUES (?, ?, 'user', ?, ?)""",
            (project_id, chapter_id, user_message, estimate_tokens(user_message)),
        )

        # 2. 压缩检查（里程碑6实现，当前为空操作）
        await self.context_manager.maybe_compress(project_id, chapter_id)

        # 3. 获取最近消息（滑动窗口）
        recent = await self._get_recent_messages(project_id, chapter_id)

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
        await self.db.execute(
            """INSERT INTO messages (project_id, chapter_id, role, content, token_count)
               VALUES (?, ?, 'assistant', ?, ?)""",
            (project_id, chapter_id, response_text, estimate_tokens(response_text)),
        )

    async def _get_recent_messages(
        self, project_id: int, chapter_id: int | None
    ) -> list[ChatMessage]:
        """获取最近 N 条消息（滑动窗口），按时间正序返回"""
        limit = self.context_config.window_size
        if chapter_id:
            rows = await self.db.fetch_all(
                """SELECT role, content FROM messages
                   WHERE chapter_id = ? AND is_summary = 0
                   ORDER BY id DESC LIMIT ?""",
                (chapter_id, limit),
            )
        else:
            rows = await self.db.fetch_all(
                """SELECT role, content FROM messages
                   WHERE project_id = ? AND chapter_id IS NULL AND is_summary = 0
                   ORDER BY id DESC LIMIT ?""",
                (project_id, limit),
            )
        # DESC 取最近 N 条，反转为正序
        rows.reverse()
        return [ChatMessage(r["role"], r["content"]) for r in rows]

    async def get_history(
        self, project_id: int, chapter_id: int | None = None, limit: int = 50
    ) -> list[Message]:
        """获取对话历史"""
        if chapter_id:
            rows = await self.db.fetch_all(
                """SELECT * FROM messages WHERE chapter_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (chapter_id, limit),
            )
        else:
            rows = await self.db.fetch_all(
                """SELECT * FROM messages
                   WHERE project_id = ? AND chapter_id IS NULL
                   ORDER BY id DESC LIMIT ?""",
                (project_id, limit),
            )
        rows.reverse()
        return [Message(**r) for r in rows]

    async def clear_history(
        self, project_id: int, chapter_id: int | None = None
    ) -> int:
        """清空对话历史，返回删除的消息数"""
        if chapter_id:
            cursor = await self.db.execute(
                "DELETE FROM messages WHERE chapter_id = ?", (chapter_id,)
            )
        else:
            cursor = await self.db.execute(
                "DELETE FROM messages WHERE project_id = ? AND chapter_id IS NULL",
                (project_id,),
            )
        return cursor.rowcount
