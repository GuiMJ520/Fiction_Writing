# AI小说写作

一个基于本地 LLM 的小说创作辅助程序，支持流式对话、章节管理、角色与世界观设定、上下文记忆管理。

## 功能特性

### 核心功能
- **流式对话生成**：基于 SSE（Server-Sent Events）的实时流式输出，边生成边显示
- **章节管理**：项目-章节两级结构，支持章节排序、正文编辑、自动保存
- **角色与世界观设定**：结构化管理角色信息和世界观条目，写作时自动注入相关设定
- **上下文记忆管理**：滑动窗口 + 摘要压缩，长篇创作时自动压缩旧对话为摘要

### 编辑与导出
- **双模式编辑**：对话模式（与 AI 交互）和正文模式（直接写作），Tab 一键切换
- **自动保存**：正文编辑 2 秒防抖自动保存，实时显示保存状态
- **导出功能**：单章导出为 TXT/Markdown，全本导出为 Markdown/TXT

### 用户体验
- **深色模式**：一键切换深/浅色主题，跟随系统偏好，localStorage 持久化
- **Toast 通知**：操作反馈通过右上角 toast 提示，支持 error/warning/info/success 四种类型
- **上下文深度调节**：滑块控制对话上下文消息数（5-50 条）
- **自动滚动**：新消息生成时自动滚动到底部
- **自动打开浏览器**：启动服务后自动打开浏览器访问应用

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Alpine.js v3（无构建步骤）、原生 CSS（变量驱动主题） |
| 后端 | Python 3.14、FastAPI |
| 存储 | 文件系统（JSON 元数据 + Markdown 章节正文） |
| LLM 接入 | OpenAI 兼容接口、llama.cpp 原生接口（支持 grammar 约束） |
| 通信 | HTTP REST API、SSE 流式输出 |

## 架构设计

```
┌─────────────────────────────────────────────┐
│  UI 层（static/）                            │
│  Alpine.js + 原生 CSS                       │
│  index.html / js/app.js / js/api.js         │
└──────────────────┬──────────────────────────┘
                   │ HTTP / SSE
┌──────────────────▼──────────────────────────┐
│  API 层（app/api/）                          │
│  FastAPI 路由 + 依赖注入                     │
│  routes/{projects,chapters,characters,       │
│          worldviews,chat,export,llm}.py      │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  Service 层（app/services/）                 │
│  UI 无关的业务逻辑（GUI 可直接复用）          │
│  {project,chapter,character,worldview,       │
│   chat,context,export}_service.py            │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  LLM 客户端层（app/llm/）                    │
│  抽象基类 + 工厂模式                          │
│  OpenAICompatClient / LlamaNativeClient      │
└─────────────────────────────────────────────┘
```

**关键设计**：Service 层不依赖 FastAPI，未来开发桌面 GUI 时可通过 `create_services()` 工厂函数直接复用全部业务逻辑。

## 快速开始

### 1. 环境准备

- Python 3.12+（推荐 3.14）
- 本地 LLM 服务（任选其一）：
  - [llama.cpp](https://github.com/ggerganov/llama.cpp) 的 `llama-server`
  - [Ollama](https://ollama.com/)
  - 任何兼容 OpenAI API 的服务

### 2. 安装依赖

```bash
pip install fastapi uvicorn httpx pydantic pyyaml
```

### 3. 配置

复制配置模板并编辑：

```bash
cp config.example.yaml config.yaml
```

`config.yaml` 示例：

```yaml
llm:
  api_type: openai_compat   # openai_compat | llama_native
  base_url: http://127.0.0.1:8080
  api_key: ""
  model: your-model-name

generation:
  temperature: 0.7
  max_tokens: 2048
  top_p: 0.9

context:
  window_size: 20          # 滑动窗口大小
  compress_threshold: 30   # 触发压缩的消息数阈值
  compress_batch: 10       # 每次压缩的消息数

storage:
  data_dir: data           # 数据根目录，每个项目一个子文件夹

server:
  host: 127.0.0.1
  port: 8000
  reload: true
  open_browser: true       # 启动时自动打开浏览器
```

### 4. 启动 LLM 服务

以 llama.cpp 为例：

```bash
llama-server -m your-model.gguf --port 8080
```

### 5. 启动应用

```bash
python run.py
```

启动后会自动打开浏览器访问 http://127.0.0.1:8000。

## 使用指南

### 创建项目
点击顶栏「+ 新项目」，输入项目名称和类型（如玄幻、都市、科幻）。

### 章节管理
- 左侧栏点击「+」创建新章节
- 点击章节进入对话模式
- 切换「正文」Tab 可直接编写章节内容，自动保存

### 角色与世界观
- 右侧面板切换「角色」/「世界观」Tab
- 点击「+」添加设定条目
- 写作时系统会根据关键词自动注入相关设定到上下文

### 上下文管理
- 底部滑块调节上下文深度（5-50 条）
- 消息数接近阈值时，上下文计数显示橙色警告
- 点击「压缩」手动触发摘要压缩

### 导出
- 章节正文模式：点击「导出」导出当前章节
- 项目对话模式：点击「导出全本」导出所有章节

### 深色模式
点击顶栏月亮/太阳图标切换主题，设置自动保存。

## 项目结构

```
AI小说写作/
├── app/
│   ├── api/              # FastAPI 路由层
│   │   ├── routes/       # 各资源路由
│   │   ├── app.py        # FastAPI 应用
│   │   └── dependencies.py
│   ├── llm/              # LLM 客户端层
│   │   ├── base.py       # 抽象基类
│   │   ├── openai_client.py
│   │   ├── llama_client.py
│   │   └── factory.py
│   ├── services/         # 业务逻辑层
│   │   ├── __init__.py   # create_services 工厂
│   │   ├── project_service.py
│   │   ├── chapter_service.py
│   │   ├── character_service.py
│   │   ├── worldview_service.py
│   │   ├── chat_service.py
│   │   ├── context_manager.py
│   │   └── export_service.py
│   ├── config.py         # 配置加载
│   ├── storage.py        # 文件系统存储
│   ├── models.py         # Pydantic 模型
│   └── utils.py          # 工具函数
├── static/               # 前端静态资源
│   ├── css/style.css
│   ├── js/
│   │   ├── app.js        # Alpine.js 主组件
│   │   ├── api.js        # API 封装
│   │   └── sse.js        # SSE 流式处理
│   ├── vendor/alpine.min.js
│   └── index.html
├── tests/                # 测试脚本
├── config.example.yaml   # 配置模板
├── run.py                # 启动入口
└── README.md
```

## 存储设计

采用文件系统存储，每个项目一个独立文件夹，章节正文保存为单独的 Markdown 文件，元数据使用 JSON 管理：

```
data/
├── index.json              # 全局 ID 计数器 + 实体到项目的映射
├── projects/
│   └── {project_id}/
│       ├── project.json    # 项目元数据
│       ├── chapters/
│       │   ├── chapters.json       # 章节元数据列表
│       │   └── {id:04d}_{title}.md # 章节正文
│       ├── characters.json # 角色列表
│       ├── worldviews.json # 世界观列表
│       ├── messages.json   # 对话消息（含摘要消息）
│       └── summaries.json  # 摘要历史记录
└── exports/                # 导出文件目录
```

| 文件 | 说明 |
|------|------|
| `index.json` | 全局 ID 计数器 + 实体到项目的映射（支持不带 project_id 的路由） |
| `project.json` | 项目元数据（名称、类型、描述、系统提示词） |
| `chapters.json` | 章节元数据列表（标题、排序、状态、摘要、字数） |
| `{id:04d}_{title}.md` | 章节正文（Markdown 格式，标题变更时自动重命名） |
| `characters.json` | 角色列表（姓名、身份、性格、背景、外貌、关键词） |
| `worldviews.json` | 世界观列表（分类、标题、内容、关键词） |
| `messages.json` | 对话消息（角色、内容、token 数、是否摘要） |
| `summaries.json` | 摘要记录（压缩后的对话摘要） |

**关键设计**：
- 原子写入：所有 JSON 文件先写 `.tmp` 再 `os.replace()`，防止数据损坏
- 并发安全：使用 `asyncio.Lock` 保护写操作
- 级联删除：删除项目时直接删除整个项目文件夹

## 开发说明

### 添加新的 LLM 后端

1. 继承 `app/llm/base.py` 的 `LLMClient` 抽象基类
2. 实现 `chat()` 和 `health_check()` 方法
3. 在 `app/llm/factory.py` 注册新后端

### 添加新的 Service

Service 层通过 `create_services(config)` 工厂函数初始化，所有 Service 接收 `FileStorage` 实例，不依赖 FastAPI。

## License

MIT
