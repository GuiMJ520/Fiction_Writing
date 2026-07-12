"""LLM 客户端手动测试脚本

使用方法：
1. 先启动 llama-server：
   llama-server -m 你的模型路径.gguf --port 8080
2. 复制配置文件（如未做）：
   cp config.example.yaml config.yaml
3. 运行测试：
   python tests/test_llm_manual.py

此脚本会：
- 检查 llama-server 是否在线
- 测试流式对话生成
- 测试 token 计数
"""
import asyncio
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import load_config
from app.llm.factory import create_llm_client
from app.llm.base import ChatMessage, GenerateParams


async def test_openai_compat():
    """测试 OpenAI 兼容客户端"""
    from app.llm.openai_client import OpenAICompatClient
    config = load_config()
    if config.llm.api_type != "openai_compat":
        print("跳过（当前配置不是 openai_compat）")
        return

    print(f"  端点: {config.llm.base_url}/v1/chat/completions")
    print(f"  模型: {config.llm.model}")
    client = OpenAICompatClient(
        base_url=config.llm.base_url,
        model=config.llm.model,
        api_key=config.llm.api_key,
    )
    await _run_tests(client)
    await client.close()


async def test_llama_native():
    """测试 llama.cpp 原生客户端"""
    from app.llm.llama_client import LlamaNativeClient
    config = load_config()
    if config.llm.api_type != "llama_native":
        print("跳过（当前配置不是 llama_native）")
        return

    print(f"  端点: {config.llm.base_url}/completion")
    client = LlamaNativeClient(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
    )
    await _run_tests(client)
    await client.close()


async def _run_tests(client):
    """执行一系列测试"""
    # 1. 健康检查
    print("\n  [1] 健康检查...")
    healthy = await client.health_check()
    if not healthy:
        print("  ✗ LLM 服务不可用，请确认 llama-server 已启动")
        return
    print("  ✓ 服务在线")

    # 2. 流式对话
    print("\n  [2] 流式对话测试...")
    messages = [
        ChatMessage("system", "你是一个小说写作助手，请用中文简短回复。"),
        ChatMessage("user", "请用一句话描述一个修仙者的出场。"),
    ]
    params = GenerateParams(temperature=0.8, max_tokens=100)
    print("  回复: ", end="", flush=True)
    full_text = []
    try:
        async for chunk in client.chat_stream(messages, params):
            print(chunk, end="", flush=True)
            full_text.append(chunk)
        print()
        print(f"  ✓ 流式生成完成（共 {len(''.join(full_text))} 字符）")
    except Exception as e:
        print(f"\n  ✗ 流式生成失败: {e}")
        return

    # 3. 非流式对话
    print("\n  [3] 非流式对话测试...")
    try:
        result = await client.chat(
            [ChatMessage("user", "用一个词形容春天")],
            GenerateParams(max_tokens=20),
        )
        print(f"  回复: {result}")
        print("  ✓ 非流式生成完成")
    except Exception as e:
        print(f"  ✗ 非流式生成失败: {e}")

    # 4. token 计数
    print("\n  [4] Token 计数测试...")
    sample = "这是一段测试文本，用于验证token计数功能。"
    try:
        count = await client.count_tokens(sample)
        print(f"  文本: {sample}")
        print(f"  Token 数: {count}")
        print("  ✓ Token 计数完成")
    except Exception as e:
        print(f"  ✗ Token 计数失败: {e}")


async def main():
    print("=" * 50)
    print("LLM 客户端测试")
    print("=" * 50)

    config = load_config()
    print(f"\n当前 API 类型: {config.llm.api_type}")
    print(f"LLM 地址: {config.llm.base_url}")

    print("\n--- 测试当前配置的客户端 ---")
    print("\n使用工厂创建客户端...")
    client = create_llm_client(config.llm)
    print(f"  客户端类型: {client.__class__.__name__}")
    await _run_tests(client)
    await client.close()

    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
