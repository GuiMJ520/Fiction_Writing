"""角色服务 - 角色卡 CRUD 和关键词检索"""
from app.storage import FileStorage
from app.models import Character, CharacterCreate, CharacterUpdate
from app.utils import extract_keywords


class CharacterService:
    def __init__(self, storage: FileStorage):
        self.storage = storage

    async def create(self, project_id: int, data: CharacterCreate) -> Character:
        character = await self.storage.create_character(
            project_id, data.model_dump()
        )
        return Character(**character)

    async def get(self, character_id: int) -> Character | None:
        row = await self.storage.get_character(character_id)
        return Character(**row) if row else None

    async def list_by_project(self, project_id: int) -> list[Character]:
        rows = await self.storage.list_characters_by_project(project_id)
        return [Character(**r) for r in rows]

    async def update(
        self, character_id: int, data: CharacterUpdate
    ) -> Character | None:
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(character_id)
        row = await self.storage.update_character(character_id, fields)
        return Character(**row) if row else None

    async def delete(self, character_id: int) -> bool:
        return await self.storage.delete_character(character_id)

    async def search_by_keywords(
        self, project_id: int, query: str, limit: int = 10
    ) -> list[Character]:
        """根据查询文本检索相关角色

        匹配规则：角色名出现在查询文本中，或角色 keywords 字段包含查询关键词。
        无匹配时返回空列表（由调用方决定是否回退到全部角色）。
        """
        keywords = extract_keywords(query)
        if not keywords:
            return []

        all_chars = await self.list_by_project(project_id)
        matched = []
        for char in all_chars:
            # 角色名出现在查询中
            if char.name and char.name in query:
                matched.append(char)
                continue
            # keywords 字段匹配查询关键词
            if char.keywords:
                char_kw = [k.strip() for k in char.keywords.split(",") if k.strip()]
                if any(kw in query for kw in char_kw):
                    matched.append(char)
                    continue
            # 查询关键词匹配角色名或描述
            if any(
                kw in char.name or (char.description and kw in char.description)
                for kw in keywords
            ):
                matched.append(char)

        return matched[:limit]
