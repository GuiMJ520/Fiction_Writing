"""Pydantic 数据模型 - 既是数据模型也是 API schema"""
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# 基础实体模型
# ============================================

class Project(BaseModel):
    """小说项目"""
    id: int | None = None
    name: str
    description: str = ""
    genre: str = ""
    system_prompt: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class Chapter(BaseModel):
    """章节"""
    id: int | None = None
    project_id: int
    title: str
    content: str = ""
    chapter_order: int = 0
    status: str = "draft"  # draft / writing / completed
    summary: str = ""
    word_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class Character(BaseModel):
    """角色卡"""
    id: int | None = None
    project_id: int
    name: str
    role: str = ""  # 主角 / 配角 / 反派 / NPC
    description: str = ""
    personality: str = ""
    background: str = ""
    appearance: str = ""
    keywords: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class Worldview(BaseModel):
    """世界观条目"""
    id: int | None = None
    project_id: int
    category: str = "其他"  # 地理 / 历史 / 势力 / 规则 / 物品 / 种族
    title: str
    content: str
    keywords: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class Message(BaseModel):
    """对话消息"""
    id: int | None = None
    project_id: int
    chapter_id: int | None = None
    role: str  # system / user / assistant
    content: str
    token_count: int = 0
    is_summary: bool = False
    created_at: str | None = None


class Summary(BaseModel):
    """摘要记录"""
    id: int | None = None
    project_id: int
    chapter_id: int | None = None
    content: str
    summarized_msg_ids: list[int] = Field(default_factory=list)
    message_count: int = 0
    token_count: int = 0
    created_at: str | None = None


# ============================================
# API 请求模型
# ============================================

class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str
    description: str = ""
    genre: str = ""
    system_prompt: str = ""


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: str | None = None
    description: str | None = None
    genre: str | None = None
    system_prompt: str | None = None


class ChapterCreate(BaseModel):
    """创建章节请求"""
    title: str
    chapter_order: int | None = None


class ChapterUpdate(BaseModel):
    """更新章节请求"""
    title: str | None = None
    content: str | None = None
    status: str | None = None
    summary: str | None = None


class CharacterCreate(BaseModel):
    """创建角色请求"""
    name: str
    role: str = ""
    description: str = ""
    personality: str = ""
    background: str = ""
    appearance: str = ""
    keywords: str = ""


class CharacterUpdate(BaseModel):
    """更新角色请求"""
    name: str | None = None
    role: str | None = None
    description: str | None = None
    personality: str | None = None
    background: str | None = None
    appearance: str | None = None
    keywords: str | None = None


class WorldviewCreate(BaseModel):
    """创建世界观条目请求"""
    category: str = "其他"
    title: str
    content: str
    keywords: str = ""


class WorldviewUpdate(BaseModel):
    """更新世界观条目请求"""
    category: str | None = None
    title: str | None = None
    content: str | None = None
    keywords: str | None = None


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    chapter_id: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    context_window: int | None = None  # 覆盖默认滑动窗口大小
