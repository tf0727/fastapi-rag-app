# 小米产品 Elasticsearch 索引和查询系统

本项目提供了将小米产品数据导入 Elasticsearch 并进行多种方式查询的完整解决方案。

## 文件说明

- `xiaomi_merged_results.json` - 小米产品数据集（包含商品名称、类别、价格、详细参数等）
- `insert_xiaomi_data.py` - 数据导入脚本（创建索引并插入数据，支持多字段embedding）
- `query_xiaomi_products.py` - 查询脚本（支持文本搜索、向量搜索、混合搜索等多种查询方式）
- `1.数据库设计和插入.py` - 参考示例（药物数据）
- `5.多embedding、混合查询.py` - 参考示例（多embedding查询）

## 功能特性

### 数据导入 (insert_xiaomi_data.py)

1. **索引设计**
   - 商品名称（支持中文分词）
   - 类别（关键字类型）
   - 价格（浮点数类型）
   - 简介（支持中文分词）
   - 详细参数（对象类型，保留原始结构）
   - 详细参数文本（将参数转为文本，支持搜索）

2. **Embedding字段**
   - 商品名称_embedding (768维向量)
   - 简介_embedding (768维向量)
   - 类别_embedding (768维向量)
   - 详细参数_embedding (768维向量)

3. **特性**
   - 自动生成多个字段的embedding向量
   - 支持GPU/CPU自动切换
   - 批量导入，显示进度条
   - 完整的错误处理和统计信息

### 查询功能 (query_xiaomi_products.py)

1. **多Embedding向量搜索**
   - 在多个embedding字段中同时搜索
   - 可自定义各字段权重
   - 支持最小相似度阈值过滤

2. **混合搜索**
   - 结合传统文本搜索和向量搜索
   - 可调节文本/向量权重比例
   - 支持价格范围过滤
   - 支持类别过滤

3. **相似产品查找**
   - 根据指定产品找到最相似的其他产品
   - 可选择不同的embedding字段进行相似度比较

4. **其他查询**
   - 按类别搜索
   - 按价格范围搜索
   - 类别统计信息

## 环境要求

### 必需组件

1. **Elasticsearch 7.x 或更高版本**
   - 需要安装并启动 Elasticsearch
   - 默认地址: `http://localhost:9200`
   - 需要安装 IK 中文分词插件

2. **Python 3.8+**

3. **Python依赖包**
```bash
pip install elasticsearch==7.17.9
pip install sentence-transformers
pip install torch
pip install tqdm
```

4. **Embedding模型**
   - 需要下载 bge-base-zh-v1.5 模型
   - 默认路径: `../bge-base-zh-v1.5`
   - 可从 HuggingFace 下载: https://huggingface.co/BAAI/bge-base-zh-v1.5

### 安装 Elasticsearch IK 分词插件

```bash
# 进入 Elasticsearch 安装目录
cd /path/to/elasticsearch

# 安装 IK 分词插件
./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v7.17.9/elasticsearch-analysis-ik-7.17.9.zip

# 重启 Elasticsearch
```

## 使用方法

### 1. 启动 Elasticsearch

确保 Elasticsearch 服务正在运行：

```bash
# Linux/Mac
./bin/elasticsearch

# Windows
.\bin\elasticsearch.bat
```

验证服务状态：
```bash
curl http://localhost:9200
```

### 2. 导入数据

运行数据导入脚本：

```bash
cd xiaomi-entity
python insert_xiaomi_data.py
```

**脚本执行流程：**
1. 加载 `xiaomi_merged_results.json` 数据文件
2. 加载 embedding 模型（自动尝试GPU，失败则使用CPU）
3. 删除已存在的索引（如果有）
4. 创建新索引和映射
5. 为每条产品数据生成4个embedding向量
6. 批量导入数据到 Elasticsearch
7. 显示导入统计和验证信息

**预期输出示例：**
```
正在加载数据文件: xiaomi_merged_results.json
成功加载数据，共 1234 条产品信息
成功加载模型: ../bge-base-zh-v1.5
索引 xiaomi_products 已存在，正在删除...
索引 xiaomi_products 创建成功

开始导入数据，共 1234 条...
导入进度: 100%|██████████| 1234/1234 [05:23<00:00,  3.82it/s]

数据导入完成！
成功: 1234 条
失败: 0 条
总计: 1234 条
```

### 3. 查询数据

运行查询脚本：

```bash
python query_xiaomi_products.py
```

或者在自己的代码中使用：

```python
from query_xiaomi_products import XiaomiProductSearch

# 创建搜索器
searcher = XiaomiProductSearch(
    model_path='../bge-base-zh-v1.5',
    host="http://localhost:9200",
    index_name="xiaomi_products"
)

# 1. 混合搜索（推荐）
results = searcher.hybrid_multi_embedding_search(
    query_text="拍照效果好的手机",
    size=5
)
searcher.print_results(results)

# 2. 纯向量搜索
results = searcher.multi_embedding_search(
    query_text="商务背包",
    field_weights={
        "商品名称_embedding": 2.5,
        "简介_embedding": 2.0,
        "详细参数_embedding": 1.5
    },
    size=10
)

# 3. 带过滤条件的混合搜索
results = searcher.hybrid_multi_embedding_search(
    query_text="智能手表",
    price_range={"gte": 500, "lte": 2000},
    category_filter="智能穿戴",
    size=5
)

# 4. 查找相似产品
results = searcher.find_similar_products(
    product_name="小米13 Pro",
    embedding_field="简介_embedding",
    size=5
)

# 5. 按类别搜索
results = searcher.search_by_category("智能穿戴", size=10)

# 6. 按价格范围搜索
results = searcher.search_by_price_range(
    min_price=100,
    max_price=500,
    size=20
)

# 7. 获取类别统计
stats = searcher.get_category_stats()
for bucket in stats:
    print(f"{bucket['key']}: {bucket['doc_count']}个产品")
```

## 查询示例

### 示例 1: 自然语言查询

```python
# 查询：适合运动的智能手表
results = searcher.hybrid_multi_embedding_search(
    query_text="适合运动的智能手表",
    size=3
)

# 结果会综合考虑：
# - 商品名称中的关键词匹配
# - 简介中的语义相似度
# - 类别信息
# - 详细参数的相关性
```

### 示例 2: 价格筛选查询

```python
# 查询：500-1000元的耳机
results = searcher.hybrid_multi_embedding_search(
    query_text="蓝牙耳机 降噪",
    price_range={"gte": 500, "lte": 1000},
    size=5
)
```

### 示例 3: 类别筛选查询

```python
# 查询：生活类别中的户外用品
results = searcher.hybrid_multi_embedding_search(
    query_text="户外运动装备",
    category_filter="生活",
    size=10
)
```

### 示例 4: 相似产品推荐

```python
# 找到与"小米手环7"相似的产品
results = searcher.find_similar_products(
    product_name="小米手环7",
    embedding_field="简介_embedding",
    size=5,
    exclude_self=True
)
```

## 参数调优建议

### Embedding字段权重调整

不同查询场景可以调整字段权重：

```python
# 场景1: 精确产品查找（强调商品名称）
field_weights = {
    "商品名称_embedding": 3.0,
    "简介_embedding": 1.5,
    "类别_embedding": 0.5,
    "详细参数_embedding": 1.0
}

# 场景2: 功能性查询（强调简介和参数）
field_weights = {
    "商品名称_embedding": 1.5,
    "简介_embedding": 2.5,
    "类别_embedding": 1.0,
    "详细参数_embedding": 2.0
}

# 场景3: 类别探索（强调类别）
field_weights = {
    "商品名称_embedding": 1.0,
    "简介_embedding": 1.5,
    "类别_embedding": 3.0,
    "详细参数_embedding": 1.0
}
```

### 文本/向量权重比例

```python
# 精确匹配场景（提高文本权重）
results = searcher.hybrid_multi_embedding_search(
    query_text="小米13 Pro",
    text_weight=0.6,
    vector_weight=0.4
)

# 语义搜索场景（提高向量权重）
results = searcher.hybrid_multi_embedding_search(
    query_text="拍照清晰的手机",
    text_weight=0.3,
    vector_weight=0.7
)
```

## 索引结构

### 完整的映射定义

```json
{
  "mappings": {
    "properties": {
      "商品名称": {
        "type": "text",
        "analyzer": "ik_max_word",
        "search_analyzer": "ik_smart",
        "fields": {
          "keyword": {"type": "keyword"}
        }
      },
      "类别": {"type": "keyword"},
      "价格": {"type": "float"},
      "简介": {
        "type": "text",
        "analyzer": "ik_max_word",
        "search_analyzer": "ik_smart"
      },
      "相关链接": {"type": "keyword"},
      "详细参数": {"type": "object", "enabled": true},
      "详细参数_文本": {
        "type": "text",
        "analyzer": "ik_max_word",
        "search_analyzer": "ik_smart"
      },
      "商品名称_embedding": {
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      },
      "简介_embedding": {
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      },
      "类别_embedding": {
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      },
      "详细参数_embedding": {
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      }
    }
  }
}
```

## 常见问题

### 1. 模型加载失败

**问题**: `加载模型失败`

**解决方案**:
- 确认模型路径正确
- 下载 bge-base-zh-v1.5 模型
- 如果没有GPU，脚本会自动切换到CPU模式

### 2. Elasticsearch 连接失败

**问题**: `Connection refused`

**解决方案**:
- 确认 Elasticsearch 服务正在运行
- 检查端口是否为 9200
- 检查防火墙设置

### 3. IK 分词插件未安装

**问题**: `unknown analyzer [ik_max_word]`

**解决方案**:
```bash
# 安装 IK 分词插件
./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v7.17.9/elasticsearch-analysis-ik-7.17.9.zip

# 重启 Elasticsearch
```

### 4. 内存不足

**问题**: 导入大量数据时内存溢出

**解决方案**:
- 增加 Elasticsearch JVM 堆内存
- 修改 `config/jvm.options`:
  ```
  -Xms4g
  -Xmx4g
  ```

### 5. Embedding 维度不匹配

**问题**: `dimension mismatch`

**解决方案**:
- 确认使用的模型是 bge-base-zh-v1.5（768维）
- 如果使用其他模型，需要修改映射中的 `dims` 参数

## 性能优化

### 1. 批量导入优化

可以修改 `insert_xiaomi_data.py`，使用 bulk API 加速导入：

```python
from elasticsearch.helpers import bulk

def bulk_index_data(self, data, batch_size=100):
    actions = []
    for item in data:
        # ... 构建doc ...
        action = {
            "_index": self.index_name,
            "_source": doc
        }
        actions.append(action)
        
        if len(actions) >= batch_size:
            bulk(self.es, actions)
            actions = []
    
    if actions:
        bulk(self.es, actions)
```

### 2. 查询性能优化

- 使用过滤条件减少搜索范围
- 合理设置 `size` 参数
- 考虑使用缓存机制

### 3. Elasticsearch 配置优化

```yaml
# elasticsearch.yml
indices.queries.cache.size: 10%
index.refresh_interval: 30s
```

## 扩展建议

1. **添加更多 Embedding 字段**
   - 可以为更多字段生成 embedding
   - 例如：品牌、型号、特性标签等

2. **实现高级过滤**
   - 多条件组合过滤
   - 范围查询
   - 地理位置查询

3. **添加聚合统计**
   - 价格分布统计
   - 品牌分布统计
   - 热门产品排行

4. **用户行为学习**
   - 点击率优化
   - 个性化推荐
   - A/B 测试

## 许可证

MIT License

## 参考资料

- [Elasticsearch 官方文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [BGE Embedding 模型](https://huggingface.co/BAAI/bge-base-zh-v1.5)
- [IK 中文分词插件](https://github.com/medcl/elasticsearch-analysis-ik)
- [Sentence Transformers](https://www.sbert.net/)

