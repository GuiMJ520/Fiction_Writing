"""上下文记忆管理器 - 构建 LLM 上下文，管理滑动窗口和摘要压缩

里程碑5：注入角色卡和世界观设定到 system prompt
里程碑6 将扩展：滑动窗口 + 摘要压缩
"""
from app.database import Database
from app.config import ContextConfig
from app.llm.base import LLMClient, ChatMessage
from app.utils import extract_keywords

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

        返回结构：[system_prompt(含角色/世界观), ...recent_messages]
        """
        # 从最近消息中提取查询文本（用于检索相关设定）
        query_text = " ".join(m.content for m in recent_messages[-3:] if m.role == "user")

        system_prompt = await self._build_system_prompt(
            project_id, chapter_id, query_text
        )
        context = [ChatMessage("system", system_prompt)]
        context.extend(recent_messages)
        return context

    async def _build_system_prompt(
        self, project_id: int, chapter_id: int | None, query_text: str = ""
    ) -> str:
        """构建 system prompt：默认提示词 + 项目信息 + 角色设定 + 世界观设定"""
        parts = [DEFAULT_SYSTEM_PROMPT]

        # 项目信息
        project = await self.db.fetch_one(
            "SELECT name, genre, description, system_prompt FROM projects WHERE id = ?",
            (project_id,),
        )
        if project:
            info_parts = []
            if project.get("name"):
                info_parts.append(f"当前作品：《{project['name']}》")
            if project.get("genre"):
                info_parts.append(f"类型：{project['genre']}")
            if project.get("description"):
                info_parts.append(f"简介：{project['description']}")
            if info_parts:
                parts.append("\n".join(info_parts))
            if project.get("system_prompt"):
                parts.append(project["system_prompt"])

        # 章节信息
        if chapter_id:
            chapter = await self.db.fetch_one(
                "SELECT title, summary FROM chapters WHERE id = ?", (chapter_id,)
            )
            if chapter:
                parts.append(f"当前章节：{chapter['title']}")
                if chapter.get("summary"):
                    parts.append(f"章节摘要：{chapter['summary']}")

        # 角色设定（关键词检索）
        char_section = await self._build_character_section(project_id, query_text)
        if char_section:
            parts.append(char_section)

        # 世界观设定（关键词检索）
        wv_section = await self._build_worldview_section(project_id, query_text)
        if wv_section:
            parts.append(wv_section)

        return "\n\n".join(parts)

    async def _build_character_section(
        self, project_id: int, query_text: str
    ) -> str:
        """构建角色设定文本"""
        # 检索相关角色
        characters = await self._retrieve_characters(project_id, query_text)
        if not characters:
            return ""

        lines = ["## 角色设定"]
        for char in characters:
            info_parts = [f"**{char['name']}**"]
            if char.get("role"):
                info_parts.append(f"（{char['role']}）")
            desc_parts = []
            if char.get("description"):
                desc_parts.append(char["description"])
            if char.get("personality"):
                desc_parts.append(f"性格：{char['personality']}")
            if char.get("background"):
                desc_parts.append(f"背景：{char['background']}")
            if char.get("appearance"):
                desc_parts.append(f"外貌：{char['appearance']}")
            if desc_parts:
                info_parts.append("，".join(desc_parts[:2]))
                if len(desc_parts) > 2:
                    info_parts.append("\n  " + "\n  ".join(desc_parts[2:]))
            lines.append("- " + "".join(info_parts))
        return "\n".join(lines)

    async def _build_worldview_section(
        self, project_id: int, query_text: str
    ) -> str:
        """构建世界观设定文本"""
        worldviews = await self._retrieve_worldviews(project_id, query_text)
        if not worldviews:
            return ""

        lines = ["## 世界观设定"]
        # 按分类分组
        categories: dict[str, list] = {}
        for wv in worldviews:
            cat = wv.get("category", "其他")
            categories.setdefault(cat, []).append(wv)

        for cat, items in categories.items():
            lines.append(f"### {cat}")
            for wv in items:
                content = wv.get("content", "")
                # 截断过长的内容
                if len(content) > 200:
                    content = content[:200] + "..."
                lines.append(f"- **{wv['title']}**：{content}")
        return "\n".join(lines)

    async def _retrieve_characters(
        self, project_id: int, query_text: str, limit: int = 8
    ) -> list[dict]:
        """检索与查询文本相关的角色"""
        all_chars = await self.db.fetch_all(
            "SELECT * FROM characters WHERE project_id = ? ORDER BY id",
            (project_id,),
        )
        if not all_chars:
            return []

        if not query_text:
            # 无查询文本时返回全部（限制数量）
            return all_chars[:limit]

        # 关键词匹配
        matched = []
        for char in all_chars:
            # 角色名出现在查询中
            if char.get("name") and char["name"] in query_text:
                matched.append(char)
                continue
            # keywords 字段匹配
            if char.get("keywords"):
                kw_list = [k.strip() for k in char["keywords"].split(",") if k.strip()]
                if any(kw in query_text for kw in kw_list):
                    matched.append(char)
                    continue

        # 无匹配时返回全部（小项目兜底）
        if not matched:
            return all_chars[:limit]
        return matched[:limit]

    async def _retrieve_worldviews(
        self, project_id: int, query_text: str, limit: int = 8
    ) -> list[dict]:
        """检索与查询文本相关的世界观条目"""
        all_wvs = await self.db.fetch_all(
            "SELECT * FROM worldviews WHERE project_id = ? ORDER BY id",
            (project_id,),
        )
        if not all_wvs:
            return []

        if not query_text:
            return all_wvs[:limit]

        matched = []
        for wv in all_wvs:
            if wv.get("title") and wv["title"] in query_text:
                matched.append(wv)
                continue
            if wv.get("keywords"):
                kw_list = [k.strip() for k in wv["keywords"].split(",") if k.strip()]
                if any(kw in query_text for kw in kw_list):
                    matched.append(wv)
                    continue

        if not matched:
            return all_wvs[:limit]
        return matched[:limit]

    async def maybe_compress(
        self, project_id: int, chapter_id: int | None
    ) -> bool:
        """检查是否需要压缩上下文（里程碑6实现）"""
        return False
