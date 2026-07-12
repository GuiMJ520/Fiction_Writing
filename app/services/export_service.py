"""导出服务 - 将章节/项目导出为 txt 或 markdown"""
from app.database import Database
from app.services.chapter_service import ChapterService
from app.services.project_service import ProjectService


class ExportService:
    def __init__(self, db: Database):
        self.db = db
        self.chapter_svc = ChapterService(db)
        self.project_svc = ProjectService(db)

    async def export_chapter(
        self, chapter_id: int, fmt: str = "txt"
    ) -> tuple[str, str]:
        """导出单个章节

        返回 (filename, content)
        """
        chapter = await self.chapter_svc.get(chapter_id)
        if not chapter:
            raise ValueError("章节不存在")

        if fmt == "md":
            content = f"# {chapter.title}\n\n{chapter.content}"
        else:
            content = f"{chapter.title}\n\n{chapter.content}"

        # 安全的文件名
        safe_title = chapter.title.replace(" ", "_").replace("/", "_")
        ext = "md" if fmt == "md" else "txt"
        filename = f"{safe_title}.{ext}"
        return filename, content

    async def export_project(
        self, project_id: int, fmt: str = "md"
    ) -> tuple[str, str]:
        """导出整个项目（所有章节）

        返回 (filename, content)
        """
        project = await self.project_svc.get(project_id)
        if not project:
            raise ValueError("项目不存在")

        chapters = await self.chapter_svc.list_by_project(project_id)

        if fmt == "md":
            lines = [f"# {project.name}\n"]
            if project.description:
                lines.append(f"> {project.description}\n")
            for ch in chapters:
                lines.append(f"## {ch.title}\n")
                lines.append(ch.content or "(暂无内容)")
                lines.append("")
        else:
            lines = [project.name, "=" * 40, ""]
            for ch in chapters:
                lines.append(ch.title)
                lines.append("-" * 20)
                lines.append(ch.content or "(暂无内容)")
                lines.append("")

        content = "\n".join(lines)
        safe_name = project.name.replace(" ", "_").replace("/", "_")
        ext = "md" if fmt == "md" else "txt"
        filename = f"{safe_name}.{ext}"
        return filename, content
