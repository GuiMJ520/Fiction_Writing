"""文件系统存储 - 替代 SQLite 的 JSON + Markdown 存储

数据结构：
    data/
    ├── index.json              # 全局 ID 计数器 + 实体到项目的映射
    └── projects/
        └── {project_id}/
            ├── project.json
            ├── chapters/
            │   ├── chapters.json       # 章节元数据列表
            │   └── {id:04d}_{title}.md # 章节正文
            ├── characters.json
            ├── worldviews.json
            ├── messages.json
            └── summaries.json
"""
import json
import os
import re
import shutil
import asyncio
from pathlib import Path
from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_title(title: str) -> str:
    """清理标题使其可作为文件名的一部分"""
    if not title:
        return ""
    cleaned = _ILLEGAL_FILENAME_CHARS.sub("_", title).strip()
    return cleaned[:50]  # 限制长度


class FileStorage:
    """异步文件系统存储"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.projects_dir = self.data_dir / "projects"
        self.index_path = self.data_dir / "index.json"
        self._lock = asyncio.Lock()
        self._index: dict = {}

    async def connect(self) -> None:
        """初始化目录结构和索引文件"""
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        if self.index_path.exists():
            try:
                self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._index = self._default_index()
                self._save_index_sync()
        else:
            self._index = self._default_index()
            self._save_index_sync()

    async def close(self) -> None:
        pass

    @staticmethod
    def _default_index() -> dict:
        return {
            "next_project_id": 1,
            "next_chapter_id": 1,
            "next_character_id": 1,
            "next_worldview_id": 1,
            "next_message_id": 1,
            "next_summary_id": 1,
            "chapter_to_project": {},
            "character_to_project": {},
            "worldview_to_project": {},
            "message_to_project": {},
        }

    def _save_index_sync(self) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, self.index_path)

    async def _save_index(self) -> None:
        self._save_index_sync()

    def _next_id(self, key: str) -> int:
        id_key = f"next_{key}_id"
        next_id = self._index.get(id_key, 1)
        self._index[id_key] = next_id + 1
        return next_id

    def _project_dir(self, project_id: int) -> Path:
        return self.projects_dir / str(project_id)

    def _read_json(self, path: Path, default=None):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    def _write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, path)

    # ============================================
    # Project
    # ============================================

    async def create_project(self, data: dict) -> dict:
        async with self._lock:
            pid = self._next_id("project")
            now = _now()
            project = {
                "id": pid,
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "genre": data.get("genre", ""),
                "system_prompt": data.get("system_prompt", ""),
                "created_at": now,
                "updated_at": now,
            }
            pdir = self._project_dir(pid)
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "chapters").mkdir(exist_ok=True)
            self._write_json(pdir / "project.json", project)
            self._write_json(pdir / "chapters" / "chapters.json", [])
            self._write_json(pdir / "characters.json", [])
            self._write_json(pdir / "worldviews.json", [])
            self._write_json(pdir / "messages.json", [])
            self._write_json(pdir / "summaries.json", [])
            await self._save_index()
            return project

    async def get_project(self, project_id: int) -> dict | None:
        path = self._project_dir(project_id) / "project.json"
        return self._read_json(path)

    async def list_projects(self) -> list[dict]:
        if not self.projects_dir.exists():
            return []
        result = []
        for d in sorted(self.projects_dir.iterdir(), key=lambda p: p.name):
            if not d.is_dir():
                continue
            proj = self._read_json(d / "project.json")
            if proj:
                result.append(proj)
        result.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return result

    async def update_project(self, project_id: int, fields: dict) -> dict | None:
        async with self._lock:
            path = self._project_dir(project_id) / "project.json"
            project = self._read_json(path)
            if not project:
                return None
            for k, v in fields.items():
                if k not in ("id", "created_at"):
                    project[k] = v
            project["updated_at"] = _now()
            self._write_json(path, project)
            return project

    async def delete_project(self, project_id: int) -> bool:
        async with self._lock:
            pdir = self._project_dir(project_id)
            if not pdir.exists():
                return False
            shutil.rmtree(pdir)
            # 清理 index 中的映射
            for map_key in (
                "chapter_to_project",
                "character_to_project",
                "worldview_to_project",
                "message_to_project",
            ):
                self._index[map_key] = {
                    k: v
                    for k, v in self._index.get(map_key, {}).items()
                    if v != project_id
                }
            await self._save_index()
            return True

    # ============================================
    # Chapter
    # ============================================

    def _chapters_json_path(self, project_id: int) -> Path:
        return self._project_dir(project_id) / "chapters" / "chapters.json"

    def _chapter_md_path(self, project_id: int, chapter_id: int, title: str) -> Path:
        safe = _sanitize_title(title)
        name = f"{chapter_id:04d}_{safe}.md" if safe else f"{chapter_id:04d}.md"
        return self._project_dir(project_id) / "chapters" / name

    def _find_chapter_md(self, project_id: int, chapter_id: int) -> Path | None:
        """通过 glob 模式查找章节 .md 文件"""
        chapters_dir = self._project_dir(project_id) / "chapters"
        matches = list(chapters_dir.glob(f"{chapter_id:04d}_*.md"))
        if matches:
            return matches[0]
        # 兜底：无标题的文件名
        fallback = chapters_dir / f"{chapter_id:04d}.md"
        return fallback if fallback.exists() else None

    async def create_chapter(self, project_id: int, data: dict) -> dict:
        async with self._lock:
            cid = self._next_id("chapter")
            now = _now()
            chapter = {
                "id": cid,
                "project_id": project_id,
                "title": data.get("title", ""),
                "chapter_order": data.get("chapter_order", 0),
                "status": data.get("status", "draft"),
                "summary": data.get("summary", ""),
                "word_count": 0,
                "created_at": now,
                "updated_at": now,
            }
            # 写入元数据
            path = self._chapters_json_path(project_id)
            chapters = self._read_json(path, [])
            chapters.append(chapter)
            self._write_json(path, chapters)
            # 创建空 .md 文件
            md_path = self._chapter_md_path(project_id, cid, chapter["title"])
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text("", encoding="utf-8")
            # 更新索引
            self._index["chapter_to_project"][str(cid)] = project_id
            await self._save_index()
            return chapter

    async def get_chapter(self, chapter_id: int) -> dict | None:
        """获取章节元数据（不含正文）"""
        pid = self._index.get("chapter_to_project", {}).get(str(chapter_id))
        if pid is None:
            return None
        chapters = self._read_json(self._chapters_json_path(pid), [])
        for ch in chapters:
            if ch.get("id") == chapter_id:
                return ch
        return None

    async def get_chapter_content(self, chapter_id: int) -> str:
        """读取章节正文"""
        pid = self._index.get("chapter_to_project", {}).get(str(chapter_id))
        if pid is None:
            return ""
        md_path = self._find_chapter_md(pid, chapter_id)
        if not md_path or not md_path.exists():
            return ""
        return md_path.read_text(encoding="utf-8")

    async def list_chapters_by_project(self, project_id: int) -> list[dict]:
        chapters = self._read_json(self._chapters_json_path(project_id), [])
        chapters.sort(key=lambda c: c.get("chapter_order", 0))
        return chapters

    async def update_chapter(self, chapter_id: int, fields: dict) -> dict | None:
        """更新章节元数据。若 title 变更则重命名 .md 文件。"""
        async with self._lock:
            pid = self._index.get("chapter_to_project", {}).get(str(chapter_id))
            if pid is None:
                return None
            path = self._chapters_json_path(pid)
            chapters = self._read_json(path, [])
            target = None
            for ch in chapters:
                if ch.get("id") == chapter_id:
                    target = ch
                    break
            if not target:
                return None
            old_title = target.get("title", "")
            for k, v in fields.items():
                if k not in ("id", "project_id", "created_at"):
                    target[k] = v
            target["updated_at"] = _now()
            self._write_json(path, chapters)
            # 标题变更时重命名 .md 文件
            new_title = target.get("title", "")
            if new_title != old_title:
                old_md = self._find_chapter_md(pid, chapter_id)
                if old_md and old_md.exists():
                    new_md = self._chapter_md_path(pid, chapter_id, new_title)
                    old_md.rename(new_md)
            return target

    async def set_chapter_content(self, chapter_id: int, content: str) -> None:
        """写入章节正文"""
        async with self._lock:
            pid = self._index.get("chapter_to_project", {}).get(str(chapter_id))
            if pid is None:
                return
            # 需要标题来定位文件
            chapters = self._read_json(self._chapters_json_path(pid), [])
            title = ""
            for ch in chapters:
                if ch.get("id") == chapter_id:
                    title = ch.get("title", "")
                    break
            md_path = self._find_chapter_md(pid, chapter_id)
            if not md_path:
                md_path = self._chapter_md_path(pid, chapter_id, title)
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(content, encoding="utf-8")

    async def reorder_chapters(
        self, project_id: int, chapter_ids: list[int]
    ) -> None:
        async with self._lock:
            path = self._chapters_json_path(project_id)
            chapters = self._read_json(path, [])
            id_to_chapter = {ch["id"]: ch for ch in chapters}
            for index, cid in enumerate(chapter_ids, start=1):
                if cid in id_to_chapter:
                    id_to_chapter[cid]["chapter_order"] = index
                    id_to_chapter[cid]["updated_at"] = _now()
            self._write_json(path, chapters)

    async def delete_chapter(self, chapter_id: int) -> bool:
        async with self._lock:
            pid = self._index.get("chapter_to_project", {}).get(str(chapter_id))
            if pid is None:
                return False
            path = self._chapters_json_path(pid)
            chapters = self._read_json(path, [])
            new_chapters = [ch for ch in chapters if ch.get("id") != chapter_id]
            if len(new_chapters) == len(chapters):
                return False
            self._write_json(path, new_chapters)
            # 删除 .md 文件
            md_path = self._find_chapter_md(pid, chapter_id)
            if md_path and md_path.exists():
                md_path.unlink()
            # 清理索引
            self._index["chapter_to_project"].pop(str(chapter_id), None)
            await self._save_index()
            return True

    # ============================================
    # Character
    # ============================================

    async def create_character(self, project_id: int, data: dict) -> dict:
        async with self._lock:
            cid = self._next_id("character")
            now = _now()
            character = {
                "id": cid,
                "project_id": project_id,
                "name": data.get("name", ""),
                "role": data.get("role", ""),
                "description": data.get("description", ""),
                "personality": data.get("personality", ""),
                "background": data.get("background", ""),
                "appearance": data.get("appearance", ""),
                "keywords": data.get("keywords", ""),
                "created_at": now,
                "updated_at": now,
            }
            path = self._project_dir(project_id) / "characters.json"
            items = self._read_json(path, [])
            items.append(character)
            self._write_json(path, items)
            self._index["character_to_project"][str(cid)] = project_id
            await self._save_index()
            return character

    async def get_character(self, character_id: int) -> dict | None:
        pid = self._index.get("character_to_project", {}).get(str(character_id))
        if pid is None:
            return None
        items = self._read_json(self._project_dir(pid) / "characters.json", [])
        for it in items:
            if it.get("id") == character_id:
                return it
        return None

    async def list_characters_by_project(self, project_id: int) -> list[dict]:
        return self._read_json(self._project_dir(project_id) / "characters.json", [])

    async def update_character(
        self, character_id: int, fields: dict
    ) -> dict | None:
        async with self._lock:
            pid = self._index.get("character_to_project", {}).get(str(character_id))
            if pid is None:
                return None
            path = self._project_dir(pid) / "characters.json"
            items = self._read_json(path, [])
            target = None
            for it in items:
                if it.get("id") == character_id:
                    target = it
                    break
            if not target:
                return None
            for k, v in fields.items():
                if k not in ("id", "project_id", "created_at"):
                    target[k] = v
            target["updated_at"] = _now()
            self._write_json(path, items)
            return target

    async def delete_character(self, character_id: int) -> bool:
        async with self._lock:
            pid = self._index.get("character_to_project", {}).get(str(character_id))
            if pid is None:
                return False
            path = self._project_dir(pid) / "characters.json"
            items = self._read_json(path, [])
            new_items = [it for it in items if it.get("id") != character_id]
            if len(new_items) == len(items):
                return False
            self._write_json(path, new_items)
            self._index["character_to_project"].pop(str(character_id), None)
            await self._save_index()
            return True

    # ============================================
    # Worldview
    # ============================================

    async def create_worldview(self, project_id: int, data: dict) -> dict:
        async with self._lock:
            wid = self._next_id("worldview")
            now = _now()
            worldview = {
                "id": wid,
                "project_id": project_id,
                "category": data.get("category", "其他"),
                "title": data.get("title", ""),
                "content": data.get("content", ""),
                "keywords": data.get("keywords", ""),
                "created_at": now,
                "updated_at": now,
            }
            path = self._project_dir(project_id) / "worldviews.json"
            items = self._read_json(path, [])
            items.append(worldview)
            self._write_json(path, items)
            self._index["worldview_to_project"][str(wid)] = project_id
            await self._save_index()
            return worldview

    async def get_worldview(self, worldview_id: int) -> dict | None:
        pid = self._index.get("worldview_to_project", {}).get(str(worldview_id))
        if pid is None:
            return None
        items = self._read_json(self._project_dir(pid) / "worldviews.json", [])
        for it in items:
            if it.get("id") == worldview_id:
                return it
        return None

    async def list_worldviews_by_project(self, project_id: int) -> list[dict]:
        return self._read_json(self._project_dir(project_id) / "worldviews.json", [])

    async def update_worldview(
        self, worldview_id: int, fields: dict
    ) -> dict | None:
        async with self._lock:
            pid = self._index.get("worldview_to_project", {}).get(str(worldview_id))
            if pid is None:
                return None
            path = self._project_dir(pid) / "worldviews.json"
            items = self._read_json(path, [])
            target = None
            for it in items:
                if it.get("id") == worldview_id:
                    target = it
                    break
            if not target:
                return None
            for k, v in fields.items():
                if k not in ("id", "project_id", "created_at"):
                    target[k] = v
            target["updated_at"] = _now()
            self._write_json(path, items)
            return target

    async def delete_worldview(self, worldview_id: int) -> bool:
        async with self._lock:
            pid = self._index.get("worldview_to_project", {}).get(str(worldview_id))
            if pid is None:
                return False
            path = self._project_dir(pid) / "worldviews.json"
            items = self._read_json(path, [])
            new_items = [it for it in items if it.get("id") != worldview_id]
            if len(new_items) == len(items):
                return False
            self._write_json(path, new_items)
            self._index["worldview_to_project"].pop(str(worldview_id), None)
            await self._save_index()
            return True

    # ============================================
    # Message
    # ============================================

    def _messages_path(self, project_id: int) -> Path:
        return self._project_dir(project_id) / "messages.json"

    async def add_message(
        self,
        project_id: int,
        chapter_id: int | None,
        role: str,
        content: str,
        token_count: int = 0,
        is_summary: bool = False,
    ) -> dict:
        async with self._lock:
            mid = self._next_id("message")
            now = _now()
            message = {
                "id": mid,
                "project_id": project_id,
                "chapter_id": chapter_id,
                "role": role,
                "content": content,
                "token_count": token_count,
                "is_summary": is_summary,
                "created_at": now,
            }
            path = self._messages_path(project_id)
            items = self._read_json(path, [])
            items.append(message)
            self._write_json(path, items)
            self._index["message_to_project"][str(mid)] = project_id
            await self._save_index()
            return message

    async def get_messages(
        self, project_id: int, chapter_id: int | None, limit: int = 50
    ) -> list[dict]:
        """获取对话历史（含摘要消息），按时间正序"""
        items = self._read_json(self._messages_path(project_id), [])
        if chapter_id:
            filtered = [m for m in items if m.get("chapter_id") == chapter_id]
        else:
            filtered = [m for m in items if m.get("chapter_id") is None]
        filtered.sort(key=lambda m: m.get("id", 0), reverse=True)
        result = filtered[:limit]
        result.reverse()
        return result

    async def get_recent_messages(
        self, project_id: int, chapter_id: int | None, limit: int
    ) -> list[dict]:
        """获取最近 N 条非摘要消息，按时间正序返回"""
        items = self._read_json(self._messages_path(project_id), [])
        if chapter_id:
            filtered = [
                m
                for m in items
                if m.get("chapter_id") == chapter_id and not m.get("is_summary", False)
            ]
        else:
            filtered = [
                m
                for m in items
                if m.get("chapter_id") is None and not m.get("is_summary", False)
            ]
        filtered.sort(key=lambda m: m.get("id", 0), reverse=True)
        result = filtered[:limit]
        result.reverse()
        return result

    async def get_oldest_messages(
        self, project_id: int, chapter_id: int | None, limit: int
    ) -> list[dict]:
        """获取最早的 N 条非摘要消息（按 id 正序）"""
        items = self._read_json(self._messages_path(project_id), [])
        if chapter_id:
            filtered = [
                m
                for m in items
                if m.get("chapter_id") == chapter_id and not m.get("is_summary", False)
            ]
        else:
            filtered = [
                m
                for m in items
                if m.get("chapter_id") is None and not m.get("is_summary", False)
            ]
        filtered.sort(key=lambda m: m.get("id", 0))
        return filtered[:limit]

    async def delete_messages_by_ids(self, msg_ids: list[int]) -> None:
        async with self._lock:
            id_set = set(msg_ids)
            # 按项目分组处理
            msg_to_proj = self._index.get("message_to_project", {})
            proj_to_ids: dict[int, list[int]] = {}
            for mid in msg_ids:
                pid = msg_to_proj.get(str(mid))
                if pid is not None:
                    proj_to_ids.setdefault(pid, []).append(mid)
            for pid, ids in proj_to_ids.items():
                path = self._messages_path(pid)
                items = self._read_json(path, [])
                new_items = [m for m in items if m.get("id") not in id_set]
                self._write_json(path, new_items)
                for mid in ids:
                    self._index["message_to_project"].pop(str(mid), None)
            await self._save_index()

    async def clear_messages(
        self, project_id: int, chapter_id: int | None
    ) -> int:
        async with self._lock:
            path = self._messages_path(project_id)
            items = self._read_json(path, [])
            if chapter_id:
                to_delete = [m for m in items if m.get("chapter_id") == chapter_id]
                new_items = [m for m in items if m.get("chapter_id") != chapter_id]
            else:
                to_delete = [m for m in items if m.get("chapter_id") is None]
                new_items = [m for m in items if m.get("chapter_id") is not None]
            self._write_json(path, new_items)
            # 清理索引
            for m in to_delete:
                self._index["message_to_project"].pop(str(m.get("id")), None)
            await self._save_index()
            return len(to_delete)

    async def count_messages(
        self, project_id: int, chapter_id: int | None
    ) -> int:
        """统计非摘要消息数"""
        items = self._read_json(self._messages_path(project_id), [])
        if chapter_id:
            return sum(
                1
                for m in items
                if m.get("chapter_id") == chapter_id
                and not m.get("is_summary", False)
            )
        return sum(
            1
            for m in items
            if m.get("chapter_id") is None and not m.get("is_summary", False)
        )

    async def get_latest_summary(
        self, project_id: int, chapter_id: int | None
    ) -> str | None:
        """获取最近的摘要消息内容"""
        items = self._read_json(self._messages_path(project_id), [])
        if chapter_id:
            summaries = [
                m
                for m in items
                if m.get("chapter_id") == chapter_id and m.get("is_summary", False)
            ]
        else:
            summaries = [
                m
                for m in items
                if m.get("chapter_id") is None and m.get("is_summary", False)
            ]
        if not summaries:
            return None
        summaries.sort(key=lambda m: m.get("id", 0), reverse=True)
        return summaries[0].get("content", "")

    # ============================================
    # Summary
    # ============================================

    async def add_summary(
        self,
        project_id: int,
        chapter_id: int | None,
        content: str,
        summarized_msg_ids: list[int],
        message_count: int,
        token_count: int,
    ) -> dict:
        async with self._lock:
            sid = self._next_id("summary")
            now = _now()
            summary = {
                "id": sid,
                "project_id": project_id,
                "chapter_id": chapter_id,
                "content": content,
                "summarized_msg_ids": summarized_msg_ids,
                "message_count": message_count,
                "token_count": token_count,
                "created_at": now,
            }
            path = self._project_dir(project_id) / "summaries.json"
            items = self._read_json(path, [])
            items.append(summary)
            self._write_json(path, items)
            await self._save_index()
            return summary
