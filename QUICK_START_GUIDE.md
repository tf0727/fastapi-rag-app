# 智能 Elasticsearch 检索工具 - 快速开始指南

## 🚀 快速开始

### 前提条件

1. ✅ Python 3.8+
2. ✅ Elasticsearch 7.x 运行在 `localhost:9200`
3. ✅ 已安装依赖包
4. ✅ 已配置通义千问 API Key
5. ✅ 已加载 bge-base-zh-v1.5 模型

### 安装依赖

```bash
pip install langchain langchain-openai langchain-community
pip install elasticsearch sentence-transformers
pip install python-dotenv
```

## 📖 使用示例

### 1. 基础使用

```python
from src.agent.retriever7 import elasticsearch_retriever_tool

# 产品价格查询
result = elasticsearch_retriever_tool.invoke("小米14 Pro的价格是多少？")
print(result)

# 价格范围查询
result = elasticsearch_retriever_tool.invoke("3000到5000元的手机推荐")
print(result)

# 类别查询
result = elasticsearch_retriever_tool.invoke("智能穿戴设备有哪些？")
print(result)

# 相似产品查询
result = elasticsearch_retriever_tool.invoke("和小米15相似的产品")
print(result)
```

### 2. 在 LangGraph 中使用

```python
from src.agent.retriever7 import ask_question

# 完整的问答流程（包含相关性判断、改写、路由等）
ask_question("小米14 Pro的处理器配置如何？")
```

### 3. 运行测试

```bash
# 单元测试
python test_smart_es_retriever.py

# 交互式演示
python demo_smart_retriever.py

# 主程序测试
cd src/agent
python retriever7.py
```

## 🎯 支持的查询类型

### 类型 1：产品参数查询

**示例查询**：
- "小米14 Pro的处理器是什么？"
- "小米15有哪些配置？"
- "红米K60的屏幕参数"

**搜索策略**：混合搜索，提高名称和参数权重

**预期结果**：返回指定产品的详细参数信息

---

### 类型 2：价格范围查询

**示例查询**：
- "2000到4000元的手机有哪些？"
- "1万以内的笔记本电脑"
- "500元以下的配件"

**搜索策略**：价格范围搜索，精确过滤

**预期结果**：只返回价格在指定范围内的产品

---

### 类型 3：类别查询

**示例查询**：
- "智能穿戴设备有哪些？"
- "给我看看生活电器"
- "有哪些智能家居产品？"

**搜索策略**：类别精确搜索

**预期结果**：返回指定类别的所有产品

---

### 类型 4：相似产品查询

**示例查询**：
- "有没有和小米14相似的产品？"
- "类似小米手环的产品推荐"
- "推荐和Redmi Note类似的手机"

**搜索策略**：基于 embedding 的相似度搜索

**预期结果**：返回功能或特性相似的产品

---

### 类型 5：功能特性查询

**示例查询**：
- "支持5G的手机"
- "有高刷屏的平板"
- "支持无线充电的手机"

**搜索策略**：混合搜索，提高参数字段权重

**预期结果**：返回满足特定功能要求的产品

## 🔧 高级配置

### 自定义字段权重

```python
# 在 LLM prompt 中会自动根据查询调整权重
# 默认权重：
field_weights = {
    "商品名称_embedding": 5.0,   # 产品名称
    "简介_embedding": 1.0,         # 产品简介
    "类别_embedding": 1.0,         # 产品类别
    "详细参数_embedding": 1.5     # 详细参数
}

# 示例：强调参数查询时
# "详细参数_embedding" 权重会自动提升到 3.0+
```

### 调整返回数量

```python
# LLM 会根据查询类型自动调整返回数量
# 一般查询：5-10 条
# 类别查询：15-20 条
# 价格查询：10-15 条
```

### 添加过滤条件

```python
# 混合搜索支持同时添加价格和类别过滤
# LLM 会自动从查询中提取这些条件

# 示例："3000元以下的智能手机"
# 自动提取：
# - price_range: {"lte": 3000}
# - category: "智能手机"
```

## 🐛 故障排查

### 问题 1：LLM 分析失败

**症状**：返回默认混合搜索结果

**原因**：JSON 解析失败或 API 调用失败

**解决**：
1. 检查 API Key 是否正确
2. 检查网络连接
3. 查看控制台错误信息

```python
# 查看调试信息
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

### 问题 2：Elasticsearch 连接失败

**症状**：`"搜索产品信息时出错"`

**原因**：Elasticsearch 未运行或连接配置错误

**解决**：
```bash
# 检查 ES 是否运行
curl http://localhost:9200

# 重启 ES
# Windows: 双击 elasticsearch.bat
# Linux: sudo systemctl start elasticsearch
```

---

### 问题 3：Embedding 模型加载失败

**症状**：`"模型未加载，无法生成embedding"`

**原因**：模型路径错误或模型文件缺失

**解决**：
```python
# 检查模型路径
model_path = "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5"
import os
print(os.path.exists(model_path))  # 应该返回 True
```

---

### 问题 4：查询结果不准确

**症状**：返回的产品不相关

**解决方法**：
1. 检查查询是否足够具体
2. 尝试不同的查询表述
3. 检查 LLM 分析的参数是否正确

```python
# 添加调试信息查看 LLM 分析结果
print("LLM 分析参数:", search_params)
```

## 📊 性能优化

### 1. 缓存 LLM 分析结果

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_llm_analysis(query: str):
    # 缓存常见查询的分析结果
    pass
```

### 2. 批量查询

```python
# 批量处理多个查询
queries = [
    "小米14的价格",
    "3000-5000元手机",
    "智能穿戴设备"
]

results = []
for query in queries:
    result = elasticsearch_retriever_tool.invoke(query)
    results.append(result)
```

### 3. 并行搜索

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_search(queries):
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(
            elasticsearch_retriever_tool.invoke, 
            queries
        )
    return list(results)
```

## 📈 监控和日志

### 添加日志记录

```python
import logging

logger = logging.getLogger(__name__)

# 在工具中添加日志
logger.info(f"查询: {query}")
logger.info(f"LLM 分析结果: {search_params}")
logger.info(f"使用搜索策略: {search_type}")
logger.info(f"返回结果数: {len(results)}")
```

### 性能监控

```python
import time

start_time = time.time()
result = elasticsearch_retriever_tool.invoke(query)
elapsed_time = time.time() - start_time

print(f"查询耗时: {elapsed_time:.2f} 秒")
```

## 🎓 最佳实践

### 1. 查询编写建议

✅ **好的查询**：
- "小米14 Pro的处理器和内存配置"（具体明确）
- "3000到5000元的5G手机"（包含明确条件）
- "智能穿戴类别的所有产品"（类别清晰）

❌ **不好的查询**：
- "手机"（太宽泛）
- "好用的"（主观模糊）
- "那个"（指代不明）

### 2. 结果处理建议

```python
result = elasticsearch_retriever_tool.invoke(query)

# 检查结果是否为空
if "未找到" in result:
    print("未找到相关产品，请尝试其他关键词")
else:
    # 处理结果
    print(result)
```

### 3. 错误处理建议

```python
try:
    result = elasticsearch_retriever_tool.invoke(query)
    print(result)
except Exception as e:
    logger.error(f"查询失败: {e}")
    # 使用备用方案
    result = searcher.hybrid_multi_embedding_search(query)
```

## 📚 更多资源

- 📖 详细文档：`SMART_ES_RETRIEVER_README.md`
- 🏗️ 架构对比：`ARCHITECTURE_COMPARISON.md`
- 📝 变更总结：`ELASTICSEARCH_TOOL_UPGRADE_SUMMARY.md`
- 🧪 测试脚本：`test_smart_es_retriever.py`
- 🎬 演示脚本：`demo_smart_retriever.py`

## 💡 提示和技巧

### 技巧 1：组合查询

```python
# 可以在一个查询中包含多个条件
query = "5000元以下支持5G的智能手机推荐"
# LLM 会自动提取：
# - 价格上限：5000
# - 功能要求：5G
# - 类别：智能手机
```

### 技巧 2：自然语言查询

```python
# 使用自然语言，无需特殊格式
queries = [
    "我想买一个2000多的手机",  # 理解为价格2000+
    "有什么好用的智能手环？",   # 理解为类别查询
    "给我推荐和小米14差不多的", # 理解为相似产品
]
```

### 技巧 3：迭代优化

```python
# 如果第一次结果不理想，尝试更具体的查询
query_v1 = "手机"  # 太宽泛
query_v2 = "小米手机"  # 更具体
query_v3 = "小米14系列手机的价格和配置"  # 最具体
```

## 🆘 获取帮助

遇到问题？

1. 查看文档：`SMART_ES_RETRIEVER_README.md`
2. 运行测试：`python test_smart_es_retriever.py`
3. 查看日志：启用 DEBUG 级别日志
4. 提交 Issue：描述问题并附上错误信息

## 🎉 开始使用

```bash
# 1. 确保服务运行
curl http://localhost:9200  # Elasticsearch

# 2. 运行演示
python demo_smart_retriever.py

# 3. 开始你的项目
from src.agent.retriever7 import elasticsearch_retriever_tool
result = elasticsearch_retriever_tool.invoke("你的查询")
print(result)
```

祝使用愉快！🚀



