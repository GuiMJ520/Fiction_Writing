"""角色路由 - /api/projects/{pid}/characters 和 /api/characters/{id}"""
from fastapi import APIRouter, Depends, HTTPException

from app.models import Character, CharacterCreate, CharacterUpdate
from app.services.character_service import CharacterService
from app.services.project_service import ProjectService
from app.api.dependencies import get_character_service, get_project_service

router = APIRouter()


@router.get(
    "/projects/{project_id}/characters",
    response_model=list[Character],
    tags=["角色"],
)
async def list_characters(
    project_id: int, svc: CharacterService = Depends(get_character_service)
):
    """列出项目下所有角色"""
    return await svc.list_by_project(project_id)


@router.post(
    "/projects/{project_id}/characters",
    response_model=Character,
    tags=["角色"],
    status_code=201,
)
async def create_character(
    project_id: int,
    data: CharacterCreate,
    svc: CharacterService = Depends(get_character_service),
    project_svc: ProjectService = Depends(get_project_service),
):
    """创建角色卡"""
    if not await project_svc.get(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return await svc.create(project_id, data)


@router.get("/characters/{character_id}", response_model=Character, tags=["角色"])
async def get_character(
    character_id: int, svc: CharacterService = Depends(get_character_service)
):
    """获取角色详情"""
    char = await svc.get(character_id)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    return char


@router.put("/characters/{character_id}", response_model=Character, tags=["角色"])
async def update_character(
    character_id: int,
    data: CharacterUpdate,
    svc: CharacterService = Depends(get_character_service),
):
    """更新角色卡"""
    char = await svc.update(character_id, data)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    return char


@router.delete("/characters/{character_id}", tags=["角色"])
async def delete_character(
    character_id: int, svc: CharacterService = Depends(get_character_service)
):
    """删除角色"""
    ok = await svc.delete(character_id)
    if not ok:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"message": "已删除"}
