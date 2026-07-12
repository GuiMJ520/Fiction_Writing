"""LLM 客户端导入和实例化测试（不需要 llama-server）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import load_config, LLMConfig
from app.llm.base import LLMClient, ChatMessage, GenerateParams
from app.llm.openai_client import OpenAICompatClient
from app.llm.llama_client import LlamaNativeClient
from app.llm.factory import create_llm_client


def test_imports():
    """测试所有模块能正确导入"""
    print("✓ 所有模块导入成功")


def test_chat_message():
    """测试 ChatMessage 数据类"""
    msg = ChatMessage("user", "你好")
    assert msg.role == "user"
    assert msg.content == "你好"
    assert msg.to_dict() == {"role": "user", "content": "你好"}
    print("✓ ChatMessage 数据类正常")


def test_generate_params():
    """测试 GenerateParams 默认值"""
    p = GenerateParams()
    assert p.temperature == 0.8
    assert p.max_tokens == 2048
    assert p.grammar is None
    p2 = GenerateParams(temperature=0.5, grammar="root ::= [a-z]+")
    assert p2.temperature == 0.5
    assert p2.grammar == "root ::= [a-z]+"
    print("✓ GenerateParams 参数正常")


def test_factory_openai():
    """测试工厂创建 OpenAI 客户端"""
    config = LLMConfig(api_type="openai_compat", base_url="http://localhost:8080", model="test")
    client = create_llm_client(config)
    assert isinstance(client, OpenAICompatClient)
    assert client.base_url == "http://localhost:8080"
    assert client.model == "test"
    print("✓ 工厂创建 OpenAICompatClient 正常")


def test_factory_llama():
    """测试工厂创建 llama.cpp 客户端"""
    config = LLMConfig(api_type="llama_native", base_url="http://localhost:8080")
    client = create_llm_client(config)
    assert isinstance(client, LlamaNativeClient)
    assert client.base_url == "http://localhost:8080"
    print("✓ 工厂创建 LlamaNativeClient 正常")


def test_factory_invalid():
    """测试工厂对无效类型的处理"""
    config = LLMConfig(api_type="invalid_type", base_url="http://localhost:8080")
    try:
        create_llm_client(config)
        assert False, "应抛出 ValueError"
    except ValueError as e:
        assert "invalid_type" in str(e)
        print("✓ 工厂对无效类型正确抛出异常")


def test_messages_to_prompt():
    """测试 llama_native 的消息转 prompt"""
    client = LlamaNativeClient("http://localhost:8080")
    messages = [
        ChatMessage("system", "你是助手"),
        ChatMessage("user", "你好"),
    ]
    prompt = client._messages_to_prompt(messages)
    assert "<|im_start|>system" in prompt
    assert "你是助手" in prompt
    assert "<|im_start|>user" in prompt
    assert "你好" in prompt
    assert prompt.endswith("<|im_start|>assistant\n")
    print("✓ 消息转 ChatML prompt 正常")


def test_openai_payload():
    """测试 OpenAI 客户端的 payload 构建"""
    client = OpenAICompatClient("http://localhost:8080", "test-model")
    messages = [ChatMessage("user", "你好")]
    params = GenerateParams(temperature=0.5, max_tokens=50)
    payload = client._build_payload(messages, params, stream=True)
    assert payload["model"] == "test-model"
    assert payload["messages"] == [{"role": "user", "content": "你好"}]
    assert payload["temperature"] == 0.5
    assert payload["max_tokens"] == 50
    assert payload["stream"] is True
    assert payload["cache_prompt"] is True
    print("✓ OpenAI payload 构建正常")


def test_llama_payload():
    """测试 llama.cpp 客户端的 payload 构建"""
    client = LlamaNativeClient("http://localhost:8080")
    params = GenerateParams(max_tokens=100, grammar="root ::= [a-z]+")
    payload = client._build_payload("test prompt", params, stream=False)
    assert payload["prompt"] == "test prompt"
    assert payload["n_predict"] == 100  # llama.cpp 用 n_predict
    assert payload["grammar"] == "root ::= [a-z]+"
    assert payload["stream"] is False
    print("✓ llama.cpp payload 构建正常（含 grammar）")


if __name__ == "__main__":
    print("=== LLM 客户端单元测试 ===\n")
    test_imports()
    test_chat_message()
    test_generate_params()
    test_factory_openai()
    test_factory_llama()
    test_factory_invalid()
    test_messages_to_prompt()
    test_openai_payload()
    test_llama_payload()
    print(f"\n✅ 所有单元测试通过")
