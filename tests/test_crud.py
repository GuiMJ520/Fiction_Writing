"""里程碑3 测试 - 项目和章节 CRUD

直接测试 service 层（不经过 HTTP），验证数据库操作正确。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database
from app.services.project_service import ProjectService
from app.services.chapter_service import ChapterService
from app.models import ProjectCreate, ProjectUpdate, ChapterCreate, ChapterUpdate


async def test_project_crud():
    """测试项目 CRUD"""
    print("\n=== 项目 CRUD 测试 ===")
    db = Database("data/test_crud.db")
    await db.connect()
    svc = ProjectService(db)

    # 清空旧数据（测试用）
    await db.execute("DELETE FROM projects")

    # 1. 创建
    print("[1] 创建项目...")
    project = await svc.create(ProjectCreate(
        name="测试小说",
        description="一个测试项目",
        genre="玄幻",
        system_prompt="你是写作助手",
    ))
    assert project.id is not None
    assert project.name == "测试小说"
    print(f"  ✓ 创建成功，id={project.id}, name={project.name}")

    # 2. 获取
    print("[2] 获取项目...")
    fetched = await svc.get(project.id)
    assert fetched is not None
    assert fetched.name == "测试小说"
    assert fetched.genre == "玄幻"
    print(f"  ✓ 获取成功: {fetched.name} ({fetched.genre})")

    # 3. 列出
    print("[3] 列出项目...")
    project2 = await svc.create(ProjectCreate(name="第二本书"))
    projects = await svc.list_all()
    assert len(projects) >= 2
    print(f"  ✓ 列出 {len(projects)} 个项目")

    # 4. 更新
    print("[4] 更新项目...")
    updated = await svc.update(project.id, ProjectUpdate(
        name="修改后的标题",
        description="新描述",
    ))
    assert updated.name == "修改后的标题"
    assert updated.description == "新描述"
    print(f"  ✓ 更新成功: {updated.name}")

    # 5. 删除
    print("[5] 删除项目...")
    ok = await svc.delete(project.id)
    assert ok
    assert await svc.get(project.id) is None
    print(f"  ✓ 删除成功")

    # 清理
    await svc.delete(project2.id)
    await db.close()
    print("\n✅ 项目 CRUD 测试通过")


async def test_chapter_crud():
    """测试章节 CRUD"""
    print("\n=== 章节 CRUD 测试 ===")
    db = Database("data/test_crud.db")
    await db.connect()
    project_svc = ProjectService(db)
    chapter_svc = ChapterService(db)

    # 清空旧数据
    await db.execute("DELETE FROM projects")

    # 先创建项目
    project = await project_svc.create(ProjectCreate(name="章节测试项目"))

    # 1. 创建章节（自动 order）
    print("[1] 创建章节（自动排序）...")
    ch1 = await chapter_svc.create(project.id, ChapterCreate(title="第一章"))
    ch2 = await chapter_svc.create(project.id, ChapterCreate(title="第二章"))
    ch3 = await chapter_svc.create(project.id, ChapterCreate(title="第三章"))
    assert ch1.chapter_order == 1
    assert ch2.chapter_order == 2
    assert ch3.chapter_order == 3
    print(f"  ✓ 三个章节创建成功，order: {ch1.chapter_order}, {ch2.chapter_order}, {ch3.chapter_order}")

    # 2. 列出章节
    print("[2] 列出章节...")
    chapters = await chapter_svc.list_by_project(project.id)
    assert len(chapters) == 3
    print(f"  ✓ 列出 {len(chapters)} 个章节")

    # 3. 更新章节内容
    print("[3] 更新章节内容...")
    updated = await chapter_svc.update(ch1.id, ChapterUpdate(
        content="这是第一章的正文内容，包含一些文字。",
        status="writing",
    ))
    assert updated.content == "这是第一章的正文内容，包含一些文字。"
    assert updated.status == "writing"
    assert updated.word_count > 0
    print(f"  ✓ 更新成功，字数: {updated.word_count}")

    # 4. 更新标题
    print("[4] 更新章节标题...")
    updated = await chapter_svc.update(ch1.id, ChapterUpdate(title="序章"))
    assert updated.title == "序章"
    print(f"  ✓ 标题更新为: {updated.title}")

    # 5. 重新排序
    print("[5] 重新排序章节...")
    await chapter_svc.reorder(project.id, [ch3.id, ch1.id, ch2.id])
    chapters = await chapter_svc.list_by_project(project.id)
    assert chapters[0].id == ch3.id
    assert chapters[1].id == ch1.id
    assert chapters[2].id == ch2.id
    print(f"  ✓ 顺序已调整: {[c.title for c in chapters]}")

    # 6. 删除章节
    print("[6] 删除章节...")
    ok = await chapter_svc.delete(ch2.id)
    assert ok
    chapters = await chapter_svc.list_by_project(project.id)
    assert len(chapters) == 2
    print(f"  ✓ 删除后剩余 {len(chapters)} 个章节")

    # 7. 级联删除（删项目后章节应自动删除）
    print("[7] 测试级联删除...")
    await project_svc.delete(project.id)
    chapters = await chapter_svc.list_by_project(project.id)
    assert len(chapters) == 0
    print(f"  ✓ 删除项目后章节自动清空: {len(chapters)} 个")

    await db.close()
    print("\n✅ 章节 CRUD 测试通过")


async def main():
    print("=" * 50)
    print("里程碑3：CRUD 测试")
    print("=" * 50)
    await test_project_crud()
    await test_chapter_crud()
    print("\n" + "=" * 50)
    print("✅ 所有 CRUD 测试通过")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
