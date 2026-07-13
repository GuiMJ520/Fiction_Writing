"""FastAPI 依赖注入 - 从 app.state 获取 service 实例"""
from fastapi import Request

from app.storage import FileStorage
from app.llm.base import LLMClient
from app.services.project_service import ProjectService
from app.services.chapter_service import ChapterService
from app.services.character_service import CharacterService
from app.services.worldview_service import WorldviewService
from app.services.chat_service import ChatService
from app.services.export_service import ExportService


def get_storage(request: Request) -> FileStorage:
    return request.app.state.storage


def get_llm_client(request: Request) -> LLMClient:
    return request.app.state.llm_client


def get_project_service(request: Request) -> ProjectService:
    return ProjectService(request.app.state.storage)


def get_chapter_service(request: Request) -> ChapterService:
    return ChapterService(request.app.state.storage)


def get_character_service(request: Request) -> CharacterService:
    return CharacterService(request.app.state.storage)


def get_worldview_service(request: Request) -> WorldviewService:
    return WorldviewService(request.app.state.storage)


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_export_service(request: Request) -> ExportService:
    return ExportService(request.app.state.storage)
