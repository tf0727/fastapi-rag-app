# Retriever6 - 智能路由 RAG 系统

> 一个基于 LangGraph 的智能检索增强生成系统，支持自动路由到 Elasticsearch（产品信息）或 Faiss（公司信息）数据库

## 📚 目录

- [概述](#概述)
- [主要特性](#主要特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [详细文档](#详细文档)
- [使用示例](#使用示例)
- [配置说明](#配置说明)
- [开发指南](#开发指南)

## 概述

Retriever6 是一个智能的 RAG（检索增强生成）系统，它能够：

1. **自动判断查询类型**：区分产品查询和公司信息查询
2. **智能路由**：根据查询类型自动选择合适的数据库
3. **双数据库支持**：
   - **Elasticsearch**：用于产品参数、规格、价格等结构化信息
   - **Faiss**：用于公司发展、ESG报告等非结构化文档

## 主要特性

### ✨ 核心功能

- 🎯 **智能相关性判断**：自动识别问题是否与小米相关
- 📝 **问题改写**：将疑问句改写为陈述句，提高检索准确度
- 🔀 **自动路由**：基于 LLM 的查询类型分类
- 🔍 **双数据库检索**：支持 Elasticsearch 和 Faiss
- 💬 **上下文生成**：基于检索结果生成高质量答案

### 🚀 技术栈

- **LangGraph**: 工作流编排
- **LangChain**: LLM 工具链
- **Elasticsearch**: 结构化数据检索
- **Faiss**: 向量数据库检索
- **通义千问 (qwen-plus)**: LLM 模型
- **BGE-base-zh-v1.5**: Embedding 模型

## 系统架构

```
┌─────────────┐
│  用户查询    │
└──────┬──────┘
       ↓
┌──────────────────┐
│ 相关性判断        │ ← 是否与小米相关？
└────┬────────┬────┘
     ↓        ↓
   相关    不相关
     ↓        ↓
┌─────────┐  ┌─────────────┐
│ 问题改写 │  │ 直接生成答案 │
└────┬────┘  └──────┬──────┘
     ↓              ↓
┌─────────────┐   END
│ 查询路由     │
└────┬────────┘
     ↓
  产品 or 公司？
     ↓
┌────┴────────────────┐
↓                     ↓
┌──────────────┐  ┌──────────┐
│ Elasticsearch│  │  Faiss   │
│  产品信息     │  │ 公司信息  │
└──────┬───────┘  └────┬─────┘
       └───────┬────────┘
               ↓
       ┌──────────────┐
       │ 生成最终答案  │
       └──────┬───────┘
              ↓
            END
```

## 快速开始

### 1. 前提条件

```bash
# 确保 Python 3.8+ 已安装
python --version

# 确保 Elasticsearch 正在运行
curl http://localhost:9200
```

### 2. 安装依赖

```bash
pip install langchain langchain-openai langchain-community
pip install faiss-cpu sentence-transformers
pip install elasticsearch python-dotenv
```

### 3. 配置环境

```bash
# 设置环境变量（可选，也可以直接在代码中设置）
export OPENAI_API_KEY="your-api-key"
```

### 4. 运行示例

```bash
cd E:\shoushixiaomi\demo\rag-xiaomi
python src/agent/retriever6.py
```

### 5. 预期输出

```
测试1：公司信息查询（应该使用 Faiss 检索）
================================================================================
问题: 小米集团在2024年的碳排放目标是什么？
================================================================================

最终答案:
根据小米集团2024年环境、社会及管治报告，小米集团在2024年的碳排放目标包括...

================================================================================
测试2：产品信息查询（应该使用 Elasticsearch 检索）
================================================================================
问题: 小米14 Pro的处理器是什么？
================================================================================

最终答案:
根据产品信息，小米14 Pro搭载了骁龙8 Gen 3处理器...
```

## 详细文档

本项目包含以下详细文档：

1. **[工作流程说明](./RETRIEVER6_WORKFLOW.md)**
   - 节点详解
   - 工作流程图
   - 路由逻辑
   - 使用示例

2. **[系统架构图](./ARCHITECTURE_DIAGRAM.md)**
   - 整体架构
   - 数据流详解
   - 消息流结构
   - 性能优化建议

3. **[修改总结](./CHANGES_SUMMARY.md)**
   - 修改内容
   - 代码对比
   - 兼容性说明
   - 后续优化建议

4. **[快速使用指南](./QUICK_START.md)**
   - 使用示例
   - 常见问题
   - 调试技巧
   - 性能优化

## 使用示例

### 基本用法

```python
from src.agent.retriever6 import ask_question

# 查询产品信息（自动路由到 Elasticsearch）
ask_question("小米14 Pro的屏幕尺寸是多少？")

# 查询公司信息（自动路由到 Faiss）
ask_question("小米集团的ESG目标是什么？")

# 不相关查询（直接回答）
ask_question("今天天气怎么样？")
```

### 自定义检索参数

```python
# 修改 Elasticsearch 检索参数
results = searcher.multi_embedding_search(
    query_text="小米14",
    field_weights={
        "商品名称_embedding": 3.0,    # 增加商品名称权重
        "简介_embedding": 2.0,
        "类别_embedding": 1.0,
        "详细参数_embedding": 2.0
    },
    size=10,           # 返回10个结果
    min_score=0.5      # 提高最低分数阈值
)
```

### 批量查询

```python
questions = [
    "小米14 Pro的价格是多少？",
    "小米手环8有哪些功能？",
    "小米的环保政策是什么？"
]

for q in questions:
    ask_question(q)
```

## 配置说明

### LLM 配置

```python
llm = ChatOpenAI(
    model="qwen-plus",                    # 模型名称
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key="your-api-key",               # API密钥
    temperature=0                          # 温度（0=确定性输出）
)
```

### Embedding 配置

```python
embeddings = HuggingFaceEmbeddings(
    model_name="E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5",
    model_kwargs={'device': 'cpu'}        # 使用 CPU（可改为 'cuda'）
)
```

### Elasticsearch 配置

```python
searcher = XiaomiProductSearch(
    model_path='../bge-base-zh-v1.5',
    host="http://localhost:9200",
    index_name="xiaomi_products"
)
```

### Faiss 配置

```python
VS_PATH = "E:/shoushixiaomi/demo/rag-xiaomi/faiss-pkl"
vector_store = FAISS.load_local(
    folder_path=VS_PATH,
    embeddings=embeddings,
    allow_dangerous_deserialization=True
)
```

## 开发指南

### 项目结构

```
src/agent/
├── retriever6.py              # 主程序
├── README_RETRIEVER6.md       # 本文件
├── RETRIEVER6_WORKFLOW.md     # 工作流程说明
├── ARCHITECTURE_DIAGRAM.md    # 架构图
├── CHANGES_SUMMARY.md         # 修改总结
└── QUICK_START.md             # 快速开始指南
```

### 工作流节点说明

| 节点名称 | 功能 | 输入 | 输出 |
|---------|------|------|------|
| `relevance_check` | 判断问题相关性 | 用户问题 | "是" / "不相关" |
| `rewrite` | 问题改写 | 用户问题 | 改写后的陈述句 |
| `query_router` | 查询路由 | 改写后的问题 | "产品" / "公司" |
| `retriever_elasticsearch` | ES检索 | 查询文本 | 产品信息 |
| `retriever_faiss` | Faiss检索 | 查询文本 | 文档内容 |
| `generate_answer` | 生成答案 | 用户问题 | 答案文本 |
| `generate_answer_with_retriever` | 基于检索生成 | 问题+上下文 | 答案文本 |

### 添加新的数据源

如果你想添加第三个数据源（例如技术文档库），可以按照以下步骤：

1. **创建新的检索工具**

```python
@tool
def tech_doc_retriever_tool(query: str) -> str:
    """搜索技术文档"""
    # 实现检索逻辑
    pass
```

2. **创建新的检索节点**

```python
def retriever_tech_doc(state: MessagesState):
    """技术文档检索节点"""
    rewritten_question = state["messages"][-2].content
    ans = tech_doc_retriever_tool.invoke(rewritten_question)
    return {"messages": [ToolMessage(content=ans, tool_call_id="tech_doc_retriever")]}
```

3. **修改路由工具**

```python
@tool
def query_router_tool(question: str) -> str:
    """判断查询类型"""
    router_prompt = f"""...
    类别1 - 产品信息
    类别2 - 公司信息
    类别3 - 技术文档  # 新增
    ...
    """
    # 返回: "产品" / "公司" / "技术文档"
```

4. **更新路由决策函数**

```python
def route_query(state: MessagesState) -> str:
    route_result = state["messages"][-1].content
    if "产品" in route_result:
        return "elasticsearch"
    elif "技术文档" in route_result:
        return "tech_doc"
    else:
        return "faiss"
```

5. **添加工作流节点和边**

```python
workflow.add_node("retriever_tech_doc", retriever_tech_doc)

workflow.add_conditional_edges(
    "query_router",
    route_query,
    {
        "elasticsearch": "retriever_elasticsearch",
        "faiss": "retriever_faiss",
        "tech_doc": "retriever_tech_doc"  # 新增
    }
)

workflow.add_edge("retriever_tech_doc", "generate_answer_with_retriever")
```

### 调试技巧

#### 1. 查看完整消息流

```python
result = app.invoke({"messages": [HumanMessage(content=question)]})
for i, msg in enumerate(result["messages"]):
    print(f"[{i}] {type(msg).__name__}: {msg.content[:100]}")
```

#### 2. 添加节点日志

```python
def query_router_node(state: MessagesState):
    rewritten_question = state["messages"][-1].content
    print(f"[路由] 输入问题: {rewritten_question}")
    
    route_result = query_router_tool.invoke(rewritten_question)
    print(f"[路由] 路由结果: {route_result}")
    
    return {"messages": [ToolMessage(content=route_result, tool_call_id="query_router_tool")]}
```

#### 3. 可视化工作流

```python
from IPython.display import Image, display

# 生成工作流图
display(Image(app.get_graph().draw_mermaid_png()))
```

## 常见问题

### Q: 路由不准确怎么办？

**A:** 可以通过以下方式优化：
1. 调整路由提示词，增加更多示例
2. 使用更强大的 LLM 模型
3. 添加关键词规则作为辅助判断
4. 收集错误案例，优化提示词

### Q: 如何提高检索质量？

**A:** 可以尝试：
1. 调整 Elasticsearch 字段权重
2. 增加检索结果数量（k值）
3. 使用更好的 Embedding 模型
4. 添加重排序（reranking）步骤
5. 优化数据质量

### Q: 响应速度慢怎么办？

**A:** 优化建议：
1. 使用 GPU 加速 Embedding
2. 添加结果缓存
3. 减少检索结果数量
4. 使用更快的 LLM 模型
5. 考虑异步处理

## 性能指标

| 指标 | 说明 | 目标值 |
|------|------|--------|
| 路由准确率 | 正确路由到目标数据库的比例 | > 95% |
| 检索召回率 | 检索结果包含答案的比例 | > 90% |
| 平均响应时间 | 从查询到答案的总时间 | < 3秒 |
| 用户满意度 | 答案质量评分 | > 4.0/5.0 |

## 更新日志

### v1.0 (2025-11-04)
- ✨ 实现智能路由功能
- ✨ 支持 Elasticsearch 和 Faiss 双数据库
- ✨ 添加问题改写和相关性判断
- 📝 完善文档和使用指南

## 贡献指南

欢迎贡献！如果你有改进建议：
1. Fork 本仓库
2. 创建特性分支
3. 提交改进
4. 发起 Pull Request

## 许可证

本项目遵循 MIT 许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 📧 Email: your-email@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)

---

**Happy Coding! 🚀**



