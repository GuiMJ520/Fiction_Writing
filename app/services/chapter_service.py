"""章节服务 - 章节 CRUD 和排序"""
from app.database import Database
from app.models import Chapter, ChapterCreate, ChapterUpdate
from app.utils import count_words


class ChapterService:
    def __init__(self, db: Database):
        self.db = db

    async def create(
        self, project_id: int, data: ChapterCreate
    ) -> Chapter:
        """创建章节。未指定 order 时自动追加到末尾"""
        if data.chapter_order is None:
            # 自动计算下一个 order
            row = await self.db.fetch_one(
                "SELECT COALESCE(MAX(chapter_order), 0) + 1 AS next_order "
                "FROM chapters WHERE project_id = ?",
                (project_id,),
            )
            order = row["next_order"] if row else 1
        else:
            order = data.chapter_order
        cursor = await self.db.execute(
            """INSERT INTO chapters (project_id, title, chapter_order)
               VALUES (?, ?, ?)""",
            (project_id, data.title, order),
        )
        return await self.get(cursor.lastrowid)  # type: ignore

    async def get(self, chapter_id: int) -> Chapter | None:
        row = await self.db.fetch_one(
            "SELECT * FROM chapters WHERE id = ?", (chapter_id,)
        )
        return Chapter(**row) if row else None

    async def list_by_project(self, project_id: int) -> list[Chapter]:
        rows = await self.db.fetch_all(
            "SELECT * FROM chapters WHERE project_id = ? ORDER BY chapter_order",
            (project_id,),
        )
        return [Chapter(**r) for r in rows]

    async def update(
        self, chapter_id: int, data: ChapterUpdate
    ) -> Chapter | None:
        """更新章节。content 变更时自动更新 word_count"""
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(chapter_id)
        # 如果更新了 content，同步更新 word_count
        if "content" in fields:
            fields["word_count"] = count_words(fields["content"])
        set_clauses = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [chapter_id]
        await self.db.execute(
            f"UPDATE chapters SET {set_clauses}, "
            f"updated_at = datetime('now','localtime') WHERE id = ?",
            tuple(values),
        )
        return await self.get(chapter_id)

    async def reorder(self, project_id: int, chapter_ids: list[int]) -> None:
        """按给定的 id 顺序重新排列章节"""
        for index, chapter_id in enumerate(chapter_ids, start=1):
            await self.db.execute(
                "UPDATE chapters SET chapter_order = ? WHERE id = ? AND project_id = ?",
                (index, chapter_id, project_id),
            )

    async def delete(self, chapter_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM chapters WHERE id = ?", (chapter_id,)
        )
        return cursor.rowcount > 0
