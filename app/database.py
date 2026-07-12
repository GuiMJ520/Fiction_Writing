"""SQLite 异步数据库管理 - 连接池、建表、CRUD 操作"""
import aiosqlite
from pathlib import Path


# ============================================
# 数据库 Schema - 所有表定义
# ============================================
SCHEMA_SQL = """
-- 项目表：一部小说对应一个项目
CREATE TABLE IF NOT EXISTS projects (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    description   TEXT DEFAULT '',
    genre         TEXT DEFAULT '',
    system_prompt TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    updated_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- 章节表
CREATE TABLE IF NOT EXISTS chapters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL,
    title         TEXT NOT NULL,
    content       TEXT DEFAULT '',
    chapter_order INTEGER NOT NULL,
    status        TEXT DEFAULT 'draft',
    summary       TEXT DEFAULT '',
    word_count    INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    updated_at    TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id, chapter_order);

-- 角色卡表
CREATE TABLE IF NOT EXISTS characters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    role          TEXT DEFAULT '',
    description   TEXT DEFAULT '',
    personality   TEXT DEFAULT '',
    background    TEXT DEFAULT '',
    appearance    TEXT DEFAULT '',
    keywords      TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    updated_at    TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_characters_project ON characters(project_id);

-- 世界观条目表
CREATE TABLE IF NOT EXISTS worldviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL,
    category      TEXT DEFAULT '其他',
    title         TEXT NOT NULL,
    content       TEXT NOT NULL,
    keywords      TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    updated_at    TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_worldviews_project ON worldviews(project_id, category);

-- 对话消息表
CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL,
    chapter_id    INTEGER,
    role          TEXT NOT NULL,
    content       TEXT NOT NULL,
    token_count   INTEGER DEFAULT 0,
    is_summary    INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_messages_chapter ON messages(chapter_id, id);
CREATE INDEX IF NOT EXISTS idx_messages_project ON messages(project_id, id);

-- 摘要历史表
CREATE TABLE IF NOT EXISTS summaries (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id           INTEGER NOT NULL,
    chapter_id           INTEGER,
    content              TEXT NOT NULL,
    summarized_msg_ids   TEXT DEFAULT '[]',
    message_count        INTEGER DEFAULT 0,
    token_count          INTEGER DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_summaries_chapter ON summaries(chapter_id);
"""


class Database:
    """异步 SQLite 数据库管理器"""

    def __init__(self, db_path: str = "data/novels.db"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """连接数据库并初始化 schema"""
        # 确保数据目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        # 开启外键约束（SQLite 默认关闭）
        await self._conn.execute("PRAGMA foreign_keys = ON")
        # 建表
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("数据库未连接，请先调用 connect()")
        return self._conn

    # 通用查询方法
    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """执行单条 SQL（INSERT/UPDATE/DELETE）"""
        cursor = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cursor

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict | None:
        """查询单条记录，返回字典"""
        cursor = await self.conn.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """查询多条记录，返回字典列表"""
        cursor = await self.conn.execute(sql, params)
        rows = await cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
