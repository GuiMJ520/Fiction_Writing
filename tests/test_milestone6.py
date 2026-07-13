"""里程碑6测试：上下文摘要压缩

验证：
1. context-info 端点返回正确的消息计数
2. 消息数未达阈值时压缩返回 False
3. 消息数超阈值时触发压缩流程（LLM 离线时 graceful 失败）
4. 压缩后摘要消息和 summaries 记录正确（需要 LLM 在线，离线时跳过）
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.storage import FileStorage
from app.utils import estimate_tokens

BASE = "http://127.0.0.1:8000/api"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 创建项目
        r = await c.post("/projects", json={"name": "压缩测试项目"})
        proj = r.json()
        pid = proj["id"]
        print(f"[项目] 创建: id={pid}")

        # 1. 初始 context-info（0 条消息）
        r = await c.get(f"/projects/{pid}/context-info")
        info = r.json()
        print(f"[context-info] 初始: {info}")
        assert info["message_count"] == 0
        assert info["has_summary"] is False
        assert info["compress_threshold"] == 30

        # 2. 手动压缩（消息不足，应返回 False）
        r = await c.post(f"/projects/{pid}/compress")
        result = r.json()
        print(f"[压缩] 不足阈值: compressed={result['compressed']}, msg={result['message']}")
        assert result["compressed"] is False

        # 3. 通过 FileStorage 直接插入 35 条消息（超过阈值 30）
        print("\n[插入] 35 条测试消息...")
        storage = FileStorage("data")
        await storage.connect()
        for i in range(35):
            role = "user" if i % 2 == 0 else "assistant"
            content = f"测试消息第{i+1}条，内容内容内容"
            await storage.add_message(
                pid, None, role, content, estimate_tokens(content)
            )
        await storage.close()

        # 4. 验证 context-info 显示 35 条
        r = await c.get(f"/projects/{pid}/context-info")
        info = r.json()
        print(f"[context-info] 35条: count={info['message_count']}, near={info['near_threshold']}")
        assert info["message_count"] == 35
        assert info["near_threshold"] is True

        # 5. 手动压缩（超阈值，LLM 离线时应 graceful 失败）
        r = await c.post(f"/projects/{pid}/compress")
        result = r.json()
        print(f"[压缩] 超阈值: compressed={result['compressed']}, msg={result['message']}")
        # LLM 离线时 compressed=False，但不应报 500 错误
        assert "compressed" in result
        assert r.status_code == 200

        # 6. 如果 LLM 在线，验证压缩后状态
        if result["compressed"]:
            r = await c.get(f"/projects/{pid}/context-info")
            info = r.json()
            print(f"[context-info] 压缩后: count={info['message_count']}, has_summary={info['has_summary']}")
            assert info["has_summary"] is True
            # 35 - 10 (compress_batch) = 25 条非摘要 + 1 条摘要
            assert info["message_count"] == 25

            # 验证 summaries.json 有记录
            import json
            summaries_path = Path(f"data/projects/{pid}/summaries.json")
            if summaries_path.exists():
                summaries = json.loads(summaries_path.read_text(encoding="utf-8"))
                if summaries:
                    s = summaries[-1]
                    print(f"[summaries] 记录: count={s['message_count']}, content={s['content'][:80]}...")
                    assert s["message_count"] == 10  # compress_batch
        else:
            print("[跳过] LLM 离线，压缩逻辑未完整执行（预期行为）")

        # 清理
        await c.delete(f"/projects/{pid}")
        print(f"\n[清理] 删除测试项目 pid={pid}")
        print("\n=== 里程碑6 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
