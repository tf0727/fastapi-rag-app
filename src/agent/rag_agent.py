from __future__ import annotations

import os
from typing import Literal
from dotenv import load_dotenv
load_dotenv(override=True)
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import create_retriever_tool
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# LLM & Embeddings
# ---------------------------------------------------------------------------
api_key = os.getenv("DASHSCOPE_API_KEY", "sk-f6fbb3799b8d4c698bcb3334effc474b")
os.environ["OPENAI_API_KEY"] = api_key

# 初始化LLM
llm_model =        ChatOpenAI(model=os.getenv("CHAT_MODEL", "qwen-plus"), base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), api_key=api_key, temperature=0)

# 本地embedding模型
embed = HuggingFaceEmbeddings(
    model_name=os.getenv("EMBEDDING_MODEL", "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5"),
    model_kwargs={'device': os.getenv("EMBEDDING_DEVICE", "cpu")}
)

# ---------------------------------------------------------------------------
# Vector store & Retriever tool
# ---------------------------------------------------------------------------
# VS_PATH = "./faiss-pkl"
VS_PATH = "../../faiss-pkl"

vector_store = FAISS.load_local(
    folder_path=VS_PATH,
    embeddings=embed,
    allow_dangerous_deserialization=True,
)
retriever_tool = create_retriever_tool(
    vector_store.as_retriever(search_kwargs={"k": 3}),
    name="database",
    description="Search and return relevant sections from database.",
)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = (
    "你是一个助手，你需要根据用户问题来检索并回答。"
    "通过调用工具`retriever_tool`来获取更多上下文信息。"
)

GRADE_PROMPT = (
    "你是一个评估者，负责评估检索到的文档与用户问题的相关性。\n"
    "检索到的文档：\n{context}\n\n用户问题：{question}\n"
    "如果相关则返回'yes'，否则返回'no'。请以JSON格式回复，字段名为'binary_score'。"
)



ANSWER_PROMPT = (
    "你是一个专业的知识助手。"
    "请根据提供的上下文信息，筛选相关内容，尽可能完整、准确、客观地回答用户的问题。"
    "请使用标准Markdown格式输出，确保回答结构清晰、易读。\n\n"
    
    "指导原则：\n"
    "- 如果上下文包含代码片段，使用三个反引号(```)引用以保留格式。\n"
    "- 如果上下文包含图片(例如![alt](url))且与问题相关，可以在回复中包含该图片。\n"
    "- 使用适当的Markdown标题、列表、表格等元素组织回答结构。\n"
    "- 如果用户明确要求只返回图片，直接从上下文中返回对应的图片内容。\n"
    "- 基于事实回答，不要添加上下文中没有的信息。\n"
    "- 如果上下文与问题不相关或无法回答问题，请明确告知：'根据现有资料无法回答该问题。'\n\n"

    "用户问题：{question}\n\n"
    "参考上下文：\n{context}"
)

# ---------------------------------------------------------------------------
# LangGraph Nodes
# ---------------------------------------------------------------------------
def generate_query_or_respond(state: MessagesState):
    """LLM decides to answer directly or call retriever tool."""
    response = llm_model.bind_tools([retriever_tool]).invoke(
        [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            *state["messages"],
        ]
    )
    return {"messages": [response]}


class GradeDoc(BaseModel):
    binary_score: str = Field(description="Relevance score 'yes' or 'no'.")


def grade_documents(state: MessagesState) -> Literal["generate_answer", "rewrite_question"]:
    # question = state["messages"][0].content  # original user question
    # ctx = state["messages"][-1].content      # retriever output
    # prompt = GRADE_PROMPT.format(question=question, context=ctx)
    # result = grader_model.with_structured_output(GradeDoc).invoke([
    #     {"role": "user", "content": prompt}
    # ])
    # # 暂时去掉rewrite_question功能，如果文档不相关，直接生成答案
    # return "generate_answer" if result.binary_score.lower().startswith("y") else "generate_answer"
    pass


def rewrite_question(state: MessagesState):
    question = state["messages"][0].content

    prompt = f"""你的任务是改写用户的输入，使其更加清晰、具体和易于理解，表达更准确，便于检索相关信息。要求如下："
1. 如果用户输入的是疑问句，需要改写为意图明确的陈述句；
2. 保持问题的核心意图不变，但使其更加明确和结构化。
用户的输入：{question}
改写后："""

    resp = llm_model.invoke([{"role": "user", "content": prompt}])
    return {"messages": [{"role": "user", "content": resp.content}]}



def generate_answer(state: MessagesState):
    question = state["messages"][0].content
    ctx = state["messages"][-1].content
    prompt = ANSWER_PROMPT.format(question=question, context=ctx)
    resp = llm_model.invoke([{"role": "user", "content": prompt}])
    return {"messages": [resp]}

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------
workflow = StateGraph(MessagesState)
workflow.add_node("rewrite_question", rewrite_question)
workflow.add_node("generate_query_or_respond", generate_query_or_respond)
workflow.add_node("retrieve", ToolNode([retriever_tool]))
workflow.add_node("generate_answer", generate_answer)

# 调整流程：START -> rewrite_question -> generate_query_or_respond -> retrieve -> generate_answer
workflow.add_edge(START, "rewrite_question")
workflow.add_edge("rewrite_question", "generate_query_or_respond")
workflow.add_edge("generate_query_or_respond", "retrieve")
workflow.add_conditional_edges("retrieve", grade_documents)
workflow.add_edge("generate_answer", END)

rag_agent = workflow.compile(name="rag_agent")