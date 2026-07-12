"""世界观服务 - 世界观条目 CRUD 和关键词检索"""
from app.database import Database
from app.models import Worldview, WorldviewCreate, WorldviewUpdate
from app.utils import extract_keywords


class WorldviewService:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, project_id: int, data: WorldviewCreate) -> Worldview:
        cursor = await self.db.execute(
            """INSERT INTO worldviews
               (project_id, category, title, content, keywords)
               VALUES (?, ?, ?, ?, ?)""",
            (project_id, data.category, data.title, data.content, data.keywords),
        )
        return await self.get(cursor.lastrowid)  # type: ignore

    async def get(self, worldview_id: int) -> Worldview | None:
        row = await self.db.fetch_one(
            "SELECT * FROM worldviews WHERE id = ?", (worldview_id,)
        )
        return Worldview(**row) if row else None

    async def list_by_project(
        self, project_id: int, category: str | None = None
    ) -> list[Worldview]:
        if category:
            rows = await self.db.fetch_all(
                "SELECT * FROM worldviews WHERE project_id = ? AND category = ? ORDER BY id",
                (project_id, category),
            )
        else:
            rows = await self.db.fetch_all(
                "SELECT * FROM worldviews WHERE project_id = ? ORDER BY category, id",
                (project_id,),
            )
        return [Worldview(**r) for r in rows]

    async def list_categories(self, project_id: int) -> list[str]:
        """列出项目下所有世界观分类"""
        rows = await self.db.fetch_all(
            "SELECT DISTINCT category FROM worldviews WHERE project_id = ? ORDER BY category",
            (project_id,),
        )
        return [r["category"] for r in rows]

    async def update(self, worldview_id: int, data: WorldviewUpdate) -> Worldview | None:
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(worldview_id)
        set_clauses = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [worldview_id]
        await self.db.execute(
            f"UPDATE worldviews SET {set_clauses}, "
            f"updated_at = datetime('now','localtime') WHERE id = ?",
            tuple(values),
        )
        return await self.get(worldview_id)

    async def delete(self, worldview_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM worldviews WHERE id = ?", (worldview_id,)
        )
        return cursor.rowcount > 0

    async def search_by_keywords(
        self, project_id: int, query: str, limit: int = 10
    ) -> list[Worldview]:
        """根据查询文本检索相关世界观条目"""
        keywords = extract_keywords(query)
        if not keywords:
            return []

        all_wvs = await self.list_by_project(project_id)
        matched = []
        for wv in all_wvs:
            # 标题出现在查询中
            if wv.title and wv.title in query:
                matched.append(wv)
                continue
            # keywords 字段匹配
            if wv.keywords:
                wv_kw = [k.strip() for k in wv.keywords.split(",") if k.strip()]
                if any(kw in query for kw in wv_kw):
                    matched.append(wv)
                    continue
            # 查询关键词匹配标题或内容
            if any(kw in wv.title or (wv.content and kw in wv.content)
                   for kw in keywords):
                matched.append(wv)

        return matched[:limit]
