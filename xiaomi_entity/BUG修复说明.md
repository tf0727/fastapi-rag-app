# Bug 修复说明

## 已修复的问题

### 1. IK 分词器未安装问题
**错误**: `analyzer [ik_smart] has not been configured in mappings`

**解决方案**: 
- 已安装 IK 中文分词插件
- 索引映射已更新使用 `ik_max_word` 和 `ik_smart` 分词器

### 2. 详细参数字段解析错误
**错误**: `failed to parse field [详细参数.摄像头] of type [text]`

**原因**: 详细参数中存在复杂的嵌套对象结构，Elasticsearch 尝试自动映射时失败

**解决方案**: 
```python
"详细参数": {
    "type": "object",
    "enabled": False  # 禁用映射，避免嵌套对象解析错误
}
```
- 将 `详细参数` 的 `enabled` 设为 `False`，这样存储但不索引内部字段
- 使用 `详细参数_文本` 字段（转换为纯文本）进行搜索
- 使用 `详细参数_embedding` 字段进行语义搜索

### 3. 价格字段类型错误
**错误**: `failed to parse field [价格] of type [float]...Preview of field's value: '未知'`

**原因**: 部分产品价格为 "未知" 字符串，无法转换为 float 类型

**解决方案**: 在插入前处理价格字段
```python
# 处理价格字段，确保是有效的数字
价格_原始 = item.get("价格")
价格 = None
if 价格_原始 is not None:
    try:
        if isinstance(价格_原始, (int, float)):
            价格 = float(价格_原始)
        elif isinstance(价格_原始, str):
            价格_清理 = 价格_原始.replace('¥', '').replace('元', '').replace(',', '').strip()
            if 价格_清理 and 价格_清理.lower() not in ['未知', 'unknown', 'n/a', '-', '']:
                价格 = float(价格_清理)
    except (ValueError, TypeError):
        价格 = None

# 只有价格为有效数字时才添加
if 价格 is not None:
    doc["价格"] = 价格
```

处理逻辑：
- 自动清理价格字符串（去除 ¥、元、逗号等）
- 将 "未知"、"unknown"、"n/a" 等无效值设为 `None`
- 只在价格有效时才添加到文档中

### 4. 查询脚本价格显示优化
**更新**: 在显示结果时优雅处理价格为 None 的情况
```python
价格显示 = f"¥{hit['价格']}" if hit['价格'] is not None else "价格未知"
print(f"   类别: {hit['类别']} | 价格: {价格显示} | 评分: {hit['score']:.3f}")
```

## 现在可以正常运行了！

### 重新导入数据
```bash
cd xiaomi-entity
python insert_xiaomi_data.py
```

预期结果：
- 所有 1435 条产品数据成功导入
- 自动生成 4 个 embedding 字段
- 价格无效的产品会跳过价格字段
- 详细参数保留原始结构但不索引内部字段

### 测试查询
```bash
python query_xiaomi_products.py
```

## 数据统计

导入后会显示：
- 成功导入数量
- 失败数量（应为 0）
- 索引验证信息
- 示例文档预览

## 注意事项

1. **价格查询**: 部分产品没有价格字段，在使用价格范围查询时会被自动排除
2. **详细参数搜索**: 虽然详细参数对象本身不被索引，但：
   - `详细参数_文本` 字段包含参数的文本形式，支持关键词搜索
   - `详细参数_embedding` 字段支持语义相似搜索
   - 原始 `详细参数` 对象仍会在查询结果中返回

3. **IK 分词器**: 确保 Elasticsearch 已安装 IK 插件，否则需要重新安装（参考 `install_ik_plugin.md`）

## 文件更新清单

✅ `insert_xiaomi_data.py` - 数据导入脚本
  - 修复详细参数映射
  - 添加价格字段处理
  - 更新模型路径

✅ `query_xiaomi_products.py` - 查询脚本
  - 修复分词器配置
  - 优化价格显示
  - 更新模型路径

