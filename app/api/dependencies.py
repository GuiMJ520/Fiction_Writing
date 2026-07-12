"""FastAPI 依赖注入 - 从 app.state 获取 db，创建 service 实例"""
from fastapi import Request

from app.database import Database
from app.services.project_service import ProjectService
from app.services.chapter_service import ChapterService


def get_db(request: Request) -> Database:
    """获取数据库实例"""
    return request.app.state.db


def get_project_service(request: Request) -> ProjectService:
    """获取项目服务实例"""
    return ProjectService(request.app.state.db)


def get_chapter_service(request: Request) -> ChapterService:
    """获取章节服务实例"""
    return ChapterService(request.app.state.db)
