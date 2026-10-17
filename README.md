# 小米智能问答系统

基于 FastAPI、LangGraph 和 Next.js 的小米 RAG 问答项目。支持多轮问题补全、相关性判断、问题改写和查询路由：公司信息使用 FAISS 检索，产品信息使用 Elasticsearch 检索，通义千问生成答案。

## 组件

- `main.py`：FastAPI 服务，提供单轮问答、多轮会话和历史管理接口。
- `src/agent/retriever8.py`：当前 FastAPI 使用的 RAG 流水线；其他 retriever 文件保留迭代版本。
- `xiaomi_entity/`：产品数据导入与 Elasticsearch 检索。
- `faiss-pkl/`：公司知识向量索引；仅加载可信来源的 pickle 索引。
- `langgraph.json`：9 个图的 LangGraph Server 配置。
- `agent-chat-ui/`：连接 LangGraph Server 的 Next.js 前端。

## 本地配置

需要 Python 3.11+、Elasticsearch 9 及 `xiaomi_products` 索引，以及可用的 DashScope API Key。

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[server]"
Copy-Item .env.example .env
```

编辑 `.env`，填写 `DASHSCOPE_API_KEY`，并确认 `EMBEDDING_MODEL`、`VECTORSTORE_PATH`、`ELASTICSEARCH_URL`。
构建和查询索引时必须使用匹配的 embedding 模型。模型也可指定为本地目录。
历史代码保留了本机路径默认值，新机器应显式设置这些变量。

## FastAPI 问答接口

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 2025
```

接口文档：`http://127.0.0.1:2025/docs`。

| 接口 | 用途 |
| --- | --- |
| `POST /ask` | 单轮问答 |
| `POST /chat` | 多轮问答，返回或复用 `session_id` |
| `GET /chat/history?session_id=...` | 查看内存中的会话历史 |
| `POST /chat/clear` | 清空指定会话 |
| `GET /health` | 查看图是否加载 |

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:2025/chat -ContentType 'application/json' -Body '{"question":"小米有哪些手机？","verbose":true}'
```

## LangGraph Server 与聊天前端

前端使用 LangGraph 的 threads/runs 协议，需要单独启动 LangGraph Server：

```powershell
.\start-langgraph.ps1
```

脚本默认端口为 `2026`，也可传入 `-Port`。在 `agent-chat-ui` 目录执行：

```powershell
pnpm install
Copy-Item .env.example .env
# 将 NEXT_PUBLIC_API_URL 改为 http://127.0.0.1:2026
# 将 NEXT_PUBLIC_ASSISTANT_ID 改为 retriever8
pnpm dev
```

前端地址为 `http://localhost:3000`。详细用法与代理配置见 [前端文档](agent-chat-ui/README.md)。

## 认证与凭据

当前 FastAPI 接口没有用户认证或会话归属校验，`session_id` 只是对话标识；CORS 配置也不构成身份验证。直接运行 `python main.py` 默认监听 `0.0.0.0`，本地使用可采用上面的 loopback 启动命令。

模型凭据 `DASHSCOPE_API_KEY` 留在 Python 服务端。前端直连 LangGraph 时可把用户输入的 LangSmith API Key 存在浏览器 localStorage；代理模式通过 Next.js 服务端的 `LANGSMITH_API_KEY` 访问上游。代理本身未实现用户登录。

组件、两条请求路径、凭据生命周期及当前边界详见 [认证说明](docs/AUTHENTICATION.md)。真实 `.env`、依赖缓存及临时文档不提交到 Git。

## 验证范围

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev,test]"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy main.py --follow-imports=skip --ignore-missing-imports
.\.venv\Scripts\python.exe -m pytest tests -q
```

GitHub Actions 对 Python 3.11/3.12 执行代码检查、API 入口类型检查和 20 个测试，覆盖图入口配置、凭据检查、会话长度限制、历史隔离、HTTP 问答、清空和异常回滚。RAG 图由测试替身替换，不读取开发者 `.env`，不调用付费模型或检索服务。

Python 检查采用 E/F/I 正确性与导入规则，保留示例中的控制台输出和中文教学注释；类型检查限定在 FastAPI 入口，不把历史实验图宣称为已通过严格类型检查。原模板引用不存在的 `agent.graph` 的测试已替换，旧的每日集成测试工作流已合并进推送时执行的 CI。

前端工作流位于根目录 `.github/workflows/frontend.yml`，执行依赖锁定安装、lint、TypeScript 检查和生产构建。也可在 `agent-chat-ui` 运行 `pnpm lint`、`pnpm typecheck` 和 `pnpm build`；构建使用的 Google Fonts 下载需要网络连接。

完整 RAG 问答验证仍需要本地模型、匹配的 FAISS 索引、Elasticsearch 数据及有效服务商凭据；上述自动检查不代表真实模型和检索服务已端到端验证。

## 来源与许可

LangGraph 项目和 Agent Chat UI 基于原有开源模板修改。许可见 [LICENSE](LICENSE) 和 [前端 LICENSE](agent-chat-ui/LICENSE)。
