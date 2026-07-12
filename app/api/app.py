"""FastAPI 应用 - 创建应用、挂载静态文件、注册路由"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import AppConfig, load_config
from app.database import Database


# 全局数据库实例（在 lifespan 中初始化）
db: Database = None  # type: ignore
config: AppConfig = None  # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库，关闭时释放连接"""
    global db, config
    config = load_config()
    db = Database(config.database.path)
    await db.connect()
    # 确保导出目录存在
    Path(config.export.output_dir).mkdir(parents=True, exist_ok=True)
    app.state.db = db
    app.state.config = config
    yield
    await db.close()


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
    from app.api.routes import projects, chapters

    app.include_router(projects.router, prefix="/api")
    app.include_router(chapters.router, prefix="/api")


app = create_app()
