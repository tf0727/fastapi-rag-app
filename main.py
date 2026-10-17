"""小米智能问答（RAG）系统 - FastAPI 服务入口

将 src/agent/retriever8.py 中的完整 RAG 流水线封装为 HTTP 接口：
问题补全 -> 相关性判断 -> 问题改写 -> 查询路由 ->
FAISS(公司信息) / Elasticsearch(产品信息) 检索 -> 生成答案。

启动方式：
    python main.py                     # 默认端口 2025
    uvicorn main:app --port 2025       # 或使用 uvicorn 命令

接口文档：http://127.0.0.1:2025/docs
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 环境初始化（必须在导入 retriever8 之前完成）
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

from src.agent import retriever8  # noqa: E402

# retriever8 中编译好的 LangGraph 流水线
GRAPH = retriever8.app
_extract_text = retriever8.extract_text_content

# 每个会话最多保留的消息条数（控制上下文长度）
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))


# ---------------------------------------------------------------------------
# 会话管理（内存存储：session_id -> 消息历史）
# ---------------------------------------------------------------------------
class SessionStore:
    """多轮对话会话存储，线程安全。"""

    def __init__(self) -> None:
        self._sessions: dict[str, list] = {}
        self._lock = threading.Lock()

    def history(self, session_id: str) -> list:
        with self._lock:
            return self._sessions.setdefault(session_id, [])

    def append(self, session_id: str, messages: list) -> None:
        with self._lock:
            history = self._sessions.setdefault(session_id, [])
            history.extend(messages)
            if len(history) > MAX_HISTORY_MESSAGES:
                del history[: len(history) - MAX_HISTORY_MESSAGES]

    def clear(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def snapshot(self, session_id: str) -> list[dict]:
        with self._lock:
            history = self._sessions.get(session_id, [])
            return [
                {
                    "role": "user" if isinstance(m, HumanMessage) else "assistant",
                    "content": _extract_text(m.content),
                }
                for m in history
            ]


SESSIONS = SessionStore()


# ---------------------------------------------------------------------------
# 流水线辅助函数
# ---------------------------------------------------------------------------
def _extract_steps(messages: list) -> list[dict]:
    """从工具消息中提取中间步骤（补全/判断/改写/路由/检索）。"""
    steps: list[dict] = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        tool_id = getattr(msg, "tool_call_id", "") or ""
        content = _extract_text(msg.content)
        if tool_id == "query_completion_tool":
            steps.append({"step": "问题补全", "result": content})
        elif tool_id == "relevance_check_tool":
            steps.append({"step": "相关性判断", "result": content})
        elif tool_id == "rewrite_tool":
            steps.append({"step": "问题改写", "result": content})
        elif tool_id == "query_router_tool":
            steps.append({"step": "查询路由", "result": content})
        elif tool_id in ("faiss_retriever_tool", "elasticsearch_retriever_tool"):
            steps.append(
                {
                    "step": "知识检索",
                    "source": (
                        "FAISS(公司信息)"
                        if "faiss" in tool_id
                        else "Elasticsearch(产品信息)"
                    ),
                    "result_length": len(content),
                }
            )
    return steps


def _run_pipeline(history: list) -> tuple[str, list[dict]]:
    """同步执行 RAG 流水线，返回 (最终答案, 中间步骤)。"""
    result = GRAPH.invoke({"messages": list(history)})
    messages = result["messages"]
    return _extract_text(messages[-1].content), _extract_steps(messages)


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    """对话请求。"""

    question: str = Field(..., description="用户问题")
    session_id: str | None = Field(
        None, description="会话ID；不传则自动生成，传相同ID可维护多轮上下文"
    )
    verbose: bool = Field(False, description="是否返回中间步骤（补全/改写/路由/检索）")


class ChatResponse(BaseModel):
    """对话响应。"""

    session_id: str
    answer: str
    steps: list[dict] = []


class SessionRequest(BaseModel):
    """会话操作请求。"""

    session_id: str


# ---------------------------------------------------------------------------
# FastAPI 应用
# ---------------------------------------------------------------------------
app = FastAPI(
    title="小米智能问答系统",
    description=(
        "基于 LangGraph 的小米 RAG 问答服务：问题补全、相关性判断、问题改写、"
        "查询路由，产品信息走 Elasticsearch，公司信息走 FAISS 向量库。"
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="服务信息")
async def root():
    """返回服务简介与可用接口。"""
    return {
        "service": "小米智能问答系统（RAG）",
        "docs": "/docs",
        "endpoints": {
            "POST /chat": "多轮对话（通过 session_id 维护上下文）",
            "POST /ask": "单轮问答（不维护历史）",
            "GET /chat/history?session_id=xxx": "查看会话历史",
            "POST /chat/clear": "清空会话历史",
            "GET /health": "健康检查",
        },
    }


@app.get("/health", summary="健康检查")
async def health():
    """检查服务与 RAG 流水线是否就绪。"""
    return {"status": "ok", "graph_loaded": GRAPH is not None}


@app.post("/chat", response_model=ChatResponse, summary="多轮对话")
async def chat(req: ChatRequest):
    """多轮对话接口，同一 session_id 下自动维护对话历史并支持指代补全。"""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question 不能为空")

    session_id = req.session_id or str(uuid.uuid4())
    history = SESSIONS.history(session_id)
    history.append(HumanMessage(content=question))

    try:
        answer, steps = await asyncio.to_thread(_run_pipeline, history)
    except Exception as e:  # 流水线异常时回滚本轮用户消息
        history.pop()
        raise HTTPException(status_code=500, detail=f"问答流水线执行失败：{e}")

    SESSIONS.append(session_id, [AIMessage(content=answer)])
    return ChatResponse(
        session_id=session_id, answer=answer, steps=steps if req.verbose else []
    )


@app.post("/ask", response_model=ChatResponse, summary="单轮问答")
async def ask(req: ChatRequest):
    """单轮问答接口，不维护任何历史上下文。"""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question 不能为空")

    try:
        answer, steps = await asyncio.to_thread(
            _run_pipeline, [HumanMessage(content=question)]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答流水线执行失败：{e}")

    return ChatResponse(
        session_id=req.session_id or "", answer=answer, steps=steps if req.verbose else []
    )


@app.get("/chat/history", summary="查看会话历史")
async def chat_history(session_id: str):
    """查看指定会话的历史消息。"""
    return {"session_id": session_id, "messages": SESSIONS.snapshot(session_id)}


@app.post("/chat/clear", summary="清空会话历史")
async def chat_clear(req: SessionRequest):
    """清空指定会话的历史。"""
    cleared = SESSIONS.clear(req.session_id)
    return {"session_id": req.session_id, "cleared": cleared}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "2025"))
    print(f"启动小米智能问答服务: http://{host}:{port} (接口文档 /docs)")
    uvicorn.run(app, host=host, port=port)
