"""上下文记忆管理器 - 构建 LLM 上下文，管理滑动窗口和摘要压缩

里程碑4（基础版）：构建 system prompt + 最近消息
里程碑6 将扩展：滑动窗口 + 摘要压缩 + 角色/世界观注入
"""
from app.database import Database
from app.config import ContextConfig
from app.llm.base import LLMClient, ChatMessage

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个专业的小说写作助手，擅长创作各种类型的小说。

你的职责：
1. 根据用户的设定和要求，创作生动的小说内容
2. 保持文风一致，情节连贯
3. 角色塑造鲜明，对话自然
4. 适当运用环境描写、心理活动等写作技巧

请用中文回复，保持专业和创意。"""


class ContextManager:
    """上下文记忆管理器"""

    def __init__(self, db: Database, llm_client: LLMClient, config: ContextConfig):
        self.db = db
        self.llm_client = llm_client
        self.config = config

    async def build_context(
        self,
        project_id: int,
        chapter_id: int | None,
        recent_messages: list[ChatMessage],
    ) -> list[ChatMessage]:
        """构建发送给 LLM 的完整上下文

        返回结构：[system_prompt, ...recent_messages]
        """
        system_prompt = await self._build_system_prompt(project_id, chapter_id)
        context = [ChatMessage("system", system_prompt)]
        context.extend(recent_messages)
        return context

    async def _build_system_prompt(
        self, project_id: int, chapter_id: int | None
    ) -> str:
        """构建 system prompt（基础版：默认提示词 + 项目设定）"""
        parts = [DEFAULT_SYSTEM_PROMPT]

        # 获取项目信息
        project = await self.db.fetch_one(
            "SELECT name, genre, description, system_prompt FROM projects WHERE id = ?",
            (project_id,),
        )
        if project:
            # 项目信息
            info_parts = []
            if project.get("name"):
                info_parts.append(f"当前作品：《{project['name']}》")
            if project.get("genre"):
                info_parts.append(f"类型：{project['genre']}")
            if project.get("description"):
                info_parts.append(f"简介：{project['description']}")
            if info_parts:
                parts.append("\n".join(info_parts))

            # 项目自定义 system prompt
            if project.get("system_prompt"):
                parts.append(project["system_prompt"])

        # 章节信息（如果有）
        if chapter_id:
            chapter = await self.db.fetch_one(
                "SELECT title, summary FROM chapters WHERE id = ?", (chapter_id,)
            )
            if chapter:
                parts.append(f"当前章节：{chapter['title']}")
                if chapter.get("summary"):
                    parts.append(f"章节摘要：{chapter['summary']}")

        return "\n\n".join(parts)

    async def maybe_compress(
        self, project_id: int, chapter_id: int | None
    ) -> bool:
        """检查是否需要压缩上下文（里程碑6实现）"""
        return False
