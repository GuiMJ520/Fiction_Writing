"""FastAPI 应用 - 创建应用、挂载静态文件、注册路由"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import AppConfig, load_config
from app.database import Database
from app.llm.factory import create_llm_client
from app.services.context_manager import ContextManager
from app.services.chat_service import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和 LLM 客户端，关闭时释放连接"""
    config = load_config()
    db = Database(config.database.path)
    await db.connect()
    Path(config.export.output_dir).mkdir(parents=True, exist_ok=True)

    # 创建 LLM 客户端和对话服务
    llm_client = create_llm_client(config.llm)
    context_manager = ContextManager(db, llm_client, config.context)
    chat_service = ChatService(db, llm_client, context_manager, config.context)

    app.state.db = db
    app.state.config = config
    app.state.llm_client = llm_client
    app.state.chat_service = chat_service
    yield
    await db.close()
    await llm_client.close()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="AI小说写作",
        description="基于本地大语言模型的 AI 辅助小说写作工具",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 静态文件挂载
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 健康检查
    @app.get("/api/health")
    async def health():
        return {"status": "ok", "service": "ai-novel-writer"}

    # 根路径返回前端页面
    @app.get("/")
    async def index():
        index_path = Path(__file__).parent.parent.parent / "static" / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"message": "AI小说写作服务正在运行，但前端页面未找到"}

    # 注册路由（后续里程碑逐步添加）
    _register_routes(app)
    return app


def _register_routes(app: FastAPI) -> None:
    """注册所有 API 路由"""
    from app.api.routes import projects, chapters, characters, worldviews, chat, export

    app.include_router(projects.router, prefix="/api")
    app.include_router(chapters.router, prefix="/api")
    app.include_router(characters.router, prefix="/api")
    app.include_router(worldviews.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(export.router, prefix="/api")


app = create_app()
