"""创建浏览器测试用的项目数据"""
import httpx
import asyncio

BASE = "http://127.0.0.1:8000/api"


async def main():
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.post("/projects", json={"name": "浏览器测试小说", "genre": "玄幻"})
        p = r.json()
        print(f"项目 id={p['id']}, name={p['name']}")

        r = await c.post(f"/projects/{p['id']}/chapters", json={"title": "第一章 风起"})
        ch = r.json()
        print(f"章节 id={ch['id']}, title={ch['title']}")

        await c.put(f"/chapters/{ch['id']}", json={"content": "风从东方来，吹动了少年的衣角。他望向远方的山峦，心中充满了期待。"})
        print("已写入章节内容")


if __name__ == "__main__":
    asyncio.run(main())
