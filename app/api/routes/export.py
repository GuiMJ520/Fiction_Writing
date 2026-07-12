"""导出路由 - 导出章节/项目为 txt 或 markdown"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.api.dependencies import get_export_service, get_project_service, get_chapter_service
from app.services.export_service import ExportService
from app.services.project_service import ProjectService
from app.services.chapter_service import ChapterService

router = APIRouter()


def _content_disposition(filename: str) -> str:
    """生成支持中文文件名的 Content-Disposition 头（RFC 6266）"""
    return f"attachment; filename*=UTF-8''{quote(filename)}"


@router.get("/projects/{project_id}/export", tags=["导出"])
async def export_project(
    project_id: int,
    format: str = Query("md", pattern="^(md|txt)$"),
    svc: ExportService = Depends(get_export_service),
    project_svc: ProjectService = Depends(get_project_service),
):
    """导出整个项目（所有章节）为 md 或 txt"""
    if not await project_svc.get(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")

    filename, content = await svc.export_project(project_id, format)
    media_type = "text/markdown" if format == "md" else "text/plain"
    return PlainTextResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": _content_disposition(filename)},
    )


@router.get("/chapters/{chapter_id}/export", tags=["导出"])
async def export_chapter(
    chapter_id: int,
    format: str = Query("txt", pattern="^(md|txt)$"),
    svc: ExportService = Depends(get_export_service),
    chapter_svc: ChapterService = Depends(get_chapter_service),
):
    """导出单个章节为 md 或 txt"""
    if not await chapter_svc.get(chapter_id):
        raise HTTPException(status_code=404, detail="章节不存在")

    filename, content = await svc.export_chapter(chapter_id, format)
    media_type = "text/markdown" if format == "md" else "text/plain"
    return PlainTextResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": _content_disposition(filename)},
    )
