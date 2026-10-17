# 📚 Retriever6 文档索引

> 快速找到你需要的文档

## 🎯 我想...

### 快速开始使用
- 👉 [快速使用指南 (QUICK_START.md)](./QUICK_START.md)
- 👉 [项目总览 (README_RETRIEVER6.md)](./README_RETRIEVER6.md)

### 了解系统原理
- 👉 [工作流程说明 (RETRIEVER6_WORKFLOW.md)](./RETRIEVER6_WORKFLOW.md)
- 👉 [系统架构图 (ARCHITECTURE_DIAGRAM.md)](./ARCHITECTURE_DIAGRAM.md)
- 👉 [可视化流程图 (WORKFLOW_DIAGRAM.mmd)](./WORKFLOW_DIAGRAM.mmd)

### 查看修改内容
- 👉 [修改总结 (CHANGES_SUMMARY.md)](./CHANGES_SUMMARY.md)
- 👉 [实现总结 (IMPLEMENTATION_SUMMARY.md)](./IMPLEMENTATION_SUMMARY.md)

### 开发和扩展
- 👉 [项目总览 - 开发指南部分 (README_RETRIEVER6.md#开发指南)](./README_RETRIEVER6.md#开发指南)
- 👉 [系统架构图 - 关键技术点 (ARCHITECTURE_DIAGRAM.md#关键技术点)](./ARCHITECTURE_DIAGRAM.md#关键技术点)

## 📖 文档清单

| 文档 | 用途 | 推荐阅读顺序 | 难度 |
|------|------|-------------|------|
| [README_RETRIEVER6.md](./README_RETRIEVER6.md) | 项目总览和完整指南 | 1️⃣ | ⭐ |
| [QUICK_START.md](./QUICK_START.md) | 快速开始和常见问题 | 2️⃣ | ⭐ |
| [RETRIEVER6_WORKFLOW.md](./RETRIEVER6_WORKFLOW.md) | 工作流程详解 | 3️⃣ | ⭐⭐ |
| [ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md) | 系统架构和数据流 | 4️⃣ | ⭐⭐⭐ |
| [WORKFLOW_DIAGRAM.mmd](./WORKFLOW_DIAGRAM.mmd) | 可视化流程图 | - | ⭐ |
| [CHANGES_SUMMARY.md](./CHANGES_SUMMARY.md) | 代码修改总结 | 5️⃣ | ⭐⭐ |
| [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) | 实现总结和验证 | 6️⃣ | ⭐⭐ |
| [DOCS_INDEX.md](./DOCS_INDEX.md) | 本文件，文档索引 | - | ⭐ |

## 🔍 按主题查找

### 安装和配置
- [前提条件](./QUICK_START.md#前提条件)
- [安装依赖](./README_RETRIEVER6.md#快速开始)
- [配置说明](./README_RETRIEVER6.md#配置说明)
- [环境检查](./QUICK_START.md#步骤1检查-elasticsearch-服务)

### 使用方法
- [基本用法](./README_RETRIEVER6.md#使用示例)
- [使用示例](./QUICK_START.md#使用示例)
- [自定义配置](./QUICK_START.md#自定义配置)
- [批量查询](./README_RETRIEVER6.md#批量查询)

### 系统原理
- [工作流程图](./RETRIEVER6_WORKFLOW.md#工作流程图)
- [节点说明](./RETRIEVER6_WORKFLOW.md#节点说明)
- [整体架构](./ARCHITECTURE_DIAGRAM.md#整体架构)
- [数据流详解](./ARCHITECTURE_DIAGRAM.md#数据流详解)
- [消息流结构](./ARCHITECTURE_DIAGRAM.md#消息流结构)

### 路由机制
- [路由节点说明](./RETRIEVER6_WORKFLOW.md#3-query_router查询路由)
- [路由决策函数](./IMPLEMENTATION_SUMMARY.md#3-路由决策函数)
- [分类标准](./QUICK_START.md#示例1查询产品信息)

### 数据库检索
- [Elasticsearch 检索](./RETRIEVER6_WORKFLOW.md#4-retriever_elasticsearch产品信息检索)
- [Faiss 检索](./RETRIEVER6_WORKFLOW.md#5-retriever_faiss公司信息检索)
- [检索参数配置](./QUICK_START.md#修改检索参数)
- [字段权重设置](./ARCHITECTURE_DIAGRAM.md#3-elasticsearch-多字段检索)

### 问题排查
- [常见问题](./QUICK_START.md#常见问题)
- [调试技巧](./QUICK_START.md#调试技巧)
- [错误处理](./README_RETRIEVER6.md#常见问题)

### 开发扩展
- [项目结构](./README_RETRIEVER6.md#项目结构)
- [添加新数据源](./README_RETRIEVER6.md#添加新的数据源)
- [工作流节点说明](./README_RETRIEVER6.md#工作流节点说明)
- [关键技术点](./IMPLEMENTATION_SUMMARY.md#关键技术点)

### 性能优化
- [性能优化建议](./QUICK_START.md#性能优化建议)
- [优化建议](./IMPLEMENTATION_SUMMARY.md#优化建议)
- [监控指标](./ARCHITECTURE_DIAGRAM.md#监控指标)
- [性能分析](./IMPLEMENTATION_SUMMARY.md#性能分析)

### 代码变更
- [主要修改内容](./CHANGES_SUMMARY.md#主要修改内容)
- [工作流对比](./CHANGES_SUMMARY.md#工作流对比)
- [新增代码统计](./CHANGES_SUMMARY.md#代码统计)
- [兼容性说明](./CHANGES_SUMMARY.md#兼容性说明)

## 📋 快速参考

### 核心概念

| 概念 | 说明 | 详细文档 |
|------|------|---------|
| 相关性判断 | 判断问题是否与小米相关 | [工作流程说明](./RETRIEVER6_WORKFLOW.md#1-relevance_check相关性判断) |
| 问题改写 | 将疑问句改为陈述句 | [工作流程说明](./RETRIEVER6_WORKFLOW.md#2-rewrite问题改写) |
| 查询路由 | 判断查询类型并路由 | [工作流程说明](./RETRIEVER6_WORKFLOW.md#3-query_router查询路由) |
| Elasticsearch | 产品信息数据库 | [架构图](./ARCHITECTURE_DIAGRAM.md) |
| Faiss | 公司信息数据库 | [架构图](./ARCHITECTURE_DIAGRAM.md) |

### 配置参数

| 参数 | 默认值 | 说明 | 位置 |
|------|--------|------|------|
| model | qwen-plus | LLM模型 | retriever6.py:28 |
| temperature | 0 | LLM温度 | retriever6.py:31 |
| k (Faiss) | 5 | 检索结果数 | retriever6.py:51 |
| size (ES) | 5 | 检索结果数 | retriever6.py:70 |
| min_score (ES) | 0.3 | 最小相似度 | retriever6.py:70 |

### 工具函数

| 函数 | 功能 | 详细说明 |
|------|------|---------|
| `relevance_check_tool` | 相关性判断 | [代码](./retriever6.py#L68) |
| `rewrite_tool` | 问题改写 | [代码](./retriever6.py#L93) |
| `query_router_tool` | 查询路由 | [代码](./retriever6.py#L175) |
| `elasticsearch_retriever_tool` | ES检索 | [代码](./retriever6.py#L66) |
| `faiss_retriever_tool` | Faiss检索 | [代码](./retriever6.py#L56) |

### 节点函数

| 节点 | 函数名 | 功能 |
|------|--------|------|
| relevance_check | `relevance_check()` | 相关性判断节点 |
| rewrite | `rewrite_node()` | 问题改写节点 |
| query_router | `query_router_node()` | 查询路由节点 |
| retriever_elasticsearch | `retriever_elasticsearch()` | ES检索节点 |
| retriever_faiss | `retriever_faiss()` | Faiss检索节点 |
| generate_answer | `generate_answer()` | 直接生成答案 |
| generate_answer_with_retriever | `generate_answer_with_retriever()` | 基于检索生成 |

## 🎓 学习路径

### 初学者路径
1. 阅读 [项目总览](./README_RETRIEVER6.md)
2. 跟随 [快速开始指南](./QUICK_START.md) 运行示例
3. 查看 [工作流程说明](./RETRIEVER6_WORKFLOW.md) 理解原理
4. 尝试修改配置参数

### 开发者路径
1. 阅读 [实现总结](./IMPLEMENTATION_SUMMARY.md)
2. 研究 [系统架构图](./ARCHITECTURE_DIAGRAM.md)
3. 查看 [修改总结](./CHANGES_SUMMARY.md)
4. 参考 [添加新数据源](./README_RETRIEVER6.md#添加新的数据源)

### 运维人员路径
1. 检查 [前提条件](./QUICK_START.md#前提条件)
2. 了解 [配置说明](./README_RETRIEVER6.md#配置说明)
3. 熟悉 [常见问题](./QUICK_START.md#常见问题)
4. 设置 [监控指标](./README_RETRIEVER6.md#性能指标)

## 💡 提示

- 📖 **首次使用**: 从 [README_RETRIEVER6.md](./README_RETRIEVER6.md) 开始
- 🚀 **快速上手**: 查看 [QUICK_START.md](./QUICK_START.md)
- 🔧 **遇到问题**: 先看 [常见问题](./QUICK_START.md#常见问题)
- 🎨 **可视化**: 使用 [Mermaid 图](./WORKFLOW_DIAGRAM.mmd) 理解流程
- 📊 **性能优化**: 参考 [优化建议](./IMPLEMENTATION_SUMMARY.md#优化建议)

## 🔗 外部资源

- [LangGraph 官方文档](https://python.langchain.com/docs/langgraph)
- [LangChain 官方文档](https://python.langchain.com/)
- [Elasticsearch 文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Faiss 文档](https://github.com/facebookresearch/faiss/wiki)
- [Mermaid 在线编辑器](https://mermaid.live/)

## 📞 获取帮助

遇到问题？按照以下顺序查找答案：

1. 🔍 在本索引中搜索相关主题
2. 📖 查看 [常见问题](./QUICK_START.md#常见问题)
3. 🐛 查看 [调试技巧](./QUICK_START.md#调试技巧)
4. 📧 联系开发者或提交 Issue

---

**最后更新**: 2025年11月4日  
**版本**: v1.0



