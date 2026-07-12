"""项目服务 - 小说项目的 CRUD 操作"""
from app.database import Database
from app.models import Project, ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: Database):
        self.db = db

    async def create(self, data: ProjectCreate) -> Project:
        """创建项目"""
        cursor = await self.db.execute(
            """INSERT INTO projects (name, description, genre, system_prompt)
               VALUES (?, ?, ?, ?)""",
            (data.name, data.description, data.genre, data.system_prompt),
        )
        project_id = cursor.lastrowid
        return await self.get(project_id)  # type: ignore

    async def get(self, project_id: int) -> Project | None:
        """获取单个项目"""
        row = await self.db.fetch_one(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        )
        return Project(**row) if row else None

    async def list_all(self) -> list[Project]:
        """列出所有项目"""
        rows = await self.db.fetch_all(
            "SELECT * FROM projects ORDER BY updated_at DESC"
        )
        return [Project(**r) for r in rows]

    async def update(self, project_id: int, data: ProjectUpdate) -> Project | None:
        """更新项目（只更新非 None 字段）"""
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(project_id)
        set_clauses = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [project_id]
        await self.db.execute(
            f"UPDATE projects SET {set_clauses}, "
            f"updated_at = datetime('now','localtime') WHERE id = ?",
            tuple(values),
        )
        return await self.get(project_id)

    async def delete(self, project_id: int) -> bool:
        """删除项目（关联数据通过 ON DELETE CASCADE 自动删除）"""
        cursor = await self.db.execute(
            "DELETE FROM projects WHERE id = ?", (project_id,)
        )
        return cursor.rowcount > 0
