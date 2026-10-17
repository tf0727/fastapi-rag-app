import os
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import json
from tqdm import tqdm

class XiaomiDataIndexer:
    def __init__(self, model_path='../bge-base-zh-v1.5', es_host="http://localhost:9200", index_name="xiaomi_products"):
        """
        初始化小米产品数据索引器
        
        Args:
            model_path (str): embedding模型路径
            es_host (str): Elasticsearch地址
            index_name (str): 索引名称
        """
        self.es = Elasticsearch(es_host)
        self.index_name = index_name
        
        # 加载embedding模型
        try:
            self.model = SentenceTransformer(model_path, device='cuda')
            print(f"成功加载模型: {model_path}")
        except Exception as e:
            print(f"加载模型失败，尝试使用CPU: {e}")
            try:
                self.model = SentenceTransformer(model_path, device='cpu')
                print(f"成功加载模型（CPU模式）: {model_path}")
            except Exception as e2:
                print(f"加载模型完全失败: {e2}")
                self.model = None
    
    def create_index(self):
        """
        创建小米产品索引及映射，包含embedding字段
        """
        # 如果索引已存在，先删除
        if self.es.indices.exists(index=self.index_name):
            print(f"索引 {self.index_name} 已存在，正在删除...")
            self.es.indices.delete(index=self.index_name)
        
        # 设置索引映射
        mappings = {
            "mappings": {
                "properties": {
                    "商品名称": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "类别": {
                        "type": "keyword"
                    },
                    "价格": {
                        "type": "float"
                    },
                    "简介": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart"
                    },
                    "相关链接": {
                        "type": "keyword"
                    },
                    "详细参数": {
                        "type": "object",
                        "enabled": False  # 禁用映射，避免嵌套对象解析错误
                    },
                    # 参数文本（将详细参数转换为文本用于搜索）
                    "详细参数_文本": {
                        "type": "text",
                        "analyzer": "ik_max_word",
                        "search_analyzer": "ik_smart"
                    },
                    # Embedding字段
                    "商品名称_embedding": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "简介_embedding": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "类别_embedding": {
                        "type": "dense_vector",
                        "dims": 768,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "详细参数_embedding": {
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
            self.es.indices.create(index=self.index_name, body=mappings)
            print(f"索引 {self.index_name} 创建成功")
            return True
        except Exception as e:
            print(f"创建索引时出错: {e}")
            return False
    
    def generate_embedding(self, text):
        """
        生成文本的embedding向量
        
        Args:
            text (str): 输入文本
            
        Returns:
            list: embedding向量，失败返回None
        """
        if self.model is None:
            return None
        
        if not text or len(str(text).strip()) <= 1:
            return None
        
        try:
            embedding = self.model.encode(str(text), convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            print(f"生成embedding失败: {e}")
            return None
    
    def convert_params_to_text(self, params):
        """
        将详细参数字典转换为文本字符串，方便搜索和生成embedding
        
        Args:
            params (dict): 详细参数字典
            
        Returns:
            str: 参数文本
        """
        if not params:
            return ""
        
        text_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
                text_parts.append(f"{key}: {value_str}")
            elif isinstance(value, dict):
                # 递归处理嵌套字典
                nested_text = self.convert_params_to_text(value)
                if nested_text:
                    text_parts.append(f"{key}: {nested_text}")
            else:
                text_parts.append(f"{key}: {value}")
        
        return "; ".join(text_parts)
    
    def index_data(self, data):
        """
        批量导入小米产品数据到Elasticsearch，包含embedding
        
        Args:
            data (list): 产品数据列表
        """
        success_count = 0
        fail_count = 0
        
        print(f"\n开始导入数据，共 {len(data)} 条...")
        
        for i, item in enumerate(tqdm(data, desc="导入进度")):
            try:
                # 提取基本字段
                商品名称 = item.get("商品名称", "")
                类别 = item.get("类别", "")
                简介 = item.get("简介", "")
                详细参数 = item.get("详细参数", {})
                
                # 处理价格字段，确保是有效的数字
                价格_原始 = item.get("价格")
                价格 = None
                if 价格_原始 is not None:
                    try:
                        if isinstance(价格_原始, (int, float)):
                            价格 = float(价格_原始)
                        elif isinstance(价格_原始, str):
                            # 尝试转换字符串为数字，失败则设为None
                            价格_清理 = 价格_原始.replace('¥', '').replace('元', '').replace(',', '').strip()
                            if 价格_清理 and 价格_清理.lower() not in ['未知', 'unknown', 'n/a', '-', '']:
                                价格 = float(价格_清理)
                    except (ValueError, TypeError):
                        价格 = None
                
                # 将详细参数转换为文本
                详细参数_文本 = self.convert_params_to_text(详细参数)
                
                # 生成embedding
                商品名称_embedding = self.generate_embedding(商品名称)
                简介_embedding = self.generate_embedding(简介)
                类别_embedding = self.generate_embedding(类别)
                详细参数_embedding = self.generate_embedding(详细参数_文本)
                
                # 构建文档
                doc = {
                    "商品名称": 商品名称,
                    "类别": 类别,
                    "简介": 简介,
                    "相关链接": item.get("相关链接", ""),
                    "详细参数": 详细参数,
                    "详细参数_文本": 详细参数_文本
                }
                
                # 只有价格为有效数字时才添加
                if 价格 is not None:
                    doc["价格"] = 价格
                
                # 只有当embedding不为None时才添加到文档中
                if 商品名称_embedding is not None:
                    doc["商品名称_embedding"] = 商品名称_embedding
                if 简介_embedding is not None:
                    doc["简介_embedding"] = 简介_embedding
                if 类别_embedding is not None:
                    doc["类别_embedding"] = 类别_embedding
                if 详细参数_embedding is not None:
                    doc["详细参数_embedding"] = 详细参数_embedding
                
                # 插入数据
                self.es.index(index=self.index_name, document=doc)
                success_count += 1
                
            except Exception as e:
                fail_count += 1
                print(f"\n导入第 {i + 1} 条数据时出错: {e}")
                print(f"问题数据: {item.get('商品名称', 'Unknown')}")
        
        print(f"\n数据导入完成！")
        print(f"成功: {success_count} 条")
        print(f"失败: {fail_count} 条")
        print(f"总计: {len(data)} 条")
    
    def verify_index(self):
        """
        验证索引是否创建成功并显示统计信息
        """
        try:
            # 获取索引统计信息
            count = self.es.count(index=self.index_name)
            print(f"\n索引验证:")
            print(f"索引名称: {self.index_name}")
            print(f"文档总数: {count['count']}")
            
            # 获取一个示例文档
            sample = self.es.search(index=self.index_name, body={"size": 1})
            if sample['hits']['hits']:
                print(f"\n示例文档:")
                doc = sample['hits']['hits'][0]['_source']
                print(f"商品名称: {doc.get('商品名称')}")
                print(f"类别: {doc.get('类别')}")
                print(f"价格: {doc.get('价格')}")
                print(f"简介: {doc.get('简介', '')[:100]}...")
                
                # 检查embedding字段
                has_embeddings = []
                if '商品名称_embedding' in doc:
                    has_embeddings.append('商品名称_embedding')
                if '简介_embedding' in doc:
                    has_embeddings.append('简介_embedding')
                if '类别_embedding' in doc:
                    has_embeddings.append('类别_embedding')
                if '详细参数_embedding' in doc:
                    has_embeddings.append('详细参数_embedding')
                
                print(f"包含的embedding字段: {', '.join(has_embeddings)}")
            
            return True
        except Exception as e:
            print(f"验证索引时出错: {e}")
            return False


def main():
    # 数据文件路径
    data_file = "xiaomi_merged_results.json"
    
    # 加载数据
    print(f"正在加载数据文件: {data_file}")
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        print(f"成功加载数据，共 {len(products)} 条产品信息")
    except Exception as e:
        print(f"加载数据失败: {e}")
        return
    
    # 创建索引器实例
    indexer = XiaomiDataIndexer(
        model_path=os.getenv("EMBEDDING_MODEL", "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5"),  # 根据实际路径调整
        es_host="http://localhost:9200",
        index_name="xiaomi_products"
    )
    
    # 创建索引
    if not indexer.create_index():
        print("创建索引失败，程序退出")
        return
    
    # 导入数据
    indexer.index_data(products)
    
    # 验证索引
    indexer.verify_index()


if __name__ == "__main__":
    main()

