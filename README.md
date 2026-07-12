# AI小说写作

基于本地大语言模型的 AI 辅助小说写作工具。通过 llama.cpp（llama-server）接入本地模型，支持长篇小说创作。

## 特性

- **本地模型接入**：通过 llama-server API 接入，同时支持 OpenAI 兼容接口和 llama.cpp 原生接口
- **流式对话生成**：实时流式输出，支持中途停止
- **章节管理**：按章节组织小说内容，支持编辑、排序、导出
- **角色与世界观设定**：维护角色卡和世界观条目，AI 写作时自动注入作为上下文
- **上下文记忆管理**：滑动窗口 + 摘要压缩，支持长篇小说创作不丢上下文
- **架构前瞻**：核心业务逻辑与 UI 解耦，未来可直接复用于桌面 GUI

## 快速开始

### 1. 启动 llama-server

```bash
llama-server -m 你的模型路径.gguf --port 8080
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`，确认 `base_url` 指向你的 llama-server 地址。

### 4. 启动应用

```bash
python run.py
```

浏览器访问 http://127.0.0.1:8000

## 架构

```
┌─────────────────────────────────┐
│  UI层 (Web前端 / Future GUI)    │  可替换
├─────────────────────────────────┤
│  API层 (FastAPI)                │  Web 用，GUI 可绕过
├─────────────────────────────────┤
│  Service层 (核心业务逻辑)        │  共用，UI 无关
├─────────────────────────────────┤
│  LLM客户端 + 存储 + 配置         │  基础设施
└─────────────────────────────────┘
```

核心业务逻辑位于 `app/services/`，不依赖 FastAPI，未来 GUI 可直接调用 `create_services()` 工厂函数复用全部业务逻辑。

## 项目结构

```
app/
├── config.py            # 配置加载
├── models.py            # Pydantic 数据模型
├── database.py          # SQLite 异步存储
├── llm/                 # LLM 客户端层
│   ├── base.py          # 抽象基类
│   ├── openai_client.py # OpenAI 兼容
│   ├── llama_client.py  # llama.cpp 原生
│   └── factory.py       # 工厂模式
├── services/            # 业务逻辑层（UI 无关）
│   ├── context_manager.py  # 上下文记忆管理
│   ├── chat_service.py     # 对话生成编排
│   └── ...
└── api/                 # FastAPI 路由层
static/                  # 前端静态资源
```

## 技术栈

- **后端**：Python 3.10+ / FastAPI / aiosqlite / httpx
- **前端**：原生 HTML + Alpine.js v3（无构建步骤）
- **存储**：SQLite
- **LLM**：llama.cpp（llama-server）

## 许可证

MIT
