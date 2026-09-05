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
from langchain_core.tools import create_retriever_tool, tool
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
try:
    from xiaomi_entity.query_xiaomi_products import searcher
except:
    from query_xiaomi_products import searcher

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


# 这是关键步骤！将检索器封装成一个工具（Faiss - 公司发展信息）
faiss_retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="xiaomi_company_knowledge_base",  # 工具名称
    description=(
        "搜索小米公司发展、业务增长、ESG报告等企业信息。"
    )
)

# 创建 Elasticsearch 检索工具（产品信息）
@tool
def elasticsearch_retriever_tool(query: str) -> str:
    """搜索小米产品参数和产品信息"""
    try:
        # 使用 LLM 分析查询意图并生成搜索参数
        analysis_prompt = """你是一个专业的查询分析专家，需要分析用户的产品查询意图，并生成Elasticsearch结构化的搜索参数。

可用字段（只能使用这些字段，不要编造其他字段名）：
- 商品名称：产品名称/型号，如"小米15"
- 简介：产品简介
- 详细参数_text：详细参数纯文本
- 详细参数_文本：详细参数纯文本（别名）
- 类别：产品类别
- 价格：产品价格

规则：
1. 如果用户问题中出现具体产品型号（如小米15、小米SU7、小米手环），必须使用 match 查询"商品名称"字段，query 写产品型号，analyzer 用 ik_smart。
2. 不要添加与问题无关的 should 子句，不要编造字段。
3. 只返回JSON，不要输出任何其他说明文字。

样例如下：

用户的输入：小米15的价格多少
输出：```json
{
  "query": {
    "match": {
      "商品名称": {
        "query": "小米15",
        "analyzer": "ik_smart"
      }
    }
  },
  "size": 5
}
```

用户的输入：小米双肩包有什么颜色？
输出：```json
{
    "query": {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": "小米双肩包",
                        "fields": ["商品名称^3", "简介^2", "详细参数_text"],
                        "type": "best_fields"
                    }
                }
            ],
            "should": [
                {
                    "match": {
                        "详细参数_text": "颜色"
                    }
                }
            ]
        }
    },
    "size": 5
}
```

请严格按照JSON格式返回，不要添加任何其他说明文字。""" + f"\n用户的输入：{query}\n输出："

        # 调用 LLM 分析查询
        response = llm.invoke([{"role": "user", "content": analysis_prompt}])
        
        # 解析 LLM 返回的 JSON
        import json
        import re
        
        # 提取JSON内容（去除可能的markdown代码块标记）
        content = response.content.strip()
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 如果没有代码块，直接尝试解析整个内容
            json_str = content
        
        search_params = json.loads(json_str)

        # 字段白名单 + 结构清理：防止LLM编造字段/添加无关should导致检索结果漂移
        _ALLOWED_FIELDS = {"商品名称", "简介", "详细参数_text", "详细参数_文本", "类别", "价格"}

        def _clean_multi_match(mm):
            fields = mm.get("fields")
            if isinstance(fields, list):
                kept = [f for f in fields if f.split("^")[0].strip() in _ALLOWED_FIELDS]
                if kept:
                    mm["fields"] = kept
                    return True
                return False
            return True

        def _sanitize_search_body(body):
            if not isinstance(body, dict):
                return body
            if "multi_match" in body:
                if not _clean_multi_match(body["multi_match"]):
                    return None
            if "match" in body and isinstance(body["match"], dict):
                body["match"] = {k: v for k, v in body["match"].items() if k in _ALLOWED_FIELDS}
                if not body["match"]:
                    return None
            if "query" in body and isinstance(body["query"], dict):
                cleaned = _sanitize_search_body(body["query"])
                if cleaned is None:
                    return None
                body["query"] = cleaned
            if "bool" in body and isinstance(body["bool"], dict):
                b = body["bool"]
                # must里已经用 match 商品名称 锁定具体产品时，丢弃should，避免噪声词干扰排序
                has_product_match = any(
                    isinstance(c, dict) and isinstance(c.get("match"), dict) and "商品名称" in c["match"]
                    for c in b.get("must", []) if isinstance(c, dict)
                )
                if has_product_match:
                    b.pop("should", None)
                for key in ("must", "should", "filter", "must_not"):
                    if key in b and isinstance(b[key], list):
                        kept = []
                        for clause in b[key]:
                            cleaned = _sanitize_search_body(clause)
                            if cleaned is not None:
                                kept.append(cleaned)
                        b[key] = kept
                        if key in ("must", "filter") and not kept:
                            return None
                        if key == "should" and not kept:
                            del b[key]
            return body

        sanitized = _sanitize_search_body(search_params)
        if sanitized is None or "query" not in sanitized:
            raise ValueError("搜索参数经过字段过滤后无有效查询条件")
        search_params = sanitized
        
        # 根据分析结果调用相应的搜索方法
        results = searcher.search_by_cmd(query,search_params)
        
        return results
    
    except (json.JSONDecodeError, ValueError) as e:
        # JSON解析失败或参数过滤后无有效查询，降级为简单的混合搜索
        print(f"JSON解析失败: {e}，使用默认混合搜索")
        results = searcher.hybrid_multi_embedding_search(query, size=10)
        return results
    
    except Exception as e:
        return f"搜索产品信息时出错：{str(e)}"

SYSTEM_PROMPT = """你是一个专业的智能助手。"""

# 创建相关性判断工具
@tool
def relevance_check_tool(question: str) -> str:
    """判断用户的问题是否和小米公司业务或者产品有关"""
    relevance_prompt = f"""假设你是小米公司的智能助手，你需要判断用户的问题是否和小米公司业务或者产品有关。
如果有关，请返回：是；如果无关，请返回：不相关；无需输出其他内容。
用户问题：{question}
你的判断："""
    response = llm.invoke([{"role": "user", "content": relevance_prompt}])
    return response.content

# 辅助函数：提取文本内容（处理多模态消息格式）
def extract_text_content(content):
    """从消息内容中提取纯文本，支持字符串和多模态格式"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # 多模态格式：[{'type': 'text', 'text': '...'}, ...]
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                text_parts.append(item.get('text', ''))
        return ' '.join(text_parts)
    return str(content)

# 创建问题改写工具
@tool
def rewrite_tool(question: str) -> str:
    """改写用户问题，使其更加清晰、具体和易于理解，表达更准确，便于检索相关信息"""
    prompt = f"""你的任务是改写用户的输入，使其更加清晰、具体和易于理解，表达更准确，便于检索相关信息。要求如下："
1. 如果用户输入的是疑问句，需要改写为意图明确的陈述句；
2. 保持用户的核心意图不变，但使其更加明确和结构化。
样例如下：
```
用户的输入：我想用用llamafactory 进行模型微调，该怎么办？
改写后的陈述句：使用llamafactory进行微调的方法与步骤

用户的输入：小米集团在气候环境上的战略有哪些？
改写后的陈述句：小米集团在气候环境上的战略布局
```
用户的输入：{question}
改写后的陈述句："""
    response = llm.invoke([{"role": "user", "content": prompt}])
    return response.content

# 相关性判断节点
def relevance_check(state: MessagesState):
    """调用相关性判断工具并返回ToolMessage"""
    user_question = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "human":
            user_question = msg.content
            break

    user_question = extract_text_content(user_question)

    ans = relevance_check_tool.invoke(user_question)
    return {"messages": [ToolMessage(content=ans, tool_call_id="relevance_check_tool")]}

# Faiss 检索节点（公司信息）
def retriever_faiss(state: MessagesState):
    """调用 Faiss 检索工具并返回ToolMessage（用于公司发展信息）"""
    # 获取改写后的问题（从rewrite_node返回的消息）
    # messages: [HumanMessage, ToolMessage(相关性判断), ToolMessage(改写后问题), ToolMessage(路由结果)]
    rewritten_question = state["messages"][-2].content  # 倒数第二条是改写后的问题
    ans = faiss_retriever_tool.invoke(rewritten_question)
    return {"messages": [ToolMessage(content=ans, tool_call_id="faiss_retriever_tool")]}

# Elasticsearch 检索节点（产品信息）
def retriever_elasticsearch(state: MessagesState):
    """调用 Elasticsearch 检索工具并返回ToolMessage（用于产品信息）"""
    # 获取改写后的问题
    rewritten_question = state["messages"][-2].content  # 倒数第二条是改写后的问题
    ans = elasticsearch_retriever_tool.invoke(rewritten_question)
    return {"messages": [ToolMessage(content=ans, tool_call_id="elasticsearch_retriever_tool")]}

# 生成答案节点（用于不相关的问题）
def generate_answer(state: MessagesState):
    """生成答案"""
    # user_question = extract_text_content(state["messages"][0].content)

    user_question = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "human":
            user_question = msg.content
            break

    user_question = extract_text_content(user_question)

    response = llm.invoke([{"role": "user", "content": user_question}])
    return {"messages": [response]}

# 问题改写节点
def rewrite_node(state: MessagesState):
    """调用问题改写工具并返回ToolMessage"""

    user_question = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "human":
            user_question = msg.content
            break

    user_question = extract_text_content(user_question)

    # user_question = extract_text_content(state["messages"][0].content)
    ans = rewrite_tool.invoke(user_question)
    return {"messages": [ToolMessage(content=ans, tool_call_id="rewrite_tool")]}

# 路由节点：判断查询类型
@tool
def query_router_tool(question: str) -> str:
    """判断用户查询是关于产品信息还是公司发展信息"""
    router_prompt = f"""你是一个查询分类专家，需要判断用户的问题属于哪个类别：

类别1 - 产品信息：关于小米具体产品的参数、功能、价格、配置、型号、规格等信息
类别2 - 公司信息：关于小米公司的发展历程、业务增长、ESG报告、企业战略、环境政策、社会责任等信息

请根据用户的问题，判断其属于哪个类别。
- 如果是关于具体产品的，请只返回：产品
- 如果是关于公司发展的，请只返回：公司
- 如果无法判断，优先返回：公司

用户问题：{question}

你的判断："""
    response = llm.invoke([{"role": "user", "content": router_prompt}])
    return response.content.strip()

def query_router_node(state: MessagesState):
    """路由节点：判断查询类型"""
    # 获取改写后的问题
    rewritten_question = state["messages"][-1].content
    route_result = query_router_tool.invoke(rewritten_question)
    # 将路由结果添加到消息中
    return {"messages": [ToolMessage(content=route_result, tool_call_id="query_router_tool")]}



def generate_answer_with_retriever(state: MessagesState):
    """
    生成最终答案节点

    这个节点会基于检索到的上下文生成最终答案
    """
    # 获取用户的原始问题
    # user_question = extract_text_content(state["messages"][0].content)

    user_question = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "human":
            user_question = msg.content
            break

    user_question = extract_text_content(user_question)

    # 获取检索到的上下文（最后一条工具消息）
    context = state["messages"][-1].content

    # 构建答案生成的提示词
    answer_prompt = f"""基于以下检索到的上下文信息，回答用户的问题。

用户问题：{user_question}

检索到的上下文：
{context}

要求：
1. 请基于上下文详细回答，不要添加上下文中没有的信息
2. 使用Markdown格式组织答案
3. 尽可能引用上下文的图片和表格内容

请回答："""

    response = llm.invoke([{"role": "user", "content": answer_prompt}])

    return {"messages": [response]}

# 路由决策函数
def route_query(state: MessagesState) -> str:
    """根据路由结果决定使用哪个检索器"""
    route_result = state["messages"][-1].content
    if "产品" in route_result:
        return "elasticsearch"
    else:
        return "faiss"

# 创建状态图
workflow = StateGraph(MessagesState)

# 添加所有节点
workflow.add_node("relevance_check", relevance_check)  # 相关性判断节点
workflow.add_node("rewrite", rewrite_node)  # 改写节点
workflow.add_node("query_router", query_router_node)  # 路由节点
workflow.add_node("retriever_faiss", retriever_faiss)  # Faiss检索节点（公司信息）
workflow.add_node("retriever_elasticsearch", retriever_elasticsearch)  # ES检索节点（产品信息）
workflow.add_node("generate_answer", generate_answer)  # 生成答案（不相关问题）
workflow.add_node("generate_answer_with_retriever", generate_answer_with_retriever)  # 生成答案（检索后）

# 添加边
workflow.add_edge(START, "relevance_check")  # 开始 -> 相关性判断

# 相关性判断后的条件边
workflow.add_conditional_edges(
    "relevance_check",
    lambda x: "不相关" in x["messages"][-1].content,
    {
        False: "rewrite",  # 相关 -> 改写
        True: "generate_answer"  # 不相关 -> 直接生成答案
    }
)

workflow.add_edge("rewrite", "query_router")  # 改写 -> 路由

# 路由后的条件边：根据查询类型选择不同的检索器
workflow.add_conditional_edges(
    "query_router",
    route_query,
    {
        "elasticsearch": "retriever_elasticsearch",  # 产品查询 -> ES检索
        "faiss": "retriever_faiss"  # 公司查询 -> Faiss检索
    }
)

# 两个检索器都连接到答案生成节点
workflow.add_edge("retriever_faiss", "generate_answer_with_retriever")  # Faiss检索 -> 生成答案
workflow.add_edge("retriever_elasticsearch", "generate_answer_with_retriever")  # ES检索 -> 生成答案

# 结束边
workflow.add_edge("generate_answer", END)  # 直接生成答案 -> 结束
workflow.add_edge("generate_answer_with_retriever", END)  # 检索后生成答案 -> 结束


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
print(searcher)
app = workflow.compile()

if __name__ == "__main__":
    # 测试公司信息查询（应该路由到 Faiss）
    # print("\n" + "="*100)
    # print("测试1：公司信息查询（应该使用 Faiss 检索）")
    # print("="*100)
    # ask_question("小米集团在2024年的碳排放目标是什么？")
    #
    # # 测试产品信息查询（应该路由到 Elasticsearch）
    # print("\n" + "="*100)
    # print("测试2：产品信息查询（应该使用 Elasticsearch 检索）")
    # print("="*100)
    ask_question("小米15的价格多少？")
    
    # 测试不相关查询
    # print("\n" + "="*100)
    # print("测试3：不相关查询")
    # print("="*100)
    # ask_question("帮我写一首押韵的古诗：苍天饶过谁？")

