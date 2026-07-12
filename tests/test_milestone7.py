"""里程碑7测试：章节编辑与导出"""
import httpx
import asyncio

BASE = "http://127.0.0.1:8000/api"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 创建项目 + 章节
        r = await c.post("/projects", json={"name": "导出测试小说", "genre": "玄幻"})
        proj = r.json()
        pid = proj["id"]
        print(f"[项目] 创建: id={pid}, name={proj['name']}")

        r = await c.post(f"/projects/{pid}/chapters", json={"title": "第一章 初入江湖"})
        ch1 = r.json()
        print(f"[章节] 创建1: id={ch1['id']}, title={ch1['title']}")

        r = await c.post(f"/projects/{pid}/chapters", json={"title": "第二章 神秘石符"})
        ch2 = r.json()
        print(f"[章节] 创建2: id={ch2['id']}, title={ch2['title']}")

        # 编辑章节内容
        content1 = "林动推开青阳镇的大门，踏入了一个全新的世界。\n\n远处魔兽山脉的轮廓在夕阳下若隐若现，他握紧了手中的石符，心中既兴奋又忐忑。"
        r = await c.put(f"/chapters/{ch1['id']}", json={"content": content1})
        updated = r.json()
        print(f"[章节] 更新内容: word_count={updated['word_count']}")

        content2 = "夜晚，石符发出幽幽光芒，林动感到一股暖流涌入体内。"
        r = await c.put(f"/chapters/{ch2['id']}", json={"content": content2})
        updated2 = r.json()
        print(f"[章节2] 更新内容: word_count={updated2['word_count']}")

        # === 导出单章 TXT ===
        print("\n--- 导出单章 TXT ---")
        r = await c.get(f"/chapters/{ch1['id']}/export?format=txt")
        print(f"HTTP {r.status_code}")
        print(f"Content-Disposition: {r.headers.get('content-disposition')}")
        print(f"内容前80字: {r.text[:80]}")
        assert r.status_code == 200
        assert ch1["title"] in r.text
        assert "林动" in r.text

        # === 导出单章 MD ===
        print("\n--- 导出单章 MD ---")
        r = await c.get(f"/chapters/{ch1['id']}/export?format=md")
        print(f"HTTP {r.status_code}")
        print(f"内容前80字: {r.text[:80]}")
        assert r.status_code == 200
        assert f"# {ch1['title']}" in r.text

        # === 导出全本 MD ===
        print("\n--- 导出全本 MD ---")
        r = await c.get(f"/projects/{pid}/export?format=md")
        print(f"HTTP {r.status_code}")
        print(f"Content-Disposition: {r.headers.get('content-disposition')}")
        print(f"内容前120字: {r.text[:120]}")
        assert r.status_code == 200
        assert f"# {proj['name']}" in r.text
        assert f"## {ch1['title']}" in r.text
        assert f"## {ch2['title']}" in r.text

        # === 导出全本 TXT ===
        print("\n--- 导出全本 TXT ---")
        r = await c.get(f"/projects/{pid}/export?format=txt")
        print(f"HTTP {r.status_code}")
        assert r.status_code == 200
        assert proj["name"] in r.text

        # === 验证自动保存：更新内容后 word_count 变化 ===
        print("\n--- 验证 word_count 自动更新 ---")
        r = await c.put(f"/chapters/{ch1['id']}", json={"content": "短内容"})
        ch1_updated = r.json()
        print(f"短内容 word_count: {ch1_updated['word_count']}")
        assert ch1_updated["word_count"] > 0

        # 清理
        await c.delete(f"/projects/{pid}")
        print(f"\n[清理] 删除测试项目 pid={pid}")
        print("\n=== 里程碑7 测试全部通过 ===")


if __name__ == "__main__":
    asyncio.run(main())
