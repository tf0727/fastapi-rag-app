"""
create_retriever_tool 使用示例

这个demo展示了如何使用 create_retriever_tool 创建一个检索工具，
并在 LangGraph 中使用它来构建一个智能问答系统。
"""

from __future__ import annotations
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import create_retriever_tool
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage

# 加载环境变量
load_dotenv(override=True)

api_key = os.getenv("DASHSCOPE_API_KEY", "sk-f6fbb3799b8d4c698bcb3334effc474b")
os.environ["OPENAI_API_KEY"] = api_key

# 初始化 LLM
llm = ChatOpenAI(
    model=os.getenv("CHAT_MODEL", "qwen-plus"),
    base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    api_key=api_key,
    temperature=0
)

# 本地 Embedding 模型
embeddings = HuggingFaceEmbeddings(
    model_name=os.getenv("EMBEDDING_MODEL", "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5"),
    model_kwargs={'device': os.getenv("EMBEDDING_DEVICE", "cpu")}
)

VS_PATH = os.getenv("VECTORSTORE_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "faiss-pkl"))

vector_store = FAISS.load_local(
    folder_path=VS_PATH,
    embeddings=embeddings,
    allow_dangerous_deserialization=True,
)

# 从向量数据库创建检索器，配置检索参数
retriever = vector_store.as_retriever(
    search_type="similarity",  # 相似度搜索
    search_kwargs={"k": 5}  # 返回前5个最相关的文档
)


# 这是关键步骤！将检索器封装成一个工具
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="xiaomi_knowledge_base",  # 工具名称，要有意义
    description=(
        "搜索相关信息。"
    )
)

SYSTEM_PROMPT = """你是一个专业的智能助手。"""

def retriever(state: MessagesState):
    # 手动调用 retriver
    ans = retriever_tool.invoke(state["messages"][0].content)

    return {"messages": [AIMessage(content=ans)]}


def generate_answer(state: MessagesState):
    """
    生成最终答案节点

    这个节点会基于检索到的上下文生成最终答案
    """
    # 获取用户的原始问题
    user_question = state["messages"][0].content

    # 获取检索到的上下文（最后一条工具消息）
    context = state["messages"][-1].content

    # 构建答案生成的提示词
    answer_prompt = f"""基于以下检索到的上下文信息，回答用户的问题。

用户问题：{user_question}

检索到的上下文：
{context}

要求：
1. 请基于上下文详细回答
2. 使用Markdown格式组织答案
3. 不要添加上下文中没有的信息
4. 如果检索到的上下文和用户输入无关，请直接回复：不知道！

请回答："""

    response = llm.invoke([{"role": "user", "content": answer_prompt}])

    return {"messages": [response]}

# 创建状态图
workflow = StateGraph(MessagesState)

workflow.add_node("retriever", retriever)  # 工具节点
workflow.add_node("generate", generate_answer)

workflow.add_edge(START, "retriever")  # 开始 -> Agent
workflow.add_edge("retriever", "generate")  # 工具 -> 生成答案
workflow.add_edge("generate", END)  # 生成答案 -> 结束


def ask_question(question: str):
    print(f"\n{'=' * 80}")
    print(f"问题: {question}")
    print(f"{'=' * 80}\n")

    # 调用 Agent
    result = app.invoke({"messages": [HumanMessage(content=question)]})

    # 获取最终答案
    final_answer = result["messages"][-1].content


    print("最终答案:")
    print(final_answer)

# 编译图
app = workflow.compile()

if __name__ == "__main__":
    # ask_question("小米集团在2024年的碳排放目标是什么？")
    ask_question("帮我写一首押韵的古诗：苍天饶过谁？")    # 如果用户的问题不在知识库的范畴，回复：不知道

