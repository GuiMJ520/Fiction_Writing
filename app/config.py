"""配置加载模块 - 从 YAML 文件加载配置并校验"""
from pathlib import Path
import yaml
from pydantic import BaseModel, Field


class GenerationParams(BaseModel):
    """LLM 生成参数"""
    temperature: float = 0.8
    max_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1
    seed: int = -1


class LLMConfig(BaseModel):
    """LLM 客户端配置"""
    api_type: str = "openai_compat"  # openai_compat | llama_native
    base_url: str = "http://127.0.0.1:8080"
    model: str = ""
    api_key: str = ""
    generation: GenerationParams = Field(default_factory=GenerationParams)


class StorageConfig(BaseModel):
    """文件系统存储配置"""
    data_dir: str = "data"


class ContextConfig(BaseModel):
    """上下文记忆管理配置"""
    window_size: int = 20          # 滑动窗口：保留最近 N 条消息
    compress_threshold: int = 30   # 消息数超过此值触发压缩
    compress_batch: int = 10       # 每次压缩 N 条旧消息
    max_context_tokens: int = 4096 # 上下文最大 token 数


class ServerConfig(BaseModel):
    """Web 服务器配置"""
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    open_browser: bool = True      # 启动时自动打开浏览器


class ExportConfig(BaseModel):
    """导出配置"""
    output_dir: str = "data/exports"


class AppConfig(BaseModel):
    """应用总配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)


def load_config(path: str = "config.yaml") -> AppConfig:
    """从 YAML 文件加载配置。文件不存在时返回默认配置（便于首次启动）"""
    config_path = Path(path)
    if not config_path.exists():
        # 配置文件不存在时，尝试从 example 加载，否则用默认值
        example_path = Path("config.example.yaml")
        if example_path.exists():
            config_path = example_path
        else:
            return AppConfig()
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AppConfig(**data)
