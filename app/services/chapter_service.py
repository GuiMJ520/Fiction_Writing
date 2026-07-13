"""章节服务 - 章节 CRUD 和排序"""
from app.storage import FileStorage
from app.models import Chapter, ChapterCreate, ChapterUpdate
from app.utils import count_words


class ChapterService:
    def __init__(self, storage: FileStorage):
        self.storage = storage

    async def create(
        self, project_id: int, data: ChapterCreate
    ) -> Chapter:
        """创建章节。未指定 order 时自动追加到末尾"""
        if data.chapter_order is None:
            existing = await self.storage.list_chapters_by_project(project_id)
            order = (
                max((c.get("chapter_order", 0) for c in existing), default=0) + 1
            )
        else:
            order = data.chapter_order
        chapter = await self.storage.create_chapter(
            project_id, {"title": data.title, "chapter_order": order}
        )
        return Chapter(**chapter)

    async def get(self, chapter_id: int) -> Chapter | None:
        """获取章节（含正文）"""
        meta = await self.storage.get_chapter(chapter_id)
        if not meta:
            return None
        meta["content"] = await self.storage.get_chapter_content(chapter_id)
        return Chapter(**meta)

    async def list_by_project(self, project_id: int) -> list[Chapter]:
        """列出项目的所有章节（仅元数据，不含正文）"""
        rows = await self.storage.list_chapters_by_project(project_id)
        return [Chapter(**r) for r in rows]

    async def update(
        self, chapter_id: int, data: ChapterUpdate
    ) -> Chapter | None:
        """更新章节。content 变更时自动更新 word_count"""
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(chapter_id)
        # 如果更新了 content，同步更新 word_count 并写入 .md 文件
        content_updated = False
        if "content" in fields:
            content = fields.pop("content")
            fields["word_count"] = count_words(content)
            await self.storage.set_chapter_content(chapter_id, content)
            content_updated = True
        if not fields:
            return await self.get(chapter_id)
        row = await self.storage.update_chapter(chapter_id, fields)
        if not row:
            return None
        if content_updated:
            row["content"] = await self.storage.get_chapter_content(chapter_id)
        return Chapter(**row)

    async def reorder(self, project_id: int, chapter_ids: list[int]) -> None:
        """按给定的 id 顺序重新排列章节"""
        await self.storage.reorder_chapters(project_id, chapter_ids)

    async def delete(self, chapter_id: int) -> bool:
        return await self.storage.delete_chapter(chapter_id)
