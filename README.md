# 智能问答系统

基于 FastAPI、LangGraph 与 Next.js 的 RAG 问答系统。工程上采用“多轮问题补全 → 相关性判断 → 问题改写 → 查询路由 → 检索 → 生成”的流水线编排：公司信息走 FAISS 向量检索，产品信息走 Elasticsearch 检索，答案由通义千问生成。

本文档从工程视角描述系统分层、模块职责、请求链路、接口契约、配置与凭据生命周期、质量保障及已知边界。启动细节见对应组件文档。

## 1. 工程目标与非目标

### 1.1 工程目标

- 提供可本地运行的 RAG 问答服务，支持单轮问答与多轮会话。
- 通过 LangGraph 编排多阶段流程，支持多轮问题补全、相关性判断、问题改写与查询路由。
- 按数据域拆分检索通道：公司知识使用 FAISS 向量索引，产品数据使用 Elasticsearch。
- 提供 FastAPI 问答接口与基于 LangGraph Server 的 Next.js 聊天前端两条访问路径。
- 建立可复现的本地依赖安装、代码检查、类型检查与自动化测试流程。

### 1.2 非目标

- 当前 FastAPI 接口不提供用户认证与会话归属校验；`session_id` 仅为对话标识。
- CORS 配置不构成身份验证。
- 自动化检查不替代真实模型、索引与检索服务的端到端验证。
- 不在仓库中提交真实 `.env`、依赖缓存与临时文档。

## 2. 系统架构与分层

| 层 | 工程职责 | 实现 |
|---|---|---|
| 前端 | LangGraph Server 聊天界面，使用 threads/runs 协议 | Next.js，`agent-chat-ui/` |
| API 入口 | 单轮问答、多轮会话、历史管理、健康检查 | FastAPI，`main.py` |
| RAG 编排 | 多轮补全、相关性判断、问题改写、查询路由、检索与生成 | LangGraph，`langgraph.json` 配置 9 个图 |
| RAG 流水线 | 当前 FastAPI 使用的检索与生成实现 | `src/agent/retriever8.py` |
| 产品检索 | 产品数据导入与 Elasticsearch 检索 | `xiaomi_entity/` |
| 公司知识检索 | 公司知识向量索引加载与检索 | `faiss-pkl/` |
| 模型层 | 向量化与答案生成 | 通义千问，DashScope API |
| 质量保障 | lint、类型检查、单元测试、前端构建 | ruff、mypy、pytest、GitHub Actions、pnpm |

数据域路由约定：

- 公司信息 → FAISS 向量检索。
- 产品信息 → Elasticsearch 检索。
- 答案生成 → 通义千问。

## 3. 项目目录与模块职责

```text
main.py                  FastAPI 服务，提供单轮问答、多轮会话和历史管理接口
src/agent/retriever8.py  当前 FastAPI 使用的 RAG 流水线；其他 retriever 文件保留迭代版本
xiaomi_entity/           产品数据导入与 Elasticsearch 检索
faiss-pkl/               公司知识向量索引；仅加载可信来源的 pickle 索引
langgraph.json           9 个图的 LangGraph Server 配置
agent-chat-ui/           连接 LangGraph Server 的 Next.js 前端
tests/                   后端测试
.github/workflows/       CI 工作流，含前端工作流 frontend.yml
```

工程边界约定：

- `main.py` 仅作为 API 入口与图调度适配层，不承载检索与生成实现细节。
- `src/agent/retriever8.py` 是当前生效的 RAG 流水线；其他 retriever 文件为迭代保留版本，不应被默认路径引用。
- `xiaomi_entity/` 与 `faiss-pkl/` 分别对应产品域与公司知识域的检索资源。
- `langgraph.json` 是 LangGraph Server 的图注册配置，图入口变更需同步测试。
- `agent-chat-ui/` 独立于 FastAPI 服务，通过 LangGraph threads/runs 协议访问后端。

## 4. 请求链路

### 4.1 FastAPI 路径

1. 客户端请求 `POST /ask` 或 `POST /chat`。
2. FastAPI 加载对应图并进入 RAG 流水线。
3. 多轮场景下执行问题补全、相关性判断与问题改写。
4. 按查询路由选择检索通道：公司信息走 FAISS，产品信息走 Elasticsearch。
5. 检索结果进入通义千问生成答案。
6. `POST /chat` 返回或复用 `session_id`；会话历史保存在内存中。
7. `GET /chat/history` 查看会话历史，`POST /chat/clear` 清空指定会话。
8. `GET /health` 返回图是否加载。

### 4.2 LangGraph Server 路径

1. 前端通过 LangGraph 的 threads/runs 协议发起请求。
2. LangGraph Server 按 `langgraph.json` 加载图。
3. 前端需配置 `NEXT_PUBLIC_API_URL` 与 `NEXT_PUBLIC_ASSISTANT_ID`。
4. 直连模式下，用户输入的 LangSmith API Key 存于浏览器 `localStorage`。
5. 代理模式下，通过 Next.js 服务端的 `LANGSMITH_API_KEY` 访问上游；代理本身未实现用户登录。

## 5. 接口契约

FastAPI 启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 2025
```

接口文档：`http://127.0.0.1:2025/docs`。

| 接口 | 用途 |
|---|---|
| `POST /ask` | 单轮问答 |
| `POST /chat` | 多轮问答，返回或复用 `session_id` |
| `GET /chat/history?session_id=...` | 查看内存中的会话历史 |
| `POST /chat/clear` | 清空指定会话 |
| `GET /health` | 查看图是否加载 |

调用示例：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:2025/chat `
  -ContentType 'application/json' `
  -Body '{"question":"小米有哪些手机？","verbose":true}'
```

接口工程约束：

- 会话历史保存在内存中，服务重启后不保证保留。
- `session_id` 仅作为对话标识，不作为权限凭据。
- 当前接口无用户认证与会话归属校验。

## 6. 配置与凭据生命周期

### 6.1 本地依赖与配置

前置条件：

- Python 3.11+
- Elasticsearch 9 及 `xiaomi_products` 索引
- 可用的 DashScope API Key

初始化：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[server]"
Copy-Item .env.example .env
```

编辑 `.env`，填写 `DASHSCOPE_API_KEY`，并确认：

- `EMBEDDING_MODEL`
- `VECTORSTORE_PATH`
- `ELASTICSEARCH_URL`

配置约束：

- 构建和查询索引时必须使用匹配的 embedding 模型。
- 模型也可指定为本地目录。
- 历史代码保留了本机路径默认值，新机器应显式设置这些变量。
- 真实 `.env`、依赖缓存及临时文档不提交到 Git。

### 6.2 凭据边界

| 凭据 | 存放位置 | 说明 |
|---|---|---|
| `DASHSCOPE_API_KEY` | Python 服务端 `.env` | 不进入前端 |
| `LANGSMITH_API_KEY`（直连） | 浏览器 `localStorage` | 用户输入 |
| `LANGSMITH_API_KEY`（代理） | Next.js 服务端环境变量 | 通过服务端访问上游 |

- 前端直连 LangGraph 时，Key 存于浏览器本地。
- 代理模式由 Next.js 服务端持有上游凭据。
- 代理本身未实现用户登录。
- 详细组件、请求路径与凭据生命周期见认证说明。

## 7. 构建、启动与部署

### 7.1 FastAPI 服务

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 2025
```

- 直接运行 `python main.py` 默认监听 `0.0.0.0`；本地使用建议采用上述 loopback 启动命令。

### 7.2 LangGraph Server

```powershell
.\start-langgraph.ps1
```

- 脚本默认端口为 `2026`，也可传入 `-Port`。

### 7.3 聊天前端

```powershell
Set-Location agent-chat-ui
pnpm install
Copy-Item .env.example .env
# 将 NEXT_PUBLIC_API_URL 改为 http://127.0.0.1:2026
# 将 NEXT_PUBLIC_ASSISTANT_ID 改为 retriever8
pnpm dev
```

- 前端地址：`http://localhost:3000`。
- 详细用法与代理配置见前端文档。

## 8. 测试与质量保障

### 8.1 本地检查

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,test]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy main.py --follow-imports=skip --ignore-missing-imports
.\.venv\Scripts\python.exe -m pytest tests -q
```

### 8.2 后端 CI

- GitHub Actions 对 Python 3.11/3.12 执行代码检查、API 入口类型检查和 20 个测试。
- 测试覆盖：图入口配置、凭据检查、会话长度限制、历史隔离、HTTP 问答、清空和异常回滚。
- RAG 图由测试替身替换，不读取开发者 `.env`，不调用付费模型或检索服务。

### 8.3 前端 CI

- 工作流位于根目录 `.github/workflows/frontend.yml`。
- 执行依赖锁定安装、lint、TypeScript 检查和生产构建。
- 也可在 `agent-chat-ui` 运行 `pnpm lint`、`pnpm typecheck`、`pnpm build`。
- 构建使用的 Google Fonts 下载需要网络连接。

### 8.4 检查范围约定

- Python 检查采用 E/F/I 正确性与导入规则。
- 保留示例中的控制台输出和中文教学注释。
- 类型检查限定在 FastAPI 入口，不将历史实验图宣称为已通过严格类型检查。
- 原模板引用不存在的 `agent.graph` 的测试已替换。
- 旧的每日集成测试工作流已合并进推送时执行的 CI。
- 完整 RAG 问答验证仍需要本地模型、匹配的 FAISS 索引、Elasticsearch 数据及有效服务商凭据；自动检查不代表真实模型和检索服务已端到端验证。

## 9. RAG 工程能力现状

| 能力 | 当前实现 | 工程说明 |
|---|---|---|
| 多轮问题补全 | LangGraph 图编排 | 依赖会话上下文 |
| 相关性判断 | 图内节点 | 判断检索结果是否满足问题 |
| 问题改写 | 图内节点 | 提升召回质量 |
| 查询路由 | 图内路由 | 公司信息走 FAISS，产品信息走 Elasticsearch |
| 向量检索 | FAISS | 公司知识索引 |
| 关键词检索 | Elasticsearch | 产品数据检索 |
| 答案生成 | 通义千问 | DashScope OpenAI 兼容接口 |
| 索引与模型匹配 | 配置约束 | 构建与查询必须使用匹配的 embedding 模型 |
| 引用与溯源 | 未在本文档中声明为已实现 | 需按业务要求补充 |
| 权限控制 | 未实现 | 当前接口无认证与会话归属校验 |
| 知识更新 | 依赖索引重建 | 需按数据源与业务节奏执行 |

说明：上表仅描述当前仓库可确认的能力边界，不将规划项表述为已实现能力。

## 10. 已知工程边界与风险

- FastAPI 接口没有用户认证或会话归属校验，`session_id` 只是对话标识。
- CORS 配置不构成身份验证。
- 会话历史保存在内存中，不具备持久化与跨进程一致性保证。
- 直接运行 `python main.py` 默认监听 `0.0.0.0`，存在暴露风险，本地应使用 loopback。
- 前端直连模式下 LangSmith API Key 存于浏览器 `localStorage`，安全性依赖前端环境。
- 代理模式未实现用户登录，不等同于生产级鉴权。
- 公司知识索引来自 pickle 文件，仅应加载可信来源。
- 自动化检查使用测试替身，不覆盖真实模型与检索服务的端到端行为。
- 历史代码保留本机路径默认值，跨机器部署必须显式配置环境变量。

## 11. 来源与许可

- LangGraph 项目与 Agent Chat UI 基于原有开源模板修改。
- 许可见 `LICENSE` 与前端 `LICENSE`。
