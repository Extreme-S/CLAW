# CLAW — 私人 AI 助手系统架构设计

## 1. 系统概览

CLAW 是一套私有部署的个人 AI 助手系统，采用 **Client-Server 架构**，分为两个独立项目：

- **Server — [OpenClaw](https://github.com/Extreme-S/OpenClaw)**：部署在 Mac Mini 上，承载全部 AI 推理、对话管理、数据存储和插件执行
- **Client — [Little-CLAW](https://github.com/Extreme-S/CLAW)**（本仓库）：桌面宠物客户端，运行在用户的其他电脑上，作为轻量级交互入口

用户通过多种客户端（CLAW 桌面宠物、飞书机器人、Web 仪表盘）与 AI 交互，所有请求通过网络汇聚到 Mac Mini 上的 OpenClaw 服务端处理。

```
┌─────────────────────────────────────────────────────────────────┐
│           用户端 Clients（运行在用户的其他电脑/设备）              │
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │ Little-CLAW   │    │  飞书机器人   │    │  Web 仪表盘   │      │
│   │ 桌面宠物客户端│    │  Feishu Bot  │    │  Dashboard   │      │
│   │ (PyQt6)      │    │              │    │              │      │
│   │ 本仓库        │    │              │    │              │      │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│          │                   │                   │              │
└──────────┼───────────────────┼───────────────────┼──────────────┘
           │ HTTP/WebSocket    │ Webhook/API       │ HTTP
           │ (局域网/Tailscale)│                   │
           ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│          Mac Mini 服务端 — OpenClaw (独立仓库)                    │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    API Gateway                          │   │
│   │              (FastAPI / Authentication)                  │   │
│   └────────┬──────────────┬──────────────┬──────────────────┘   │
│            │              │              │                       │
│   ┌────────▼───────┐ ┌───▼────────┐ ┌───▼──────────────┐       │
│   │  Chat Engine   │ │  Tool      │ │  Plugin Manager  │       │
│   │  对话引擎      │ │  Executor  │ │  插件管理器       │       │
│   │  (多轮/记忆)   │ │  工具执行   │ │                  │       │
│   └────────┬───────┘ └───┬────────┘ └───┬──────────────┘       │
│            │             │              │                       │
│   ┌────────▼─────────────▼──────────────▼──────────────────┐   │
│   │                   Core Services                        │   │
│   │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────────┐  │   │
│   │  │ AI Router│ │ Memory   │ │ Logger │ │ Scheduler  │  │   │
│   │  │ 模型路由  │ │ 长期记忆  │ │ 日志   │ │ 定时任务   │  │   │
│   │  └──────────┘ └──────────┘ └────────┘ └────────────┘  │   │
│   └────────────────────────┬───────────────────────────────┘   │
│                            │                                    │
│   ┌────────────────────────▼───────────────────────────────┐   │
│   │                    Storage Layer                        │   │
│   │  ┌──────────┐ ┌──────────────┐ ┌───────────────────┐   │   │
│   │  │ SQLite   │ │ File Storage │ │ Vector DB (FAISS) │   │   │
│   │  │ 对话/配置 │ │ 文件/日志    │ │ 语义检索          │   │   │
│   │  └──────────┘ └──────────────┘ └───────────────────┘   │   │
│   └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 项目结构

系统拆分为两个独立仓库：

### 2.1 服务端 — OpenClaw（独立仓库，部署在 Mac Mini）

```
openclaw/                               # github.com/Extreme-S/OpenClaw
├── main.py                             # FastAPI 入口
├── requirements.txt
├── config.yaml                         # 服务端配置（API Key、Token 等）
│
├── api/                                # API 层
│   ├── __init__.py
│   ├── routes_chat.py                  # POST /chat, WebSocket /chat/stream
│   ├── routes_tools.py                 # POST /tools/execute
│   ├── routes_history.py               # GET /history, GET /sessions
│   ├── routes_health.py                # GET /health
│   ├── middleware.py                   # 认证、限流、日志中间件
│   └── deps.py                         # 依赖注入
│
├── core/                               # 核心服务
│   ├── __init__.py
│   ├── chat_engine.py                  # 多轮对话引擎（上下文管理、消息裁剪）
│   ├── ai_router.py                    # AI 模型路由（OpenAI/Claude/本地模型切换）
│   ├── memory.py                       # 长期记忆（用户画像、偏好、知识库）
│   ├── tool_executor.py                # Function Calling 工具执行器
│   ├── plugin_manager.py               # 插件加载与管理
│   └── scheduler.py                    # 定时任务调度（提醒、新闻、日报）
│
├── plugins/                            # 内置插件
│   ├── __init__.py
│   ├── base.py                         # 插件基类
│   ├── water_reminder.py               # 喝水提醒
│   ├── news_collector.py               # 新闻搜集 + AI 摘要
│   ├── weather.py                      # 天气查询
│   ├── translator.py                   # 翻译
│   ├── reminder.py                     # 自定义提醒（"3点提醒我开会"）
│   └── daily_briefing.py               # 每日简报
│
├── storage/                            # 存储层
│   ├── __init__.py
│   ├── database.py                     # SQLite 管理（对话、会话、用户数据）
│   ├── models.py                       # ORM 模型定义
│   ├── vector_store.py                 # 向量存储（FAISS，用于语义检索记忆）
│   └── file_store.py                   # 文件存储管理
│
├── adapters/                           # 客户端适配器
│   ├── __init__.py
│   ├── feishu_bot.py                   # 飞书机器人 Webhook 适配
│   └── feishu_events.py                # 飞书事件回调处理
│
├── data/                               # 运行时数据（gitignore）
│   ├── openclaw.db                     # SQLite 数据库
│   ├── vectors/                        # FAISS 向量索引
│   ├── logs/                           # 日志文件
│   └── uploads/                        # 用户上传文件
│
└── tests/
    ├── test_chat_engine.py
    ├── test_plugins.py
    └── test_api.py
```

### 2.2 客户端 — Little-CLAW（本仓库，运行在用户的其他电脑上）

```
little-claw/                            # github.com/Extreme-S/CLAW（本仓库）
├── main.py                             # PyQt6 入口
├── requirements.txt
│
├── core/
│   ├── __init__.py
│   ├── api_client.py                   # 与 OpenClaw 服务端通信的 HTTP/WS 客户端
│   ├── config_manager.py               # 本地配置（服务器地址、Token、快捷键等）
│   ├── event_bus.py
│   └── macos_topmost.py
│
├── ui/
│   ├── __init__.py
│   ├── tv_widget.py                    # 赛博朋克 CLAW 桌面宠物（与 Web Logo 一致）
│   ├── chat_panel.py                   # 聊天面板（通过 api_client 调 OpenClaw）
│   ├── news_panel.py
│   ├── bubble_toast.py
│   ├── tray_icon.py
│   └── settings_dialog.py
│
├── features/
│   └── hotkey.py                       # 全局快捷键
│
├── web/                                # Web 仪表盘（静态页面）
│   ├── index.html
│   ├── css/
│   └── js/
│
└── docs/
    └── architecture-design.md          # 本文档
```

## 3. 服务端设计（OpenClaw）

### 3.1 API Gateway

基于 FastAPI 构建，提供 RESTful + WebSocket 接口。

```
API 端点设计：

POST   /api/v1/chat                  # 发送消息（同步返回）
WS     /api/v1/chat/stream           # 流式对话（WebSocket）
GET    /api/v1/sessions              # 获取会话列表
GET    /api/v1/sessions/{id}/history # 获取某会话的历史记录
DELETE /api/v1/sessions/{id}         # 删除会话
POST   /api/v1/tools/execute         # 执行工具/插件
GET    /api/v1/plugins               # 获取可用插件列表
PUT    /api/v1/settings              # 更新设置
GET    /api/v1/health                # 健康检查
```

**认证方式**：Bearer Token（简单安全，私有部署无需复杂 OAuth）

```python
# 请求示例
POST /api/v1/chat
Authorization: Bearer <your-token>
Content-Type: application/json

{
    "session_id": "abc-123",          # 可选，不传则创建新会话
    "message": "帮我翻译这段话",
    "client": "desktop",              # 来源标识
    "attachments": []                 # 可选，图片/文件
}
```

### 3.2 Chat Engine（对话引擎）

核心模块，管理多轮对话的完整生命周期。

```python
class ChatEngine:
    """
    职责：
    1. 会话管理 — 创建/恢复/切换会话
    2. 上下文组装 — system prompt + 长期记忆 + 近期对话 + 当前消息
    3. 消息裁剪 — 超过 token 上限时智能截断早期消息
    4. 工具调用 — 解析 AI 返回的 function_call，执行后回填结果
    5. 流式输出 — 支持 SSE/WebSocket 逐字推送
    """

    async def chat(self, session_id, message, client) -> AsyncIterator[str]:
        # 1. 加载/创建会话
        session = await self.storage.get_or_create_session(session_id)

        # 2. 组装上下文
        context = await self._build_context(session, message)
        # context = [system_prompt, memory_summary, ...history, user_msg]

        # 3. 调用 AI
        async for chunk in self.ai_router.stream(context):
            if chunk.is_tool_call:
                # 4. 执行工具，将结果追加到上下文，继续对话
                result = await self.tool_executor.run(chunk.tool_call)
                context.append({"role": "tool", "content": result})
                async for sub_chunk in self.ai_router.stream(context):
                    yield sub_chunk.text
            else:
                yield chunk.text

        # 5. 持久化
        await self.storage.save_message(session_id, message, role="user")
        await self.storage.save_message(session_id, full_response, role="assistant")
```

**上下文组装策略**：

```
┌────────────────────────────────────────────┐
│ System Prompt（人设 + 工具描述）             │  固定
├────────────────────────────────────────────┤
│ Memory Summary（用户画像 + 长期记忆摘要）    │  从向量库检索
├────────────────────────────────────────────┤
│ Recent History（最近 N 轮对话）              │  从 SQLite 加载
├────────────────────────────────────────────┤
│ Current Message（当前用户消息）              │  实时输入
└────────────────────────────────────────────┘
```

### 3.3 AI Router（模型路由）

统一管理多个 AI 后端，支持按任务类型自动路由。

```python
class AIRouter:
    """
    路由策略：
    - 日常闲聊 → gpt-4o-mini（快速、低成本）
    - 复杂推理 → claude-opus / gpt-4o（高质量）
    - 翻译任务 → 指定模型
    - 本地模型 → Ollama（完全离线，隐私敏感场景）
    """

    providers = {
        "openai":  OpenAIProvider,
        "claude":  ClaudeProvider,
        "ollama":  OllamaProvider,     # 本地模型，未来扩展
    }
```

### 3.4 Memory（长期记忆）

```
记忆体系：
├── 用户画像 — 姓名、职业、偏好、习惯（结构化 JSON）
├── 知识库   — 用户主动告知的事实（"我的猫叫小橘"）
├── 对话摘要 — 定期将长对话压缩为摘要存入向量库
└── 语义检索 — 每次对话前，用当前消息检索相关记忆片段
```

使用 FAISS 做本地向量存储，embedding 可用 OpenAI `text-embedding-3-small` 或本地模型。

### 3.5 Plugin System（插件系统）

```python
class Plugin(ABC):
    """插件基类，所有功能模块继承此类。"""

    name: str                    # 插件名称
    description: str             # 描述（会注入到 system prompt 供 AI 调用）
    triggers: list[str]          # 触发关键词

    @abstractmethod
    async def execute(self, params: dict) -> str:
        """执行插件逻辑，返回文本结果。"""
        ...

    def as_tool_schema(self) -> dict:
        """导出为 OpenAI Function Calling schema。"""
        ...
```

**内置插件列表**：

| 插件 | 触发方式 | 功能 |
|---|---|---|
| `water_reminder` | 定时 / 聊天触发 | 喝水提醒 |
| `news_collector` | 定时 / 手动刷新 | AI 新闻搜集与摘要 |
| `weather` | AI 调用 | 查询天气 |
| `translator` | AI 调用 / `/translate` | 翻译 |
| `reminder` | AI 调用 | 自定义定时提醒 |
| `daily_briefing` | 每日定时 | 天气+新闻+日程汇总 |
| `web_search` | AI 调用 | 联网搜索 |

### 3.6 Storage（存储层）

全部数据存储在 Mac Mini 本地。

```sql
-- SQLite 核心表结构

-- 会话表
CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT,             -- 自动生成的会话标题
    client      TEXT,             -- 来源：desktop / feishu
    created_at  DATETIME,
    updated_at  DATETIME
);

-- 消息表
CREATE TABLE messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT REFERENCES sessions(id),
    role        TEXT,             -- user / assistant / system / tool
    content     TEXT,
    tokens      INTEGER,          -- token 计数
    model       TEXT,             -- 使用的模型
    created_at  DATETIME
);

-- 记忆表
CREATE TABLE memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category    TEXT,             -- profile / knowledge / summary
    content     TEXT,
    embedding   BLOB,            -- 向量（FAISS 也会单独存索引）
    created_at  DATETIME,
    updated_at  DATETIME
);

-- 日志表
CREATE TABLE logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    level       TEXT,             -- info / warn / error
    source      TEXT,             -- 模块来源
    message     TEXT,
    metadata    TEXT,             -- JSON 扩展字段
    created_at  DATETIME
);
```

## 4. 客户端设计（Little-CLAW / 本仓库）

### 4.1 Desktop Client（CLAW 桌面宠物客户端）

桌面宠物运行在**用户的其他电脑**上（如 MacBook、工作站等），作为**瘦客户端**通过局域网/Tailscale 连接 Mac Mini 上的 OpenClaw 服务端。客户端只负责 UI 渲染和交互，所有 AI 推理、对话管理、数据存储均由 OpenClaw 完成。

```python
# core/api_client.py

class OpenClawClient:
    """与 OpenClaw 服务端通信。"""

    def __init__(self, server_url: str, token: str):
        self.server_url = server_url    # e.g. "http://mac-mini.local:8000"
        self.token = token

    async def chat_stream(self, session_id: str, message: str):
        """WebSocket 流式对话。"""
        async with websockets.connect(
            f"{self.ws_url}/api/v1/chat/stream",
            extra_headers={"Authorization": f"Bearer {self.token}"}
        ) as ws:
            await ws.send(json.dumps({
                "session_id": session_id,
                "message": message,
                "client": "desktop"
            }))
            async for chunk in ws:
                yield json.loads(chunk)["text"]

    async def get_sessions(self) -> list[dict]:
        """获取历史会话列表。"""
        ...

    async def get_history(self, session_id: str) -> list[dict]:
        """获取某会话的完整历史。"""
        ...
```

**改动点**（相对现有代码）：

| 模块 | 现状 | 重构后 |
|---|---|---|
| `tv_widget.py` | B站小电视形象 | 赛博朋克 CLAW Logo（已完成） |
| `chat_panel.py` | 直接调 OpenAI/Claude SDK | 通过 `OpenClawClient` 调 OpenClaw 服务端 |
| `ai_chat.py` | 客户端内置 Provider | 删除，AI 逻辑移至 OpenClaw |
| `news_collector.py` | 客户端本地采集 | 移至 OpenClaw 插件，客户端只展示 |
| `water_reminder.py` | 客户端定时器 | OpenClaw 调度，通过 WebSocket 推送到客户端 |
| 新增 `api_client.py` | — | 统一的 OpenClaw 服务端通信层 |
| 新增 `hotkey.py` | — | 全局快捷键（Cmd+Shift+Space） |

**网络拓扑**：
```
用户电脑 (MacBook/PC)              Mac Mini (常驻服务器)
┌────────────────────┐            ┌────────────────────┐
│  Little-CLAW        │───HTTP/WS──→│  OpenClaw 服务端   │
│  桌面宠物客户端      │←──推送─────│  (FastAPI)         │
│  (PyQt6 瘦客户端)   │            │                    │
└────────────────────┘            └────────────────────┘
  局域网: http://mac-mini.local:8000
  外网:   通过 Tailscale 组网
```

### 4.2 Feishu Bot（飞书机器人）

飞书作为移动端入口，通过 Webhook 与服务端通信。

```
飞书消息流：

用户 → 飞书 App → 飞书开放平台 → Webhook → OpenClaw 服务端
                                                    │
                                                    ▼
                                              Chat Engine
                                                    │
                                                    ▼
OpenClaw 服务端 → 飞书 API (发送消息) → 飞书 App → 用户
```

```python
# openclaw/adapters/feishu_bot.py

class FeishuAdapter:
    """飞书事件处理适配器。"""

    async def handle_message(self, event: dict):
        """收到飞书消息 → 转发到 ChatEngine → 回复飞书。"""
        user_id = event["sender"]["sender_id"]["open_id"]
        text = event["message"]["content"]

        # 每个飞书用户对应一个持久会话
        session_id = f"feishu_{user_id}"

        full_response = ""
        async for chunk in self.chat_engine.chat(session_id, text, client="feishu"):
            full_response += chunk

        await self.feishu_client.reply_message(event["message_id"], full_response)
```

**飞书配置要点**：
- 在飞书开放平台创建企业自建应用
- 配置事件订阅 URL：`https://<your-domain>/api/v1/feishu/events`
- 需要的权限：`im:message:receive_v1`、`im:message:create_v1`
- Mac Mini 需通过内网穿透（frp/ngrok）或绑定域名暴露接口

## 5. 通信协议

### 5.1 客户端 ↔ 服务端

| 场景 | 协议 | 说明 |
|---|---|---|
| 流式对话 | WebSocket | 低延迟，逐字推送 |
| 普通请求 | HTTP REST | 历史记录、设置、插件操作 |
| 服务端推送 | WebSocket | 定时提醒、新闻推送 |

### 5.2 消息格式

```json
// WebSocket 消息格式
// → 客户端发送
{
    "type": "chat",
    "session_id": "abc-123",
    "message": "今天天气怎么样",
    "client": "desktop"
}

// ← 服务端推送
{"type": "chunk", "text": "今天"}
{"type": "chunk", "text": "今天北京"}
{"type": "chunk", "text": "今天北京天气晴朗"}
{"type": "done",  "text": "今天北京天气晴朗，气温15°C。", "session_id": "abc-123"}

// ← 服务端主动推送（提醒）
{"type": "notification", "plugin": "water_reminder", "message": "该喝水啦～"}
{"type": "notification", "plugin": "daily_briefing", "message": "早安！今日简报..."}
```

## 6. 数据流全景

```
 用户电脑/设备                          Mac Mini 服务端
┌──────────┐  用户输入   ┌──────────────┐  HTTP/WS  ┌──────────────┐
│CLAW 桌面宠├───────────→│ API Gateway  ├─────────→│ Chat Engine  │
│物 / 飞书  │  (网络)    │ (认证/路由)   │          │ (上下文组装)  │
└──────────┘            └──────────────┘          └──────┬───────┘
     ▲                                                    │
     │                                          ┌─────────▼─────────┐
     │                                          │ 检索相关记忆       │
     │                                          │ Memory + VectorDB │
     │                                          └─────────┬─────────┘
     │                                                    │
     │                                          ┌─────────▼─────────┐
     │                                          │ 调用 AI 模型       │
     │                                          │ AI Router         │
     │                                          └─────────┬─────────┘
     │                                                    │
     │            ┌───── 需要工具？──────┐                 │
     │            │ Yes                 │ No              │
     │     ┌──────▼──────┐              │                 │
     │     │ Tool        │              │                 │
     │     │ Executor    │──结果回填──→  │                 │
     │     │ (插件执行)   │              │                 │
     │     └─────────────┘              │                 │
     │                                  │                 │
     │                         ┌────────▼─────────┐       │
     │   流式推送              │ 保存对话到 SQLite │       │
     └─────────────────────────│ 更新记忆          │◄──────┘
                               └──────────────────┘
```

## 7. 部署方案

### Mac Mini — OpenClaw 服务端

从 OpenClaw 仓库部署，常驻运行在 Mac Mini 上，开机自启。

```bash
# 1. 克隆 OpenClaw 服务端仓库
git clone https://github.com/Extreme-S/OpenClaw.git
cd openclaw

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库
python -m storage.database init

# 4. 配置
cp config.example.yaml config.yaml
# 编辑 config.yaml：填写 API Key、飞书凭证、客户端 Token 等

# 5. 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000

# 6. 用 launchd 设为开机自启（推荐）
```

### 网络连接

```yaml
# 局域网直连（同一网络下的其他电脑）
server_url: "http://mac-mini.local:8000"

# 外网访问（不在同一局域网时）
# 方案 A：Tailscale 组网（推荐，零配置 P2P VPN，所有设备加入同一虚拟网络）
# 方案 B：frp 内网穿透
# 方案 C：Cloudflare Tunnel
# 飞书 Webhook 需要外网可达，推荐 Tailscale + Funnel 或 Cloudflare Tunnel
```

### 其他电脑 — Little-CLAW 桌面宠物客户端

从本仓库 (CLAW) 部署，在用户的 MacBook/PC 上安装运行，连接 Mac Mini 上的 OpenClaw。

```bash
# 1. 克隆客户端仓库
git clone https://github.com/Extreme-S/CLAW.git
cd CLAW

# 2. 安装依赖
pip install -r requirements.txt

# 3. 首次运行需配置 OpenClaw 服务端地址
# config.yaml → server_url: "http://mac-mini.local:8000"

# 4. 启动桌面宠物
python main.py
```

## 8. 安全设计

| 层面 | 措施 |
|---|---|
| 传输 | 局域网内 HTTP 即可；外网必须 HTTPS（Tailscale 自带加密） |
| 认证 | Bearer Token，OpenClaw 服务端校验。Token 存储在客户端本地加密配置 |
| API Key | 所有 AI API Key 只存在 OpenClaw 的 config.yaml，客户端不接触 |
| 数据 | 全部存储在 Mac Mini 本地（OpenClaw），不经过第三方云服务（除 AI API 调用） |
| 日志 | 操作日志记录到 SQLite，可审计追溯 |

## 9. 开发路线

### Phase 1：OpenClaw 服务端搭建（1-2 周）
> 仓库：`Extreme-S/OpenClaw`，部署在 Mac Mini

- [ ] 创建 OpenClaw 仓库，FastAPI 骨架 + 认证中间件
- [ ] Chat Engine（多轮对话 + 消息持久化）
- [ ] AI Router（OpenAI + Claude）
- [ ] SQLite 存储层
- [ ] WebSocket 流式接口

### Phase 2：Little-CLAW 客户端对接（1 周）
> 仓库：`Extreme-S/CLAW`（本仓库），运行在其他电脑

- [x] 桌面宠物形象更新为赛博朋克 CLAW Logo（与 Web 端一致）
- [ ] 新增 `api_client.py`，替换直接 SDK 调用，连接 OpenClaw 服务端
- [ ] ChatPanel 改为调 OpenClaw API
- [ ] 会话管理（新建/切换/历史）
- [ ] 全局快捷键
- [ ] 客户端打包分发（支持在多台电脑上安装）

### Phase 3：飞书机器人接入（1 周）
> 在 OpenClaw 服务端实现适配器

- [ ] 飞书开放平台应用配置
- [ ] Webhook 事件处理适配器
- [ ] 消息回复（支持富文本/Markdown）
- [ ] 内网穿透 or Tailscale

### Phase 4：智能增强（持续迭代）
> OpenClaw 服务端插件扩展

- [ ] 插件系统 + Function Calling
- [ ] 长期记忆 + 向量检索
- [ ] 每日简报、天气、提醒等插件
- [ ] 本地模型支持（Ollama）

## 10. 技术选型汇总

| 组件 | 技术 | 理由 |
|---|---|---|
| 服务端框架 | FastAPI (OpenClaw) | 异步、高性能、自动生成 API 文档 |
| 数据库 | SQLite | 轻量、零运维、私有部署够用 |
| 向量存储 | FAISS | 本地部署、无需额外服务 |
| 实时通信 | WebSocket | 原生支持流式推送 |
| 桌面 UI | PyQt6 (Little-CLAW) | 已有基础，跨平台 |
| 飞书集成 | 飞书开放平台 SDK | 官方支持，文档完善 |
| 组网 | Tailscale | 零配置 P2P VPN，安全免运维 |
| AI 后端 | OpenAI + Claude + Ollama | 多模型灵活切换 |
| 进程管理 | launchd (macOS) | Mac Mini 原生服务管理 |
