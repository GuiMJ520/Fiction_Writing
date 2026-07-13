"""AI小说写作 - 启动入口"""
import uvicorn
from app.config import load_config


def main():
    config = load_config()
    print(f"AI小说写作服务启动中...")
    print(f"  监听: http://{config.server.host}:{config.server.port}")
    print(f"  LLM: {config.llm.base_url} ({config.llm.api_type})")
    print(f"  数据目录: {config.storage.data_dir}")
    if config.server.open_browser:
        print(f"  将自动打开浏览器")
    uvicorn.run(
        "app.api.app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
    )


if __name__ == "__main__":
    main()
