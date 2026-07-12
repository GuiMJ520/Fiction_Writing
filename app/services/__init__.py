"""Service 层入口 - 提供 create_services() 工厂函数

GUI 可直接调用此函数创建所有 service，无需经过 FastAPI。
"""
from dataclasses import dataclass

from app.config import AppConfig
from app.database import Database
from app.llm.factory import create_llm_client
from .project_service import ProjectService
from .chapter_service import ChapterService


@dataclass
class Services:
    """所有 service 的容器"""
    project_service: ProjectService
    chapter_service: ChapterService


def create_services(config: AppConfig) -> Services:
    """根据配置创建所有 service 实例

    GUI 层调用示例：
        config = load_config()
        services = create_services(config)
        project = await services.project_service.create(...)
    """
    db = Database(config.database.path)
    # 注意：GUI 使用时需要自行 await db.connect()
    return Services(
        project_service=ProjectService(db),
        chapter_service=ChapterService(db),
    )
