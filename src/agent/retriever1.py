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
from langchain_core.messages import HumanMessage

# 加载环境变量
load_dotenv(override=True)

# ==============================================================================
# 第一步：初始化 LLM 和 Embedding 模型
# ==============================================================================
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

# ==============================================================================
# 第二步：加载向量数据库并创建检索器
# ==============================================================================
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

# ==============================================================================
# 第三步：使用 create_retriever_tool 创建检索工具
# ==============================================================================
# 这是关键步骤！将检索器封装成一个工具

retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="xiaomi_knowledge_base",  # 工具名称，要有意义
    description=(
        "搜索小米集团的相关文档。"
        "当用户询问关于小米的环境、社会、治理、可持续发展等问题时使用此工具。"
        "输入应该是一个搜索查询。"
    )
)

# ==============================================================================
# 第四步：定义 Agent 的系统提示词
# ==============================================================================
SYSTEM_PROMPT = """你是一个专业的人工智能助手，你需要友好的回复用户的所有问题。"""


# ==============================================================================
# 第五步：定义 LangGraph 节点
# ==============================================================================

def agent_node(state: MessagesState):
    """
    Agent 节点：LLM 决定是否需要调用检索工具

    这里 LLM 会分析用户问题，决定：
    - 是否需要检索信息
    - 如果需要，生成检索查询
    """
    # 绑定工具到 LLM
    llm_with_tools = llm.bind_tools([retriever_tool])

    # 构建消息列表
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role":"user","content":state["messages"][0].content}
    ]

    # 调用 LLM
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}


def generate_answer(state: MessagesState):
    """
    生成最终答案节点

    这个节点会基于检索到的上下文生成最终答案
    """
    # 获取用户的原始问题
    user_question = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "human":
            user_question = msg.content
            break

    # 获取检索到的上下文（最后一条工具消息）
    context = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "tool":
            context = msg.content
            break

    # 构建答案生成的提示词
    answer_prompt = f"""基于以下检索到的上下文信息，回答用户的问题。

用户问题：{user_question}

检索到的上下文：
{context}

要求：
1. 如果上下文包含相关信息，请基于上下文详细回答
2. 使用Markdown格式组织答案
3. 如果上下文与问题不太相关，请明确说明
4. 不要添加上下文中没有的信息

请回答："""

    response = llm.invoke([{"role": "user", "content": answer_prompt}])

    return {"messages": [response]}


def route_after_agent(state: MessagesState):
    """
    路由函数：决定 Agent 之后的流程

    - 如果 LLM 调用了工具，则路由到工具节点
    - 如果 LLM 直接回答，则结束
    """
    last_message = state["messages"][-1]

    # 检查是否有工具调用
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"

    return END


# ==============================================================================
# 第六步：构建 LangGraph 工作流
# ==============================================================================

# 创建状态图
workflow = StateGraph(MessagesState)

# 添加节点
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode([retriever_tool]))  # 工具节点
workflow.add_node("generate", generate_answer)

# 定义流程
workflow.add_edge(START, "agent")  # 开始 -> Agent
workflow.add_conditional_edges(
    "agent",  # Agent 之后
    route_after_agent,  # 使用路由函数决定
    {
        "tools": "tools",  # 如果需要工具 -> 工具节点
        END: END  # 否则结束
    }
)
workflow.add_edge("tools", "generate")  # 工具 -> 生成答案
workflow.add_edge("generate", END)  # 生成答案 -> 结束


# ==============================================================================
# 第七步：测试运行
# ==============================================================================

def ask_question(question: str):
    """
    提问函数

    Args:
        question: 用户问题

    Returns:
        最终答案
    """
    print(f"\n{'=' * 80}")
    print(f"问题: {question}")
    print(f"{'=' * 80}\n")

    # 调用 Agent
    result = app.invoke({"messages": [HumanMessage(content=question)]})

    # 打印流程
    print("\n执行流程：")
    for i, msg in enumerate(result["messages"], 1):
        msg_type = msg.__class__.__name__
        print(f"{i}. {msg_type}", end="")

        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f" -> 调用工具: {msg.tool_calls[0]['name']}")
        elif msg_type == "ToolMessage":
            print(f" -> 检索到 {len(msg.content)} 个字符的内容")
        else:
            print()

    # 获取最终答案
    final_answer = result["messages"][-1].content

    print(f"\n{'=' * 80}")
    print("最终答案:")
    print(f"{'=' * 80}")
    print(final_answer)
    print(f"{'=' * 80}\n")

    return final_answer


# 编译图
app = workflow.compile()

if __name__ == "__main__":
    ask_question("小米集团在2024年的碳排放目标是什么？")
    # ask_question("帮我写一首押韵的古诗：苍天饶过谁？")
    # llm.bind_tools 绑定工具，自动决定是否调用召回工具

