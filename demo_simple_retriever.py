"""
create_retriever_tool 简单示例

这是一个最简化的示例，展示 create_retriever_tool 的基本用法
"""

import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.tools import create_retriever_tool

load_dotenv(override=True)

# ==============================================================================
# 方式一：最基础的使用方法
# ==============================================================================

print("="*80)
print("方式一：直接调用 retriever_tool")
print("="*80 + "\n")

# 1. 初始化 Embedding
embeddings = HuggingFaceEmbeddings(
    model_name=os.getenv("EMBEDDING_MODEL", "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5"),
    model_kwargs={'device': 'cpu'}
)

# 2. 加载向量数据库
vector_store = FAISS.load_local(
    folder_path="./faiss-pkl",
    embeddings=embeddings,
    allow_dangerous_deserialization=True,
)

# 3. 创建检索器
retriever = vector_store.as_retriever(search_kwargs={"k": 3})

# 4. 创建检索工具
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="xiaomi_search",
    description="搜索小米ESG相关信息"
)

# 5. 直接调用工具（像函数一样）
query = "小米的环境战略"
result = retriever_tool.invoke(query)

print(f"查询: {query}")
print(f"\n检索结果:\n{result[:500]}...")  # 只显示前500个字符


# ==============================================================================
# 方式二：查看工具的详细信息
# ==============================================================================

print("\n" + "="*80)
print("方式二：查看工具属性")
print("="*80 + "\n")

print(f"工具名称: {retriever_tool.name}")
print(f"工具描述: {retriever_tool.description}")
print(f"工具类型: {type(retriever_tool)}")
print(f"是否是工具: {hasattr(retriever_tool, 'invoke')}")


# ==============================================================================
# 方式三：配置不同的检索参数
# ==============================================================================

print("\n" + "="*80)
print("方式三：不同的检索配置")
print("="*80 + "\n")

# 配置1: 返回更多结果
retriever_more = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 10}  # 返回前10个最相关的结果
)

tool_more = create_retriever_tool(
    retriever=retriever_more,
    name="detailed_search",
    description="详细搜索，返回更多结果"
)

# 配置2: 使用最大边际相关性（MMR）搜索
retriever_mmr = vector_store.as_retriever(
    search_type="mmr",  # Maximum Marginal Relevance
    search_kwargs={
        "k": 5,
        "fetch_k": 20,  # 先获取20个候选
        "lambda_mult": 0.5  # 多样性参数（0=最大多样性，1=最大相关性）
    }
)

tool_mmr = create_retriever_tool(
    retriever=retriever_mmr,
    name="diverse_search",
    description="多样性搜索，返回更多样化的结果"
)

# 配置3: 使用相似度阈值
retriever_threshold = vector_store.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={
        "score_threshold": 0.5,  # 只返回相似度>0.5的结果
        "k": 5
    }
)

tool_threshold = create_retriever_tool(
    retriever=retriever_threshold,
    name="threshold_search",
    description="阈值搜索，只返回高相关度的结果"
)

query = "碳中和"
print(f"查询: {query}\n")

print("1. 标准搜索（k=3）:")
result1 = retriever_tool.invoke(query)
print(f"   结果长度: {len(result1)} 字符\n")

print("2. 详细搜索（k=10）:")
result2 = tool_more.invoke(query)
print(f"   结果长度: {len(result2)} 字符\n")

print("3. MMR搜索（多样性）:")
result3 = tool_mmr.invoke(query)
print(f"   结果长度: {len(result3)} 字符\n")


# ==============================================================================
# 方式四：批量查询
# ==============================================================================

print("\n" + "="*80)
print("方式四：批量查询")
print("="*80 + "\n")

queries = [
    "小米的环境目标",
    "员工福利政策",
    "供应链管理"
]

for i, q in enumerate(queries, 1):
    result = retriever_tool.invoke(q)
    print(f"{i}. 查询: {q}")
    print(f"   结果预览: {result[:100]}...")
    print()


# ==============================================================================
# 方式五：与 LLM 结合使用
# ==============================================================================

print("\n" + "="*80)
print("方式五：与 LLM 结合使用")
print("="*80 + "\n")

from langchain_openai import ChatOpenAI
import os

os.environ["OPENAI_API_KEY"] = os.getenv("DASHSCOPE_API_KEY", "sk-f6fbb3799b8d4c698bcb3334effc474b")

llm = ChatOpenAI(
    model=os.getenv("CHAT_MODEL", "qwen-plus"),
    base_url=os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    temperature=0
)

# 将工具绑定到 LLM
llm_with_tools = llm.bind_tools([retriever_tool])

# 用户问题
question = "小米在2024年的碳排放目标是什么？"

# LLM 会自动决定是否调用工具
response = llm_with_tools.invoke([
    {"role": "user", "content": question}
])

print(f"问题: {question}\n")

# 检查是否有工具调用
if hasattr(response, 'tool_calls') and response.tool_calls:
    print("✓ LLM 决定调用检索工具")
    print(f"  工具名称: {response.tool_calls[0]['name']}")
    print(f"  查询参数: {response.tool_calls[0]['args']}")
    
    # 手动执行工具调用
    query_text = response.tool_calls[0]['args'].get('query', '')
    context = retriever_tool.invoke(query_text)
    
    print(f"\n检索到的上下文 ({len(context)} 字符):")
    print(context[:300] + "...\n")
    
    # 基于上下文生成最终答案
    final_response = llm.invoke([
        {"role": "user", "content": f"问题: {question}\n\n上下文: {context}\n\n请基于上下文回答问题。"}
    ])
    
    print("最终答案:")
    print(final_response.content)
else:
    print("✗ LLM 决定直接回答（未调用工具）")
    print(response.content)


print("\n" + "="*80)
print("Demo 运行完成！")
print("="*80)

