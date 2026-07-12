"""章节路由 - /api/projects/{pid}/chapters 和 /api/chapters/{cid}"""
from fastapi import APIRouter, Depends, HTTPException

from app.models import Chapter, ChapterCreate, ChapterUpdate
from app.services.chapter_service import ChapterService
from app.services.project_service import ProjectService
from app.api.dependencies import get_chapter_service, get_project_service

router = APIRouter()


@router.get(
    "/projects/{project_id}/chapters",
    response_model=list[Chapter],
    tags=["章节"],
)
async def list_chapters(
    project_id: int, svc: ChapterService = Depends(get_chapter_service)
):
    """列出项目下所有章节"""
    return await svc.list_by_project(project_id)


@router.post(
    "/projects/{project_id}/chapters",
    response_model=Chapter,
    tags=["章节"],
    status_code=201,
)
async def create_chapter(
    project_id: int,
    data: ChapterCreate,
    svc: ChapterService = Depends(get_chapter_service),
    project_svc: ProjectService = Depends(get_project_service),
):
    """在项目下创建章节"""
    # 校验项目存在
    if not await project_svc.get(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return await svc.create(project_id, data)


@router.get("/chapters/{chapter_id}", response_model=Chapter, tags=["章节"])
async def get_chapter(
    chapter_id: int, svc: ChapterService = Depends(get_chapter_service)
):
    """获取章节详情"""
    chapter = await svc.get(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.put("/chapters/{chapter_id}", response_model=Chapter, tags=["章节"])
async def update_chapter(
    chapter_id: int,
    data: ChapterUpdate,
    svc: ChapterService = Depends(get_chapter_service),
):
    """更新章节（标题/内容/状态/摘要）"""
    chapter = await svc.update(chapter_id, data)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")
    return chapter


@router.put(
    "/projects/{project_id}/chapters/reorder",
    tags=["章节"],
)
async def reorder_chapters(
    project_id: int,
    chapter_ids: list[int],
    svc: ChapterService = Depends(get_chapter_service),
):
    """调整章节顺序（传入按新顺序排列的 chapter id 列表）"""
    await svc.reorder(project_id, chapter_ids)
    return {"message": "顺序已更新"}


@router.delete("/chapters/{chapter_id}", tags=["章节"])
async def delete_chapter(
    chapter_id: int, svc: ChapterService = Depends(get_chapter_service)
):
    """删除章节"""
    ok = await svc.delete(chapter_id)
    if not ok:
        raise HTTPException(status_code=404, detail="章节不存在")
    return {"message": "已删除"}
