# Retriever6 工作流程说明

## 概述
这个 RAG 系统整合了两个知识库：
- **Elasticsearch**: 存储小米产品参数和信息
- **Faiss**: 存储小米公司发展、业务增长、ESG报告等企业信息

系统会自动判断用户查询的类型，并路由到相应的数据库进行检索。

## 工作流程图

```
用户查询
    ↓
[START]
    ↓
[relevance_check] ─────────────────────┐
相关性判断                               │
    │                                  │
    │ 相关                              │ 不相关
    ↓                                  │
[rewrite]                              │
问题改写                                 │
    ↓                                  │
[query_router] ───────────┐            │
查询类型路由                │            │
    │                    │            │
    │ 产品查询            │ 公司查询     │
    ↓                    ↓            │
[retriever_elasticsearch] [retriever_faiss]
Elasticsearch检索          Faiss检索     │
    │                    │            │
    └────────┬───────────┘            │
             ↓                        ↓
    [generate_answer_with_retriever] [generate_answer]
    基于检索结果生成答案              直接生成答案
             │                        │
             └────────┬───────────────┘
                      ↓
                    [END]
```

## 节点说明

### 1. relevance_check（相关性判断）
- **功能**: 判断用户问题是否与小米公司业务或产品相关
- **输出**: "是" 或 "不相关"
- **路由逻辑**:
  - 相关 → `rewrite` 节点
  - 不相关 → `generate_answer` 节点（直接回答）

### 2. rewrite（问题改写）
- **功能**: 将用户问题改写为更清晰、准确的陈述句
- **示例**:
  - 输入: "小米14 Pro的处理器是什么？"
  - 输出: "小米14 Pro的处理器型号和配置"

### 3. query_router（查询路由）⭐ 新增
- **功能**: 判断查询类型并路由到不同的检索器
- **分类标准**:
  - **产品信息**: 产品参数、功能、价格、配置、型号、规格等
  - **公司信息**: 公司发展、业务增长、ESG报告、企业战略、环境政策、社会责任等
- **输出**: "产品" 或 "公司"
- **路由逻辑**:
  - 产品 → `retriever_elasticsearch`
  - 公司 → `retriever_faiss`

### 4. retriever_elasticsearch（产品信息检索）⭐ 新增
- **数据源**: Elasticsearch
- **检索内容**: 小米产品参数和信息
- **返回格式**:
  ```
  产品：小米14 Pro
  类别：手机
  简介：...
  价格：...
  详细参数：...
  相关度评分：...
  ```

### 5. retriever_faiss（公司信息检索）⭐ 新增
- **数据源**: Faiss 向量数据库
- **检索内容**: 小米公司发展、业务增长、ESG报告等
- **检索参数**: 相似度搜索，返回前5个最相关文档

### 6. generate_answer_with_retriever（基于检索生成答案）
- **功能**: 基于检索到的上下文生成最终答案
- **特点**:
  - 使用 Markdown 格式
  - 引用上下文中的图片和表格
  - 不添加上下文之外的信息

### 7. generate_answer（直接生成答案）
- **功能**: 对于不相关的问题直接生成答案
- **触发条件**: 问题与小米无关

## 关键特性

### 🎯 智能路由
系统使用 LLM 进行两层判断：
1. **第一层**: 判断问题是否与小米相关
2. **第二层**: 判断是产品查询还是公司信息查询

### 🔍 双数据库检索
- **Elasticsearch**: 
  - 多字段向量搜索
  - 支持产品名称、简介、类别、详细参数等多维度检索
  - 权重可配置
  
- **Faiss**: 
  - 高效的向量相似度搜索
  - 适合非结构化文档检索

### 📝 问题改写
将疑问句改写为陈述句，提高检索准确度

## 使用示例

### 示例1：公司信息查询
```python
ask_question("小米集团在2024年的碳排放目标是什么？")
```
**路由路径**: START → relevance_check → rewrite → query_router → retriever_faiss → generate_answer_with_retriever → END

### 示例2：产品信息查询
```python
ask_question("小米14 Pro的处理器是什么？")
```
**路由路径**: START → relevance_check → rewrite → query_router → retriever_elasticsearch → generate_answer_with_retriever → END

### 示例3：不相关查询
```python
ask_question("帮我写一首古诗")
```
**路由路径**: START → relevance_check → generate_answer → END

## 配置说明

### Elasticsearch 配置
- **主机**: localhost:9200
- **索引**: xiaomi_products
- **检索数量**: 5条
- **最小评分**: 0.3

### Faiss 配置
- **存储路径**: E:/shoushixiaomi/demo/rag-xiaomi/faiss-pkl
- **检索类型**: 相似度搜索
- **检索数量**: 5条

### LLM 配置
- **模型**: qwen-plus
- **温度**: 0（确保输出稳定性）

## 扩展建议

1. **增加更多数据源**: 可以添加更多检索器节点，如财报数据库、技术文档库等
2. **优化路由逻辑**: 可以使用更复杂的分类模型进行查询分类
3. **混合检索**: 对于某些查询，可以同时检索多个数据源并合并结果
4. **添加缓存**: 对常见问题进行缓存，提高响应速度
5. **评估指标**: 添加检索质量评估，记录路由准确率

## 注意事项

⚠️ **消息索引**: 在检索节点中，需要正确获取改写后的问题：
- `state["messages"][-2].content` 获取改写后的问题
- `state["messages"][-1].content` 获取路由结果

⚠️ **Elasticsearch 依赖**: 需要确保 Elasticsearch 服务正在运行

⚠️ **模型路径**: 确保 Embedding 模型路径正确配置

