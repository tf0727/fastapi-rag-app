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

# 创建问题补全工具
@tool
def query_completion_tool(current_question: str, history: str) -> str:
    """根据对话历史补全当前问题的主谓宾，处理指代词和省略的情况"""
    completion_prompt = f"""你是一个问题补全专家，需要根据对话历史补全用户当前问题中缺失或模糊的主谓宾成分。

任务说明：
1. 分析用户当前问题，识别是否存在指代词（如"它"、"这个"、"那个"等）或省略主语的情况
2. 结合对话历史，将指代词替换为具体的实体，补全省略的主语
3. 如果问题已经完整，直接返回原问题
4. 只返回补全后的问题，不要添加任何解释

样例：
```
对话历史：
- 用户：小米15的价格多少？
- AI：小米15的价格为4499元起...

当前问题：它有哪些颜色？
补全后：小米15有哪些颜色？

---

对话历史：
- 用户：小米SU7怎么样？
- AI：小米SU7是一款智能电动汽车...
- 用户：配置如何？
- AI：小米SU7提供多种配置...

当前问题：价格呢？
补全后：小米SU7的价格是多少？

---

对话历史：
（无历史或不相关）

当前问题：小米手环多少钱？
补全后：小米手环多少钱？
```

对话历史：
{history}

当前问题：{current_question}

补全后："""
    response = llm.invoke([{"role": "user", "content": completion_prompt}])
    return response.content.strip()

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

# 问题补全节点
def query_completion_node(state: MessagesState):
    """根据对话历史补全当前问题的主谓宾"""
    # 获取当前用户问题
    current_question = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "human":
            current_question = msg.content
            break
    
    current_question = extract_text_content(current_question)
    
    # 构建对话历史字符串
    history_text = ""
    human_messages = []
    ai_messages = []
    
    # 收集历史对话（不包括当前问题）
    for msg in state["messages"]:
        if hasattr(msg, 'type'):
            if msg.type == "human":
                human_messages.append(extract_text_content(msg.content))
            elif msg.type == "ai":
                ai_messages.append(extract_text_content(msg.content))
    
    # 如果有历史对话（至少有一轮完整对话）
    if len(human_messages) > 1 and len(ai_messages) >= 1:
        # 构建历史文本（最近3轮对话）
        recent_pairs = min(3, len(human_messages) - 1)  # -1 因为最后一个是当前问题
        for i in range(max(0, len(human_messages) - recent_pairs - 1), len(human_messages) - 1):
            if i < len(human_messages) and i < len(ai_messages):
                history_text += f"- 用户：{human_messages[i]}\n"
                history_text += f"- AI：{ai_messages[i][:200]}...\n\n"  # 截取前200字符
    else:
        history_text = "（无历史对话）"
    
    # 调用补全工具
    completed_question = query_completion_tool.invoke({
        "current_question": current_question,
        "history": history_text
    })
    
    return {"messages": [ToolMessage(content=completed_question, tool_call_id="query_completion_tool")]}

# Faiss 检索节点（公司信息）
def retriever_faiss(state: MessagesState):
    """调用 Faiss 检索工具并返回ToolMessage（用于公司发展信息）"""
    # 从后往前查找改写后的问题（tool_call_id 为 "rewrite_tool" 的消息）
    rewritten_question = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id') and msg.tool_call_id == "rewrite_tool":
            rewritten_question = msg.content
            break
    
    if not rewritten_question:
        # 如果没找到改写后的问题，使用最近的用户问题
        for msg in reversed(state["messages"]):
            if hasattr(msg, 'type') and msg.type == "human":
                rewritten_question = extract_text_content(msg.content)
                break
    
    ans = faiss_retriever_tool.invoke(rewritten_question)
    return {"messages": [ToolMessage(content=ans, tool_call_id="faiss_retriever_tool")]}

# Elasticsearch 检索节点（产品信息）
def retriever_elasticsearch(state: MessagesState):
    """调用 Elasticsearch 检索工具并返回ToolMessage（用于产品信息）"""
    # 从后往前查找改写后的问题（tool_call_id 为 "rewrite_tool" 的消息）
    rewritten_question = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id') and msg.tool_call_id == "rewrite_tool":
            rewritten_question = msg.content
            break
    
    if not rewritten_question:
        # 如果没找到改写后的问题，使用最近的用户问题
        for msg in reversed(state["messages"]):
            if hasattr(msg, 'type') and msg.type == "human":
                rewritten_question = extract_text_content(msg.content)
                break
    
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
    
    # 优先使用补全后的问题（如果存在）
    completed_question = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id') and msg.tool_call_id == "query_completion_tool":
            completed_question = msg.content
            break
    
    # 如果没有补全后的问题，使用原始用户问题
    if not completed_question:
        for msg in reversed(state["messages"]):
            if hasattr(msg, 'type') and msg.type == "human":
                completed_question = extract_text_content(msg.content)
                break
    
    # 调用改写工具
    ans = rewrite_tool.invoke(completed_question)
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
    # 从后往前查找改写后的问题（tool_call_id 为 "rewrite_tool" 的消息）
    rewritten_question = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id') and msg.tool_call_id == "rewrite_tool":
            rewritten_question = msg.content
            break
    
    if not rewritten_question:
        # 如果没找到改写后的问题，使用最近的用户问题
        for msg in reversed(state["messages"]):
            if hasattr(msg, 'type') and msg.type == "human":
                rewritten_question = extract_text_content(msg.content)
                break
    
    route_result = query_router_tool.invoke(rewritten_question)
    # 将路由结果添加到消息中
    return {"messages": [ToolMessage(content=route_result, tool_call_id="query_router_tool")]}



def generate_answer_with_retriever(state: MessagesState):
    """
    生成最终答案节点

    这个节点会基于检索到的上下文生成最终答案
    """
    # 获取用户的原始问题（最近的 HumanMessage）
    user_question = None
    for msg in reversed(state["messages"]):
        if hasattr(msg, 'type') and msg.type == "human":
            user_question = msg.content
            break

    user_question = extract_text_content(user_question)

    # 获取检索到的上下文（查找最近的检索工具消息）
    context = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id'):
            if msg.tool_call_id in ["faiss_retriever_tool", "elasticsearch_retriever_tool"]:
                context = msg.content
                break
    
    if not context:
        # 如果没有找到检索结果，使用默认消息
        context = "未找到相关信息"

    # 获取对话历史（用于提供上下文）
    history_context = ""
    ai_messages = []
    human_messages = []
    
    # 收集历史对话（跳过当前问题和工具消息）
    for msg in state["messages"][:-1]:  # 不包括最新的检索结果
        if hasattr(msg, 'type'):
            if msg.type == "human":
                human_messages.append(extract_text_content(msg.content))
            elif msg.type == "ai":
                ai_messages.append(extract_text_content(msg.content))
    
    # 如果有历史对话，构建历史上下文
    if len(human_messages) > 1:  # 有之前的对话（不只是当前问题）
        history_context = "\n\n历史对话：\n"
        # 只取最近的几轮对话（避免上下文过长）
        recent_pairs = min(3, len(human_messages) - 1)  # -1 因为最后一个是当前问题
        for i in range(max(0, len(human_messages) - recent_pairs - 1), len(human_messages) - 1):
            if i < len(human_messages) and i < len(ai_messages):
                history_context += f"- 用户: {human_messages[i][:100]}...\n"
                history_context += f"- AI: {ai_messages[i][:100]}...\n"

    # 构建答案生成的提示词
    answer_prompt = f"""基于以下检索到的上下文信息，回答用户的问题。
{history_context}
当前用户问题：{user_question}

检索到的上下文：
{context}

要求：
1. 请基于上下文详细回答，不要添加上下文中没有的信息
2. 如果用户的问题涉及之前的对话内容（如"它"、"这个"等指代词），请结合历史对话理解用户意图
3. 使用Markdown格式组织答案
4. 尽可能引用上下文的图片和表格内容

请回答："""

    response = llm.invoke([{"role": "user", "content": answer_prompt}])

    return {"messages": [response]}

# 路由决策函数
def route_query(state: MessagesState) -> str:
    """根据路由结果决定使用哪个检索器"""
    # 从后往前查找路由结果（tool_call_id 为 "query_router_tool" 的消息）
    route_result = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and hasattr(msg, 'tool_call_id') and msg.tool_call_id == "query_router_tool":
            route_result = msg.content
            break
    
    if not route_result:
        # 如果没有找到路由结果，默认使用 faiss
        return "faiss"
    
    if "产品" in route_result:
        return "elasticsearch"
    else:
        return "faiss"

# 创建状态图
workflow = StateGraph(MessagesState)

# 添加所有节点
workflow.add_node("relevance_check", relevance_check)  # 相关性判断节点
workflow.add_node("query_completion", query_completion_node)  # 问题补全节点（新增）
workflow.add_node("rewrite", rewrite_node)  # 改写节点
workflow.add_node("query_router", query_router_node)  # 路由节点
workflow.add_node("retriever_faiss", retriever_faiss)  # Faiss检索节点（公司信息）
workflow.add_node("retriever_elasticsearch", retriever_elasticsearch)  # ES检索节点（产品信息）
workflow.add_node("generate_answer", generate_answer)  # 生成答案（不相关问题）
workflow.add_node("generate_answer_with_retriever", generate_answer_with_retriever)  # 生成答案（检索后）

# 添加边
workflow.add_edge(START, "query_completion")
workflow.add_edge("query_completion", "relevance_check")  # 问题补全 -> 改写（新增）

# 相关性判断后的条件边
workflow.add_conditional_edges(
    "relevance_check",
    lambda x: "不相关" in x["messages"][-1].content,
    {
        False: "rewrite",  # 相关 -> 问题补全（修改）
        True: "generate_answer"  # 不相关 -> 直接生成答案
    }
)

# workflow.add_edge("query_completion", "rewrite")  # 问题补全 -> 改写（新增）
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


class ConversationManager:
    """对话管理器：维护多轮对话的历史上下文"""
    def __init__(self, verbose=False):
        self.history = []  # 存储对话历史
        self.verbose = verbose  # 是否显示详细的中间步骤
    
    def ask_question(self, question: str):
        """
        处理用户问题并维护对话历史
        
        Args:
            question: 用户输入的问题
            
        Returns:
            str: AI的回复
        """
        print(f"\n{'=' * 80}")
        print(f"🙋 用户问题: {question}")
        print(f"{'=' * 80}\n")
        
        # 将用户问题添加到历史中
        self.history.append(HumanMessage(content=question))
        
        # 调用 Agent，传入完整的历史消息
        result = app.invoke({"messages": self.history})
        
        # 如果开启详细模式，显示中间步骤
        if self.verbose:
            print(f"\n{'─' * 80}")
            print("📋 中间步骤:")
            print(f"{'─' * 80}")
            for msg in result["messages"]:
                if isinstance(msg, ToolMessage):
                    tool_name = msg.tool_call_id if hasattr(msg, 'tool_call_id') else "unknown"
                    if tool_name == "query_completion_tool":
                        print(f"  ✏️  [问题补全] {msg.content[:150]}...")
                    elif tool_name == "rewrite_tool":
                        print(f"  🔄 [问题改写] {msg.content[:150]}...")
                    elif tool_name == "query_router_tool":
                        print(f"  🧭 [路由决策] {msg.content}")
                    elif tool_name in ["faiss_retriever_tool", "elasticsearch_retriever_tool"]:
                        retriever_type = "Faiss" if "faiss" in tool_name else "Elasticsearch"
                        print(f"  🔍 [检索-{retriever_type}] 检索到 {len(msg.content)} 字符的内容")
            print(f"{'─' * 80}\n")
        
        # 获取最终答案
        final_answer = result["messages"][-1]
        
        # 将 AI 的回答添加到历史中（只添加最终的 AI 回复，不添加中间的工具消息）
        if isinstance(final_answer, AIMessage):
            self.history.append(final_answer)
        
        print("🤖 最终答案:")
        print(final_answer.content)
        
        return final_answer.content
    
    def clear_history(self):
        """清空对话历史"""
        self.history = []
        print("对话历史已清空")
    
    def show_history(self):
        """显示对话历史"""
        print(f"\n{'=' * 80}")
        print("对话历史:")
        print(f"{'=' * 80}")
        for i, msg in enumerate(self.history):
            role = "用户" if isinstance(msg, HumanMessage) else "AI"
            content = extract_text_content(msg.content)
            print(f"\n{i+1}. [{role}]: {content[:100]}...")
        print(f"{'=' * 80}\n")


def ask_question(question: str):
    """
    简单的单轮问答函数（不维护历史）
    
    Args:
        question: 用户输入的问题
    """
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
    # 创建对话管理器实例（开启 verbose 模式以查看问题补全效果）
    conversation = ConversationManager(verbose=True)
    
    # ============================================================
    # 方式1：多轮对话示例（维护上下文 + 展示问题补全）
    # ============================================================
    print("\n" + "="*100)
    print("🎯 演示：多轮对话（带上下文） - 可以看到问题补全的效果")
    print("="*100)
    print("\n💡 注意观察：")
    print("   - 第2、3轮中使用了指代词（'它'）和省略主语（'内存配置'）")
    print("   - 系统会自动根据历史补全完整的主谓宾")
    print("   - 在【中间步骤】中可以看到补全结果")
    
    # 第一轮：询问产品价格
    conversation.ask_question("小米15的价格多少？")
    
    # 第二轮：追问（使用指代词"它"）
    conversation.ask_question("它有哪些颜色可选？")
    
    # 第三轮：继续追问（省略主语）
    conversation.ask_question("内存配置有哪些？")
    
    # 查看对话历史
    conversation.show_history()
    
    # 清空历史，开始新的对话
    print("\n" + "="*100)
    print("🔄 切换话题：从产品咨询切换到公司信息")
    print("="*100)
    conversation.clear_history()
    
    # 第四轮：询问公司信息
    conversation.ask_question("小米集团在2024年的碳排放目标是什么？")
    
    # 第五轮：追问（省略主语）
    conversation.ask_question("具体采取了哪些措施？")
    
    # 第六轮：继续追问
    conversation.ask_question("效果如何？")
    
    # ============================================================
    # 方式2：单轮对话示例（不维护历史，每次独立）
    # ============================================================
    # print("\n" + "="*100)
    # print("演示：单轮对话（无上下文）")
    # print("="*100)
    # ask_question("小米15的价格多少？")
    
    # ============================================================
    # 方式3：交互式对话模式
    # ============================================================
    # print("\n" + "="*100)
    # print("交互式多轮对话模式（输入 'quit' 退出，'clear' 清空历史，'history' 查看历史）")
    # print("="*100)
    # 
    # conversation_interactive = ConversationManager()
    # while True:
    #     user_input = input("\n请输入问题: ").strip()
    #     
    #     if user_input.lower() == 'quit':
    #         print("退出对话")
    #         break
    #     elif user_input.lower() == 'clear':
    #         conversation_interactive.clear_history()
    #         continue
    #     elif user_input.lower() == 'history':
    #         conversation_interactive.show_history()
    #         continue
    #     elif not user_input:
    #         print("请输入有效的问题")
    #         continue
    #     
    #     conversation_interactive.ask_question(user_input)

