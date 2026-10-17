# Retriever6 修改总结

## 修改日期
2025年11月4日

## 修改目标
在 `rewrite` 节点后创建路由机制，根据用户查询类型自动选择合适的数据库进行检索：
- **Elasticsearch**: 产品参数和信息
- **Faiss**: 公司发展和业务信息

## 主要修改内容

### 1. 工具层修改

#### 1.1 重命名 Faiss 检索工具
```python
# 原来
retriever_tool = create_retriever_tool(...)

# 修改后
faiss_retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="xiaomi_company_knowledge_base",
    description="搜索小米公司发展、业务增长、ESG报告等企业信息。"
)
```

#### 1.2 新增 Elasticsearch 检索工具
```python
@tool
def elasticsearch_retriever_tool(query: str) -> str:
    """搜索小米产品参数和产品信息"""
    # 使用 searcher.multi_embedding_search 进行检索
    # 格式化返回产品信息
```

#### 1.3 新增查询路由工具
```python
@tool
def query_router_tool(question: str) -> str:
    """判断用户查询是关于产品信息还是公司发展信息"""
    # 使用 LLM 进行分类
    # 返回 "产品" 或 "公司"
```

### 2. 节点层修改

#### 2.1 原检索节点拆分为两个
```python
# 原来
def retriever(state: MessagesState):
    """单一检索节点"""

# 修改后
def retriever_faiss(state: MessagesState):
    """Faiss检索节点（公司信息）"""

def retriever_elasticsearch(state: MessagesState):
    """Elasticsearch检索节点（产品信息）"""
```

#### 2.2 新增路由节点
```python
def query_router_node(state: MessagesState):
    """路由节点：判断查询类型"""
    # 调用 query_router_tool 进行分类
```

#### 2.3 新增路由决策函数
```python
def route_query(state: MessagesState) -> str:
    """根据路由结果决定使用哪个检索器"""
    # 返回 "elasticsearch" 或 "faiss"
```

### 3. 工作流修改

#### 3.1 节点添加
```python
# 新增节点
workflow.add_node("query_router", query_router_node)
workflow.add_node("retriever_faiss", retriever_faiss)
workflow.add_node("retriever_elasticsearch", retriever_elasticsearch)
```

#### 3.2 边的修改
```python
# 原来
workflow.add_edge("rewrite", "retriever")

# 修改后
workflow.add_edge("rewrite", "query_router")  # 改写后先路由

# 新增条件边
workflow.add_conditional_edges(
    "query_router",
    route_query,
    {
        "elasticsearch": "retriever_elasticsearch",
        "faiss": "retriever_faiss"
    }
)
```

## 工作流对比

### 修改前
```
START → relevance_check → rewrite → retriever → generate_answer_with_retriever → END
                      ↓
                  generate_answer → END
```

### 修改后
```
START → relevance_check → rewrite → query_router ┬→ retriever_elasticsearch ┐
                      ↓                          └→ retriever_faiss          ├→ generate_answer_with_retriever → END
                  generate_answer → END                                      ┘
```

## 代码统计

### 新增代码
- 新增工具函数：2个（`elasticsearch_retriever_tool`, `query_router_tool`）
- 新增节点函数：2个（`query_router_node`, `route_query`）
- 修改节点函数：2个（拆分 `retriever` 为 `retriever_faiss` 和 `retriever_elasticsearch`）
- 新增工作流节点：3个
- 新增条件边：1个
- 总新增代码行数：约 80 行

### 修改代码
- 工具定义：1处
- 检索节点：1处改为2处
- 工作流边：2处
- 测试代码：1处

## 测试用例

### 测试1：公司信息查询
```python
ask_question("小米集团在2024年的碳排放目标是什么？")
```
**预期路由**: query_router → retriever_faiss

### 测试2：产品信息查询
```python
ask_question("小米14 Pro的处理器是什么？")
```
**预期路由**: query_router → retriever_elasticsearch

## 兼容性说明

### 向后兼容
- ✅ 保持了原有的消息流结构
- ✅ 保持了原有的状态定义（MessagesState）
- ✅ 保持了原有的 LLM 和 Embedding 配置

### 依赖要求
- ✅ 无新增依赖包
- ⚠️ 需要 Elasticsearch 服务运行在 localhost:9200
- ⚠️ 需要 `xiaomi_entity.query_xiaomi_products.searcher` 正确初始化

## 注意事项

1. **消息索引的正确性**: 
   - 在 `retriever_faiss` 和 `retriever_elasticsearch` 中，使用 `state["messages"][-2].content` 获取改写后的问题
   - 这是因为消息顺序为：[HumanMessage, ToolMessage(相关性), ToolMessage(改写), ToolMessage(路由)]

2. **Elasticsearch 服务**:
   - 确保 Elasticsearch 服务正在运行
   - 确保索引 `xiaomi_products` 已正确创建并包含数据

3. **路由准确性**:
   - 路由依赖 LLM 的分类能力
   - 可能需要根据实际使用情况调整路由提示词

## 后续优化建议

1. **增加日志**: 在路由节点添加日志，记录路由决策过程
2. **评估指标**: 添加路由准确率统计
3. **混合检索**: 对于模糊查询，可以同时检索两个数据库并合并结果
4. **缓存机制**: 对常见查询进行缓存，提高响应速度
5. **错误处理**: 增强 Elasticsearch 连接失败时的降级处理

## 文件清单

修改的文件：
- ✅ `src/agent/retriever6.py` - 主要实现文件

新增的文件：
- ✅ `src/agent/RETRIEVER6_WORKFLOW.md` - 工作流说明文档
- ✅ `src/agent/CHANGES_SUMMARY.md` - 本文件，修改总结



