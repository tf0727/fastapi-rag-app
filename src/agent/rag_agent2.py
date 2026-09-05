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
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from typing_extensions import TypedDict

api_key = os.getenv("DASHSCOPE_API_KEY", "sk-f6fbb3799b8d4c698bcb3334effc474b")
os.environ["OPENAI_API_KEY"] = api_key

llm_model = ChatOpenAI(model=os.getenv("CHAT_MODEL", "qwen-plus"), base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), api_key=api_key, temperature=0)

# 本地embedding模型
embed = HuggingFaceEmbeddings(model_name=os.getenv("EMBEDDING_MODEL", "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5"), model_kwargs={'device': os.getenv("EMBEDDING_DEVICE", "cpu")})

VS_PATH = "../../faiss-pkl"
vector_store = FAISS.load_local(folder_path=VS_PATH,embeddings=embed,allow_dangerous_deserialization=True)
retriever_tool = create_retriever_tool(vector_store.as_retriever(search_kwargs={"k": 10}),name="retrieve",description="Search and return relevant sections from database.")

class AgentState(MessagesState):
    next: str

def rewrite_question(state: AgentState):
    question = state["messages"][-1].content

    system_prompt = f"""你的任务是改写用户的输入，使其更加清晰、具体和易于理解，表达更准确，便于检索相关信息。要求如下：
1. 如果用户输入的是疑问句，需要改写为意图明确的陈述句；
2. 保持用户的核心意图不变，但使其更加明确和结构化。
样例如下：
```
用户的输入：我想用用llamafactory 进行模型微调，该怎么办？
改写后的陈述句：使用llamafactory进行微调的方法与步骤

用户的输入：小米集团在气候环境上的战略有哪些？
改写后的陈述句：小米集团在气候环境上的战略布局
```
"""
    # 构建消息
    enhanced_messages = [{"role": "system", "content":system_prompt},
                         {"role": "user","content":question}]
    model_response = llm_model.invoke(enhanced_messages)
    # response_content = model_response.content

    return {"messages":[model_response]}

def generate_query_or_respond(state:AgentState):
    SYSTEM_INSTRUCTION = (
        "你是一个助手，你需要根据用户问题来检索并回答。"
        "通过调用工具`retriever_tool`来获取更多上下文信息。"
    )

    response = llm_model.bind_tools([retriever_tool]).invoke(
        [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            *state["messages"],
        ]
    )
    # response = retriever_tool.invoke(state["messages"][0].content)
    # msg = ToolMessage(content=response)
    # return {"messages": state["messages"] + [msg]}
    return {"messages": [response]}


def grade_documents(state: AgentState):
    question = state["messages"][0].content  # original user question
    ctx = state["messages"][-1].content      # retriever output
    # prompt = GRADE_PROMPT.format(question=question, context=ctx)
    # result = grader_model.with_structured_output(GradeDoc).ainvoke([
    #     {"role": "user", "content": prompt}
    # ])
    # # 暂时去掉rewrite_question功能，如果文档不相关，直接生成答案
    # return "generate_answer" if result.binary_score.lower().startswith("y") else "generate_answer"
    return {"message":state}

graph = StateGraph(AgentState)
graph.add_node("rewrite_question", rewrite_question)
# graph.add_node("retriever", retriever)
graph.add_node("retrieve", ToolNode([retriever_tool]))
graph.add_node("generate_query_or_respond", generate_query_or_respond)
graph.add_node("grade_documents", grade_documents)


graph.add_edge(START, "rewrite_question")
graph.add_edge("rewrite_question", "generate_query_or_respond")
graph.add_edge("generate_query_or_respond", "retrieve")
graph.add_edge("retrieve", "grade_documents")

graph = graph.compile()

graph.invoke({"messages":[HumanMessage(content="请介绍下开源开发者平台：Xiaomi Vela")]})
