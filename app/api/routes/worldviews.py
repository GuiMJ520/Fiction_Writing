"""世界观路由 - /api/projects/{pid}/worldviews 和 /api/worldviews/{id}"""
from fastapi import APIRouter, Depends, HTTPException

from app.models import Worldview, WorldviewCreate, WorldviewUpdate
from app.services.worldview_service import WorldviewService
from app.services.project_service import ProjectService
from app.api.dependencies import get_worldview_service, get_project_service

router = APIRouter()


@router.get(
    "/projects/{project_id}/worldviews",
    response_model=list[Worldview],
    tags=["世界观"],
)
async def list_worldviews(
    project_id: int,
    category: str | None = None,
    svc: WorldviewService = Depends(get_worldview_service),
):
    """列出项目下所有世界观条目（可按分类过滤）"""
    return await svc.list_by_project(project_id, category)


@router.get(
    "/projects/{project_id}/worldviews/categories",
    response_model=list[str],
    tags=["世界观"],
)
async def list_categories(
    project_id: int, svc: WorldviewService = Depends(get_worldview_service)
):
    """列出项目下所有世界观分类"""
    return await svc.list_categories(project_id)


@router.post(
    "/projects/{project_id}/worldviews",
    response_model=Worldview,
    tags=["世界观"],
    status_code=201,
)
async def create_worldview(
    project_id: int,
    data: WorldviewCreate,
    svc: WorldviewService = Depends(get_worldview_service),
    project_svc: ProjectService = Depends(get_project_service),
):
    """创建世界观条目"""
    if not await project_svc.get(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return await svc.create(project_id, data)


@router.get("/worldviews/{worldview_id}", response_model=Worldview, tags=["世界观"])
async def get_worldview(
    worldview_id: int, svc: WorldviewService = Depends(get_worldview_service)
):
    """获取世界观条目详情"""
    wv = await svc.get(worldview_id)
    if not wv:
        raise HTTPException(status_code=404, detail="世界观条目不存在")
    return wv


@router.put("/worldviews/{worldview_id}", response_model=Worldview, tags=["世界观"])
async def update_worldview(
    worldview_id: int,
    data: WorldviewUpdate,
    svc: WorldviewService = Depends(get_worldview_service),
):
    """更新世界观条目"""
    wv = await svc.update(worldview_id, data)
    if not wv:
        raise HTTPException(status_code=404, detail="世界观条目不存在")
    return wv


@router.delete("/worldviews/{worldview_id}", tags=["世界观"])
async def delete_worldview(
    worldview_id: int, svc: WorldviewService = Depends(get_worldview_service)
):
    """删除世界观条目"""
    ok = await svc.delete(worldview_id)
    if not ok:
        raise HTTPException(status_code=404, detail="世界观条目不存在")
    return {"message": "已删除"}
