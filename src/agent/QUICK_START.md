# Retriever6 快速使用指南

## 📋 前提条件

### 1. 环境要求
- Python 3.8+
- Elasticsearch 服务运行中 (localhost:9200)
- 足够的内存用于加载 Embedding 模型

### 2. 必需的文件和服务
```
✅ Faiss 向量数据库: E:/shoushixiaomi/demo/rag-xiaomi/faiss-pkl/
✅ Embedding 模型: E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5/
✅ Elasticsearch 索引: xiaomi_products
✅ API Key: 通义千问 API Key
```

### 3. 依赖包
```bash
pip install langchain langchain-openai langchain-community
pip install faiss-cpu sentence-transformers
pip install elasticsearch python-dotenv
```

## 🚀 快速开始

### 步骤1：检查 Elasticsearch 服务

```bash
# Windows PowerShell
curl http://localhost:9200

# 预期输出：
# {
#   "name" : "...",
#   "cluster_name" : "elasticsearch",
#   ...
# }
```

### 步骤2：验证索引存在

```bash
curl http://localhost:9200/xiaomi_products/_count
```

### 步骤3：运行程序

```bash
cd E:\shoushixiaomi\demo\rag-xiaomi
python src/agent/retriever6.py
```

## 💡 使用示例

### 示例1：查询产品信息

```python
from src.agent.retriever6 import ask_question

# 产品参数查询
ask_question("小米14 Pro的屏幕尺寸是多少？")
ask_question("小米手环8有哪些颜色？")
ask_question("小米平板6的电池容量是多少？")
```

**预期流程**:
```
问题 → relevance_check → rewrite → query_router 
    → retriever_elasticsearch → generate_answer_with_retriever
```

**预期输出示例**:
```
问题: 小米14 Pro的屏幕尺寸是多少？
================================================================================

最终答案:
根据产品信息，小米14 Pro采用6.73英寸的AMOLED屏幕，支持3200×1440分辨率...
```

### 示例2：查询公司信息

```python
# 公司发展查询
ask_question("小米集团在2024年的ESG目标是什么？")
ask_question("小米在环境保护方面有哪些举措？")
ask_question("小米的碳中和计划是怎样的？")
```

**预期流程**:
```
问题 → relevance_check → rewrite → query_router 
    → retriever_faiss → generate_answer_with_retriever
```

**预期输出示例**:
```
问题: 小米集团在2024年的ESG目标是什么？
================================================================================

最终答案:
根据小米集团2024年环境、社会及管治报告，小米集团在2024年的ESG目标包括：

1. **环境方面**：
   - 实现碳达峰目标
   - 推进可再生能源使用...

2. **社会方面**：
   - 员工福利提升...
```

### 示例3：不相关查询

```python
# 不相关查询
ask_question("今天天气怎么样？")
ask_question("帮我写一首诗")
```

**预期流程**:
```
问题 → relevance_check → generate_answer
```

## 🔧 自定义配置

### 修改检索参数

```python
# Elasticsearch 检索配置
results = searcher.multi_embedding_search(
    query, 
    size=5,           # 修改返回数量
    min_score=0.3     # 修改最小相似度阈值
)

# Faiss 检索配置
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}  # 修改返回数量
)
```

### 修改字段权重

```python
# 在 elasticsearch_retriever_tool 中
field_weights = {
    "商品名称_embedding": 2.5,    # 可以调整权重
    "简介_embedding": 2.0,
    "类别_embedding": 1.0,
    "详细参数_embedding": 1.5
}
```

### 修改路由提示词

```python
# 在 query_router_tool 中调整分类规则
router_prompt = f"""你是一个查询分类专家...
类别1 - 产品信息：...
类别2 - 公司信息：...
"""
```

## 🐛 常见问题

### Q1: Elasticsearch 连接失败

**错误信息**: 
```
ConnectionError: [Errno 10061] No connection could be made...
```

**解决方案**:
1. 确认 Elasticsearch 服务正在运行
2. 检查端口是否为 9200
3. 尝试重启 Elasticsearch 服务

### Q2: 模型加载失败

**错误信息**:
```
OSError: [Errno 2] No such file or directory: 'E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5'
```

**解决方案**:
1. 确认模型路径正确
2. 下载 bge-base-zh-v1.5 模型到指定路径
3. 修改代码中的 `model_name` 路径

### Q3: Faiss 索引加载失败

**错误信息**:
```
RuntimeError: Error in faiss::FileIOReader::FileIOReader...
```

**解决方案**:
1. 确认 `faiss-pkl/` 目录存在
2. 确认包含 `index.faiss` 和 `index.pkl` 文件
3. 重新构建 Faiss 索引

### Q4: API Key 无效

**错误信息**:
```
AuthenticationError: Invalid API key
```

**解决方案**:
1. 检查 `.env` 文件中的 API Key
2. 或修改代码中的 `api_key` 变量
3. 确认 API Key 有效且未过期

### Q5: 路由不准确

**现象**: 产品查询被路由到 Faiss，或反之

**解决方案**:
1. 检查路由提示词是否清晰
2. 增加示例来提升分类准确性
3. 调整 LLM 的 temperature（当前为0）
4. 添加日志查看路由决策过程

## 📊 调试技巧

### 1. 添加调试日志

```python
def query_router_node(state: MessagesState):
    """路由节点：判断查询类型"""
    rewritten_question = state["messages"][-1].content
    route_result = query_router_tool.invoke(rewritten_question)
    
    # 添加调试输出
    print(f"[DEBUG] 改写后问题: {rewritten_question}")
    print(f"[DEBUG] 路由结果: {route_result}")
    
    return {"messages": [ToolMessage(content=route_result, tool_call_id="query_router_tool")]}
```

### 2. 查看消息流

```python
def ask_question(question: str):
    result = app.invoke({"messages": [HumanMessage(content=question)]})
    
    # 打印所有消息
    print("\n[DEBUG] 消息流:")
    for i, msg in enumerate(result["messages"]):
        print(f"  [{i}] {type(msg).__name__}: {msg.content[:100]}...")
    
    final_answer = result["messages"][-1].content
    print(final_answer)
```

### 3. 检查检索结果

```python
def retriever_elasticsearch(state: MessagesState):
    rewritten_question = state["messages"][-2].content
    ans = elasticsearch_retriever_tool.invoke(rewritten_question)
    
    # 添加调试输出
    print(f"[DEBUG] ES检索结果长度: {len(ans)}")
    print(f"[DEBUG] ES检索结果预览: {ans[:200]}...")
    
    return {"messages": [ToolMessage(content=ans, tool_call_id="elasticsearch_retriever_tool")]}
```

## 🎯 性能优化建议

### 1. 使用 GPU 加速（如果可用）

```python
embeddings = HuggingFaceEmbeddings(
    model_name="E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5",
    model_kwargs={'device': 'cuda'}  # 改为 cuda
)

# Elasticsearch searcher 也可以使用 GPU
searcher = XiaomiProductSearch(
    model_path='../bge-base-zh-v1.5',
    device='cuda'
)
```

### 2. 批量查询

```python
def batch_ask_questions(questions: list):
    """批量处理多个问题"""
    results = []
    for q in questions:
        result = app.invoke({"messages": [HumanMessage(content=q)]})
        results.append(result["messages"][-1].content)
    return results
```

### 3. 添加缓存

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_retriever(query: str, db_type: str):
    """缓存检索结果"""
    if db_type == "elasticsearch":
        return elasticsearch_retriever_tool.invoke(query)
    else:
        return faiss_retriever_tool.invoke(query)
```

## 📈 监控和评估

### 1. 统计路由分布

```python
from collections import Counter

route_stats = Counter()

def query_router_node_with_stats(state: MessagesState):
    rewritten_question = state["messages"][-1].content
    route_result = query_router_tool.invoke(rewritten_question)
    
    # 统计路由结果
    if "产品" in route_result:
        route_stats["elasticsearch"] += 1
    else:
        route_stats["faiss"] += 1
    
    print(f"路由统计: {dict(route_stats)}")
    
    return {"messages": [ToolMessage(content=route_result, tool_call_id="query_router_tool")]}
```

### 2. 测试集评估

```python
# 创建测试集
test_cases = [
    ("小米14 Pro的价格是多少？", "elasticsearch"),
    ("小米的碳排放目标是什么？", "faiss"),
    ("小米手环8的功能有哪些？", "elasticsearch"),
    ("小米集团的ESG报告在哪里？", "faiss"),
]

# 运行评估
correct = 0
for question, expected_route in test_cases:
    # 运行查询并检查路由
    result = app.invoke({"messages": [HumanMessage(content=question)]})
    # 检查路由是否正确
    # ...
    if actual_route == expected_route:
        correct += 1

accuracy = correct / len(test_cases)
print(f"路由准确率: {accuracy:.2%}")
```

## 🔗 相关文档

- [工作流程说明](./RETRIEVER6_WORKFLOW.md)
- [架构图](./ARCHITECTURE_DIAGRAM.md)
- [修改总结](./CHANGES_SUMMARY.md)

## 🆘 获取帮助

如果遇到问题：
1. 查看上述常见问题部分
2. 启用调试日志查看详细信息
3. 检查 Elasticsearch 和模型服务状态
4. 确认所有依赖正确安装



