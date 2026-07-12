"""里程碑1 验证脚本 - 测试数据库初始化和 FastAPI 应用创建"""
import asyncio
from app.database import Database


async def test_database():
    """测试数据库建表"""
    db = Database("data/novels.db")
    await db.connect()
    tables = await db.fetch_all(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = [t["name"] for t in tables]
    print("已建表:", table_names)
    expected = {"projects", "chapters", "characters", "worldviews", "messages", "summaries"}
    assert expected.issubset(set(table_names)), f"缺少表: {expected - set(table_names)}"
    print("✓ 所有 6 张表创建成功")
    await db.close()


def test_app():
    """测试 FastAPI 应用创建"""
    from app.api.app import create_app
    app = create_app()
    print("✓ FastAPI 应用创建成功")
    routes = [r.path for r in app.routes]
    print("路由:", routes)


if __name__ == "__main__":
    print("=== 测试数据库 ===")
    asyncio.run(test_database())
    print("\n=== 测试 FastAPI 应用 ===")
    test_app()
    print("\n✅ 里程碑1 验证通过")
