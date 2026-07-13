"""项目服务 - 小说项目的 CRUD 操作"""
from app.storage import FileStorage
from app.models import Project, ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, storage: FileStorage):
        self.storage = storage

    async def create(self, data: ProjectCreate) -> Project:
        """创建项目"""
        project = await self.storage.create_project(data.model_dump())
        return Project(**project)

    async def get(self, project_id: int) -> Project | None:
        """获取单个项目"""
        row = await self.storage.get_project(project_id)
        return Project(**row) if row else None

    async def list_all(self) -> list[Project]:
        """列出所有项目"""
        rows = await self.storage.list_projects()
        return [Project(**r) for r in rows]

    async def update(self, project_id: int, data: ProjectUpdate) -> Project | None:
        """更新项目（只更新非 None 字段）"""
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(project_id)
        row = await self.storage.update_project(project_id, fields)
        return Project(**row) if row else None

    async def delete(self, project_id: int) -> bool:
        """删除项目（关联数据通过文件夹删除自动清理）"""
        return await self.storage.delete_project(project_id)
