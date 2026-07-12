"""LLM 客户端工厂 - 根据配置创建对应类型的客户端"""
from app.config import LLMConfig
from .base import LLMClient
from .openai_client import OpenAICompatClient
from .llama_client import LlamaNativeClient


def create_llm_client(config: LLMConfig) -> LLMClient:
    """根据 config.llm.api_type 创建对应的 LLM 客户端

    参数:
        config: LLM 配置（AppConfig.llm）

    返回:
        LLMClient 实例

    抛出:
        ValueError: 不支持的 api_type
    """
    api_type = config.api_type
    if api_type == "openai_compat":
        return OpenAICompatClient(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
        )
    elif api_type == "llama_native":
        return LlamaNativeClient(
            base_url=config.base_url,
            api_key=config.api_key,
        )
    else:
        raise ValueError(
            f"不支持的 LLM API 类型: {api_type}，"
            f"可选值: openai_compat, llama_native"
        )
