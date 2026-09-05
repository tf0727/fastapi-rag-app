from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import json

model = SentenceTransformer('../9.embedding语义模型微调/微调/new_bge-base-zh-v1.5', device='cuda')
es = Elasticsearch("http://localhost:9200")

# 创建索引映射
def create_index(es, index_name="drugs"):
    """
    创建药物索引及映射，包含embedding字段
    """
    # 如果索引已存在，先删除
    if es.indices.exists(index=index_name):
        print(f"索引 {index_name} 已存在，正在删除...")
        es.indices.delete(index=index_name)
    
    # 设置索引映射
    mappings = {
        "mappings": {
            "properties": {
                "药物名称": {"type": "text","analyzer": "ik_max_word", "search_analyzer": "ik_smart" },
                "药物拼音": {"type": "keyword"},
                "药物英文": {"type": "keyword"},
                "介绍": {
                    "type": "text",
                    "analyzer": "ik_max_word", 
                    "search_analyzer": "ik_smart"
                },
                "性状": {"type": "text", "analyzer": "ik_max_word"},
                "检查": {"type": "text", "analyzer": "ik_max_word"},
                "鉴别": {"type": "text", "analyzer": "ik_max_word"},
                "性味与归经": {"type": "text", "analyzer": "ik_max_word"},
                "功能与主治": {"type": "text", "analyzer": "ik_max_word"},
                "用法与用量": {"type": "text", "analyzer": "ik_max_word"},
                "主要成分": {"type": "text", "analyzer": "ik_max_word"},
                "含量测定": {"type": "text", "analyzer": "ik_max_word"},
                "注意": {"type": "text", "analyzer": "ik_max_word"},
                "禁忌": {"type": "text", "analyzer": "ik_max_word"},
                "规格": {"type": "text", "analyzer": "ik_max_word"},
                "贮藏": {"type": "text", "analyzer": "ik_max_word"},
                # 添加embedding字段
                "药物名称_embedding": {
                    "type": "dense_vector",
                    "dims": 768,  # 根据模型输出维度调整
                    "index": True,
                    "similarity": "cosine"
                },
                "介绍_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                },
                "功能与主治_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "max_result_window": 10000
        }
    }
    # 创建索引
    try:
        es.indices.create(index=index_name, body=mappings)
        print(f"索引 {index_name} 创建成功")
        return True
    except Exception as e:
        print(f"创建索引时出错: {e}")
        return False
# 生成文本的embedding
def generate_embedding(model, text):
    if len(text) <= 1:
        return None
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()

def index_data(es, data, model=None, index_name="drugs"):
    """
    逐条导入药物数据到Elasticsearch，包含embedding
    """
    for i, item in enumerate(data):
        # 为需要的字段生成embedding
        drug_name_embedding = generate_embedding(model, item.get("药物名称", ""))
        intro_embedding = generate_embedding(model, item.get("介绍", ""))
        function_embedding = generate_embedding(model, item.get("功能与主治", ""))
        
        # 构建文档
        doc = {
            "药物名称": item.get("药物名称", ""),
            "药物拼音": item.get("药物拼音", ""),
            "药物英文": item.get("药物英文", ""),
            "介绍": item.get("介绍", ""),
            "性状": item.get("性状", ""),
            "性味归经": item.get("性味归经", ""),
            "功能与主治": item.get("功能与主治", ""),
            "用法与用量": item.get("用法与用量", ""),
            "主要成分": item.get("主要成分", ""),
            "药理作用": item.get("药理作用", ""),
            "注意": item.get("注意", ""),
            "禁忌": item.get("禁忌", ""),
            "不良反应": item.get("不良反应", ""),
            "贮藏": item.get("贮藏", ""),
        }
        
        # 只有当embedding不为None时才添加到文档中
        if drug_name_embedding is not None:
            doc["药物名称_embedding"] = drug_name_embedding
        if intro_embedding is not None:
            doc["介绍_embedding"] = intro_embedding
        if function_embedding is not None:
            doc["功能与主治_embedding"] = function_embedding
        es.index(index=index_name, document=doc)
        # 插入数据
        try:
            es.index(index=index_name, document=doc)
            if (i + 1) % 100 == 0:  # 每100条显示一次进度
                print(f"已导入 {i + 1} 条数据")
        except Exception as e:
            print(f"导入第 {i + 1} 条数据时出错: {e}")
    
    print(f"数据导入完成，共导入 {len(data)} 条数据")

def main():
    with open('../3.结构化处理/最终解析结果.json', 'r', encoding='utf-8') as f:
        all_drugs_dict = json.load(f)
    print(f"成功加载药物数据，共 {len(all_drugs_dict)} 条")
    
    # 将字典格式转换为列表格式
    all_drugs = []
    for drug_name, drug_info in all_drugs_dict.items():
        # 合并饮片信息到主信息中
        if "饮片" in drug_info:
            decoction_piece = drug_info.pop("饮片")
            drug_info.update(decoction_piece)
        drug_info["药物名称"] = drug_name
        all_drugs.append(drug_info)
    
    if create_index(es, "drugs"): # 创建索引
        index_data(es, all_drugs, model, "drugs")         # 导入数据
    else:
        print("创建索引失败")

if __name__ == "__main__":
    main()