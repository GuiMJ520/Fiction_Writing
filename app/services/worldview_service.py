"""世界观服务 - 世界观条目 CRUD 和关键词检索"""
from app.storage import FileStorage
from app.models import Worldview, WorldviewCreate, WorldviewUpdate
from app.utils import extract_keywords


class WorldviewService:
    def __init__(self, storage: FileStorage):
        self.storage = storage

    async def create(self, project_id: int, data: WorldviewCreate) -> Worldview:
        worldview = await self.storage.create_worldview(
            project_id, data.model_dump()
        )
        return Worldview(**worldview)

    async def get(self, worldview_id: int) -> Worldview | None:
        row = await self.storage.get_worldview(worldview_id)
        return Worldview(**row) if row else None

    async def list_by_project(
        self, project_id: int, category: str | None = None
    ) -> list[Worldview]:
        rows = await self.storage.list_worldviews_by_project(project_id)
        if category:
            rows = [r for r in rows if r.get("category") == category]
        else:
            rows.sort(key=lambda r: (r.get("category", ""), r.get("id", 0)))
        return [Worldview(**r) for r in rows]

    async def list_categories(self, project_id: int) -> list[str]:
        """列出项目下所有世界观分类"""
        rows = await self.storage.list_worldviews_by_project(project_id)
        seen = set()
        result = []
        for r in rows:
            cat = r.get("category", "其他")
            if cat not in seen:
                seen.add(cat)
                result.append(cat)
        result.sort()
        return result

    async def update(
        self, worldview_id: int, data: WorldviewUpdate
    ) -> Worldview | None:
        fields = data.model_dump(exclude_none=True)
        if not fields:
            return await self.get(worldview_id)
        row = await self.storage.update_worldview(worldview_id, fields)
        return Worldview(**row) if row else None

    async def delete(self, worldview_id: int) -> bool:
        return await self.storage.delete_worldview(worldview_id)

    async def search_by_keywords(
        self, project_id: int, query: str, limit: int = 10
    ) -> list[Worldview]:
        """根据查询文本检索相关世界观条目"""
        keywords = extract_keywords(query)
        if not keywords:
            return []

        all_wvs = await self.list_by_project(project_id)
        matched = []
        for wv in all_wvs:
            # 标题出现在查询中
            if wv.title and wv.title in query:
                matched.append(wv)
                continue
            # keywords 字段匹配
            if wv.keywords:
                wv_kw = [k.strip() for k in wv.keywords.split(",") if k.strip()]
                if any(kw in query for kw in wv_kw):
                    matched.append(wv)
                    continue
            # 查询关键词匹配标题或内容
            if any(
                kw in wv.title or (wv.content and kw in wv.content)
                for kw in keywords
            ):
                matched.append(wv)

        return matched[:limit]
