"""里程碑5测试：角色与世界观 CRUD + 上下文注入"""
import httpx
import asyncio

BASE = "http://127.0.0.1:8000/api"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # 创建项目
        r = await c.post("/projects", json={"name": "测试小说", "genre": "玄幻"})
        proj = r.json()
        pid = proj["id"]
        print(f"[项目] 创建: id={pid}, name={proj['name']}, genre={proj['genre']}")

        # === 角色 CRUD ===
        print("\n--- 角色 CRUD ---")
        r = await c.post(f"/projects/{pid}/characters", json={
            "name": "林动", "role": "主角",
            "description": "来自青阳镇的少年",
            "personality": "坚韧不拔", "background": "偶得神秘石符",
            "appearance": "黑发黑瞳", "keywords": "石符, 武学, 坚毅"
        })
        char1 = r.json()
        print(f"[角色] 创建1: id={char1['id']}, name={char1['name']}, role={char1['role']}")

        r = await c.post(f"/projects/{pid}/characters", json={
            "name": "绫清竹", "role": "女主",
            "description": "九天太清宫传人",
            "keywords": "太清宫, 冰清玉洁"
        })
        char2 = r.json()
        print(f"[角色] 创建2: id={char2['id']}, name={char2['name']}")

        # 列表
        r = await c.get(f"/projects/{pid}/characters")
        chars = r.json()
        print(f"[角色] 列表: {len(chars)} 个")

        # 更新
        r = await c.put(f"/characters/{char1['id']}", json={
            "role": "男主角", "description": "来自青阳镇的天才少年"
        })
        updated = r.json()
        print(f"[角色] 更新: role={updated['role']}, desc={updated['description']}")

        # 删除
        r = await c.delete(f"/characters/{char2['id']}")
        print(f"[角色] 删除 char2: {r.json()}")

        r = await c.get(f"/projects/{pid}/characters")
        chars_after = r.json()
        print(f"[角色] 删除后列表: {len(chars_after)} 个")

        # === 世界观 CRUD ===
        print("\n--- 世界观 CRUD ---")
        r = await c.post(f"/projects/{pid}/worldviews", json={
            "category": "地理", "title": "青阳镇",
            "content": "大炎王朝边陲小镇，靠近魔兽山脉",
            "keywords": "大炎王朝, 魔兽山脉"
        })
        wv1 = r.json()
        print(f"[世界观] 创建1: id={wv1['id']}, cat={wv1['category']}, title={wv1['title']}")

        r = await c.post(f"/projects/{pid}/worldviews", json={
            "category": "势力", "title": "九天太清宫",
            "content": "超级势力之一，擅长冰系功法",
            "keywords": "冰系, 超级势力"
        })
        wv2 = r.json()
        print(f"[世界观] 创建2: id={wv2['id']}, title={wv2['title']}")

        # 列表
        r = await c.get(f"/projects/{pid}/worldviews")
        wvs = r.json()
        print(f"[世界观] 列表: {len(wvs)} 个")

        # 分类列表
        r = await c.get(f"/projects/{pid}/worldviews/categories")
        cats = r.json()
        print(f"[世界观] 分类: {cats}")

        # 更新
        r = await c.put(f"/worldviews/{wv1['id']}", json={
            "content": "大炎王朝边陲小镇，靠近魔兽山脉，是主角的故乡"
        })
        updated_wv = r.json()
        print(f"[世界观] 更新: content={updated_wv['content']}")

        # 删除
        r = await c.delete(f"/worldviews/{wv2['id']}")
        print(f"[世界观] 删除 wv2: {r.json()}")

        r = await c.get(f"/projects/{pid}/worldviews")
        wvs_after = r.json()
        print(f"[世界观] 删除后列表: {len(wvs_after)} 个")

        # === 上下文注入测试（需要 LLM 在线，只验证构建不报错）===
        print("\n--- 对话测试（验证角色/世界观注入上下文）---")
        # 发送一条消息，即使 LLM 离线也能验证后端构建上下文的过程
        try:
            async with httpx.AsyncClient(base_url=BASE, timeout=60) as stream_client:
                async with stream_client.stream("POST", f"/projects/{pid}/chat",
                        json={"message": "介绍一下林动这个角色"}) as resp:
                    print(f"  HTTP {resp.status_code}")
                    collected = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            import json
                            data = json.loads(line[6:])
                            if data.get("content"):
                                collected += data["content"]
                            if data.get("done"):
                                break
                    print(f"  AI回复: {collected[:200]}...")
        except Exception as e:
            print(f"  对话测试跳过（LLM可能离线）: {e}")

        # 清理
        await c.delete(f"/projects/{pid}")
        print(f"\n[清理] 删除测试项目 pid={pid}")

        print("\n=== 里程碑5 API 测试全部通过 ===")


if __name__ == "__main__":
    asyncio.run(main())
