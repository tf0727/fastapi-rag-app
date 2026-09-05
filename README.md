# New LangGraph Project

## 本机启动（2026-09-05 修复）

在项目目录执行：

```powershell
.\start-langgraph.ps1
```

服务地址为 `http://127.0.0.1:2026`，接口文档为 `/docs`。
脚本使用项目 `.venv`，避免误用缺少检索依赖的 `langgraph` Conda 环境。
本机 2024 端口绑定报 WinError 10048，因此默认使用已验证的 2026；
需要其他端口时运行 `.\start-langgraph.ps1 -Port 端口号`。
前端连接此服务时也需将 API URL 配置为 `http://127.0.0.1:2026`。

当前 `.venv` 基于本机 `D:\miniconda\envs\data-base` 的 Python 3.11，
通过 `--system-site-packages` 复用已安装的 PyTorch 和 sentence-transformers，
请保留该基础环境。新机器请使用 Python 3.11 创建独立环境并安装完整依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[server]"
```

`.env` 中需配置 `DASHSCOPE_API_KEY`、`EMBEDDING_MODEL`、`VECTORSTORE_PATH`，
商品检索还需要 `ELASTICSEARCH_URL` 对应的服务及 `xiaomi_products` 索引。
本次验证包括依赖一致性、9 个图加载、健康检查和图 schema 接口，未调用付费模型接口。

[![CI](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml)

This template demonstrates a simple application implemented using [LangGraph](https://github.com/langchain-ai/langgraph), designed for showing how to get started with [LangGraph Server](https://langchain-ai.github.io/langgraph/concepts/langgraph_server/#langgraph-server) and using [LangGraph Studio](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/), a visual debugging IDE.

<div align="center">
  <img src="./static/studio_ui.png" alt="Graph view in LangGraph studio UI" width="75%" />
</div>

The core logic defined in `src/agent/graph.py`, showcases an single-step application that responds with a fixed string and the configuration provided.

You can extend this graph to orchestrate more complex agentic workflows that can be visualized and debugged in LangGraph Studio.

## Getting Started

1. Install dependencies, along with the [LangGraph CLI](https://langchain-ai.github.io/langgraph/concepts/langgraph_cli/), which will be used to run the server.

```bash
cd path/to/your/app
pip install -e . "langgraph-cli[inmem]"
```

2. (Optional) Customize the code and project as needed. Create a `.env` file if you need to use secrets.

```bash
cp .env.example .env
```

If you want to enable LangSmith tracing, add your LangSmith API key to the `.env` file.

```text
# .env
LANGSMITH_API_KEY=lsv2...
```

3. Start the LangGraph Server.

```shell
langgraph dev
```

For more information on getting started with LangGraph Server, [see here](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/).

## How to customize

1. **Define runtime context**: Modify the `Context` class in the `graph.py` file to expose the arguments you want to configure per assistant. For example, in a chatbot application you may want to define a dynamic system prompt or LLM to use. For more information on runtime context in LangGraph, [see here](https://langchain-ai.github.io/langgraph/agents/context/?h=context#static-runtime-context).

2. **Extend the graph**: The core logic of the application is defined in [graph.py](./src/agent/graph.py). You can modify this file to add new nodes, edges, or change the flow of information.

## Development

While iterating on your graph in LangGraph Studio, you can edit past state and rerun your app from previous states to debug specific nodes. Local changes will be automatically applied via hot reload.

Follow-up requests extend the same thread. You can create an entirely new thread, clearing previous history, using the `+` button in the top right.

For more advanced features and examples, refer to the [LangGraph documentation](https://langchain-ai.github.io/langgraph/). These resources can help you adapt this template for your specific use case and build more sophisticated conversational agents.

LangGraph Studio also integrates with [LangSmith](https://smith.langchain.com/) for more in-depth tracing and collaboration with teammates, allowing you to analyze and optimize your chatbot's performance.
