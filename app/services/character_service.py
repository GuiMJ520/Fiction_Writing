"""角色服务 - 角色卡 CRUD 和关键词检索"""
from app.database import Database
from app.models import Character, CharacterCreate, CharacterUpdate
from app.utils import extract_keywords


class CharacterService:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, project_id: int, data: CharacterCreate) -> Character:
        cursor = await self.db.execute(
            """INSERT INTO characters
               (project_id, name, role, description, personality, background, appearance, keywords)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, data.name, data.role, data.description,
             data.personality, data.background, data.appearance, data.keywords),
        )
        return await self.get(cursor.lastrowid)  # type: ignore

    async def get(self, character_id: int) -> Character | None:
        row = await self.db.fetch_one(
            "SELECT * FROM characters WHERE id = ?", (character_id,)
        )
        return Character(**row) if row else None

    async def list_by_project(self, project_id: int) -> list[Character]:
        rows = await self.db.fetch_all(
            "SELECT * FROM characters WHERE project_id = ? ORDER BY id",
            (project_id,),
        )
        return [Character(**r) for r in rows]

    async def update(self, character_id: int, data: CharacterUpdate) -> Character | None:
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(character_id)
        set_clauses = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [character_id]
        await self.db.execute(
            f"UPDATE characters SET {set_clauses}, "
            f"updated_at = datetime('now','localtime') WHERE id = ?",
            tuple(values),
        )
        return await self.get(character_id)

    async def delete(self, character_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM characters WHERE id = ?", (character_id,)
        )
        return cursor.rowcount > 0

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

        # 构建匹配条件：name LIKE 或 keywords LIKE
        conditions = []
        params: list = [project_id]
        # 角色名匹配
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
            if any(kw in char.name or (char.description and kw in char.description)
                   for kw in keywords):
                matched.append(char)

        return matched[:limit]
