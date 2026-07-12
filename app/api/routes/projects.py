"""项目路由 - /api/projects"""
from fastapi import APIRouter, Depends, HTTPException

from app.models import Project, ProjectCreate, ProjectUpdate
from app.services.project_service import ProjectService
from app.api.dependencies import get_project_service

router = APIRouter()


@router.get("/projects", response_model=list[Project], tags=["项目"])
async def list_projects(svc: ProjectService = Depends(get_project_service)):
    """列出所有项目"""
    return await svc.list_all()


@router.post("/projects", response_model=Project, tags=["项目"], status_code=201)
async def create_project(
    data: ProjectCreate, svc: ProjectService = Depends(get_project_service)
):
    """创建项目"""
    return await svc.create(data)


@router.get("/projects/{project_id}", response_model=Project, tags=["项目"])
async def get_project(
    project_id: int, svc: ProjectService = Depends(get_project_service)
):
    """获取项目详情"""
    project = await svc.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.put("/projects/{project_id}", response_model=Project, tags=["项目"])
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    svc: ProjectService = Depends(get_project_service),
):
    """更新项目"""
    project = await svc.update(project_id, data)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.delete("/projects/{project_id}", tags=["项目"])
async def delete_project(
    project_id: int, svc: ProjectService = Depends(get_project_service)
):
    """删除项目（关联数据自动级联删除）"""
    ok = await svc.delete(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "已删除"}
