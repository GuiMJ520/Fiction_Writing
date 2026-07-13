"""Service 层入口 - 提供 create_services() 工厂函数

GUI 可直接调用此函数创建所有 service，无需经过 FastAPI。
"""
from dataclasses import dataclass

from app.config import AppConfig
from app.storage import FileStorage
from app.llm.factory import create_llm_client
from .project_service import ProjectService
from .chapter_service import ChapterService
from .context_manager import ContextManager
from .chat_service import ChatService


@dataclass
class Services:
    """所有 service 的容器"""
    project_service: ProjectService
    chapter_service: ChapterService
    chat_service: ChatService
    storage: FileStorage
    llm_client: object  # LLMClient 实例


async def create_services(config: AppConfig) -> Services:
    """根据配置创建所有 service 实例并初始化存储

    GUI 层调用示例：
        config = load_config()
        services = await create_services(config)
        project = await services.project_service.create(...)
        # 使用完毕后
        await services.storage.close()
    """
    storage = FileStorage(config.storage.data_dir)
    await storage.connect()
    llm_client = create_llm_client(config.llm)
    context_manager = ContextManager(storage, llm_client, config.context)
    return Services(
        project_service=ProjectService(storage),
        chapter_service=ChapterService(storage),
        chat_service=ChatService(storage, llm_client, context_manager, config.context),
        storage=storage,
        llm_client=llm_client,
    )
