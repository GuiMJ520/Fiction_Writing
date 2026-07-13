"""里程碑1 验证脚本 - 测试文件系统存储初始化和 FastAPI 应用创建"""
import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage import FileStorage

TEST_DIR = "data/test_milestone1"


async def test_storage():
    """测试文件系统存储初始化"""
    # 清理旧数据
    test_path = Path(TEST_DIR)
    if test_path.exists():
        shutil.rmtree(test_path)

    storage = FileStorage(TEST_DIR)
    await storage.connect()

    # 验证目录结构
    assert (test_path / "index.json").exists(), "index.json 未创建"
    assert (test_path / "projects").exists(), "projects 目录未创建"
    print("✓ 目录结构创建成功")

    # 验证 index.json 内容
    import json
    index = json.loads((test_path / "index.json").read_text(encoding="utf-8"))
    assert "next_project_id" in index
    assert "chapter_to_project" in index
    print("✓ index.json 结构正确")

    # 创建测试项目验证完整流程
    project = await storage.create_project({
        "name": "测试项目",
        "genre": "玄幻",
        "description": "测试描述",
    })
    assert project["id"] == 1
    assert project["name"] == "测试项目"

    pdir = test_path / "projects" / "1"
    assert (pdir / "project.json").exists()
    assert (pdir / "chapters" / "chapters.json").exists()
    assert (pdir / "characters.json").exists()
    assert (pdir / "worldviews.json").exists()
    assert (pdir / "messages.json").exists()
    assert (pdir / "summaries.json").exists()
    print("✓ 项目创建及所有 JSON 文件生成成功")

    await storage.close()

    # 清理
    if test_path.exists():
        shutil.rmtree(test_path)
    print("✓ 文件系统存储测试通过")


def test_app():
    """测试 FastAPI 应用创建"""
    from app.api.app import create_app
    app = create_app()
    print("✓ FastAPI 应用创建成功")
    routes = [getattr(r, 'path', str(r)) for r in app.routes]
    print(f"  路由数: {len(routes)}")


if __name__ == "__main__":
    print("=== 测试文件系统存储 ===")
    asyncio.run(test_storage())
    print("\n=== 测试 FastAPI 应用 ===")
    test_app()
    print("\n✅ 里程碑1 验证通过")
