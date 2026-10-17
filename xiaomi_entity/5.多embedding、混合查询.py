from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

class MultiEmbeddingSearch:
    def __init__(self, model_path='../bge-base-zh-v1.5', host="http://localhost:9200", index_name="drugs"):
        self.es = Elasticsearch(host)
        self.index_name = index_name
        # 加载embedding模型
        try:
            self.model = SentenceTransformer(model_path, device='cuda')
            print(f"成功加载模型: {model_path}")
        except Exception as e:
            print(f"加载模型失败: {e}")
            self.model = None
        
        # 定义embedding字段
        self.embedding_fields = [
            "药物名称_embedding",
            "介绍_embedding", 
            "功能与主治_embedding"
        ]
    
    def generate_query_embedding(self, query_text):
        """
        为查询文本生成embedding向量
        
        Args:
            query_text (str): 查询文本
        """
        if self.model is None:
            print("模型未加载，无法生成embedding")
            return None
        
        try:
            embedding = self.model.encode(query_text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            print(f"生成embedding失败: {e}")
            return None
    
    def multi_embedding_search(self, query_text, field_weights=None, size=10, min_score=0.5):
        """
        在多个embedding字段中进行向量搜索
        
        Args:
            query_text (str): 查询文本
            field_weights (dict): 字段权重，如 {"药物名称_embedding": 2.0, "功能与主治_embedding": 1.5}
            size (int): 返回结果数量，默认10条
            min_score (float): 最小相似度阈值，默认0.5
        """
        # 生成查询向量
        query_embedding = self.generate_query_embedding(query_text)
        if query_embedding is None:
            return None
        
        # 默认权重设置
        if field_weights is None:
            field_weights = {
                "药物名称_embedding": 2.0,
                "介绍_embedding": 1.5,
                "功能与主治_embedding": 1.8
            }
        
        # 构建多字段向量查询
        should_queries = []
        for field, weight in field_weights.items():
            should_queries.append({
                "script_score": {
                    "query": {
                        "exists": {
                            "field": field
                        }
                    },
                    "script": {
                        "source": f"(cosineSimilarity(params.query_vector, '{field}') + 1.0) * {weight}",
                        "params": {
                            "query_vector": query_embedding
                        }
                    }
                }
            })
        
        search_body = {
            "query": {
                "bool": {
                    "should": should_queries
                }
            },
            "min_score": min_score,
            "size": size
        }
        
        try:
            response = self.es.search(index=self.index_name, body=search_body)
            return self.format_results(response, query_text, field_weights)
        except Exception as e:
            print(f"多embedding向量搜索出错: {e}")
            return None
    
    def hybrid_multi_embedding_search(self, query_text, field_weights=None, text_weight=0.3, vector_weight=0.7, size=10):
        """
        混合搜索：结合文本搜索和多embedding向量搜索
        
        Args:
            query_text (str): 查询文本
            field_weights (dict): embedding字段权重
            text_weight (float): 文本搜索权重，默认0.3
            vector_weight (float): 向量搜索权重，默认0.7
            size (int): 返回结果数量，默认10条
        """
        # 生成查询向量
        query_embedding = self.generate_query_embedding(query_text)
        if query_embedding is None:
            return None
        
        # 默认权重设置
        if field_weights is None:
            field_weights = {
                "药物名称_embedding": 2.0,
                "介绍_embedding": 1.5,
                "功能与主治_embedding": 1.8
            }
        
        # 构建查询
        should_queries = []
        
        # 添加文本搜索
        text_fields = ["药物名称", "介绍", "功能与主治"]
        should_queries.append({
            "multi_match": {
                "query": query_text,
                "fields": text_fields,
                "type": "best_fields",
                "analyzer": "ik_smart",
                "boost": text_weight
            }
        })
        
        # 添加向量搜索
        for field, weight in field_weights.items():
            should_queries.append({
                "script_score": {
                    "query": {
                        "exists": {
                            "field": field
                        }
                    },
                    "script": {
                        "source": f"(cosineSimilarity(params.query_vector, '{field}') + 1.0) * {weight} * {vector_weight}",
                        "params": {
                            "query_vector": query_embedding
                        }
                    }
                }
            })
        
        search_body = {
            "query": {
                "bool": {
                    "should": should_queries
                }
            },
            "size": size
        }
        
        try:
            response = self.es.search(index=self.index_name, body=search_body)
            return self.format_results(response, query_text, field_weights, hybrid=True)
        except Exception as e:
            print(f"混合多embedding搜索出错: {e}")
            return None
    
    def find_most_similar_by_embedding(self, drug_name, embedding_field="介绍_embedding", size=10, exclude_self=True):
        """
        根据指定embedding字段找到最相似的药物
        
        Args:
            drug_name (str): 药物名称
            embedding_field (str): 用于比较的embedding字段
            size (int): 返回结果数量，默认10条
            exclude_self (bool): 是否排除自身，默认True
        
        Returns:
            dict: 搜索结果
        """
        if embedding_field not in self.embedding_fields:
            print(f"无效的embedding字段: {embedding_field}")
            return None
        
        # 首先获取该药物的指定embedding
        get_drug_body = {
            "query": {
                "match": {
                    "药物名称": drug_name
                }
            },
            "size": 1
        }
        
        try:
            response = self.es.search(index=self.index_name, body=get_drug_body)
            if response['hits']['total']['value'] == 0:
                print(f"未找到药物: {drug_name}")
                return None
            
            drug_embedding = response['hits']['hits'][0]['_source'].get(embedding_field)
            if drug_embedding is None:
                print(f"药物 {drug_name} 没有 {embedding_field}")
                return None
            
            # 使用该药物的embedding查找相似药物
            search_body = {
                "query": {
                    "script_score": {
                        "query": {
                            "exists": {
                                "field": embedding_field
                            }
                        },
                        "script": {
                            "source": f"cosineSimilarity(params.query_vector, '{embedding_field}') + 1.0",
                            "params": {
                                "query_vector": drug_embedding
                            }
                        }
                    }
                },
                "size": size + (1 if exclude_self else 0)
            }
            
            if exclude_self:
                search_body["query"]["script_score"]["query"] = {
                    "bool": {
                        "must": {
                            "exists": {
                                "field": embedding_field
                            }
                        },
                        "must_not": {
                            "match": {
                                "药物名称": drug_name
                            }
                        }
                    }
                }
            
            response = self.es.search(index=self.index_name, body=search_body)
            return self.format_results(response, f"与{drug_name}在{embedding_field}字段最相似的药物")
            
        except Exception as e:
            print(f"查找最相似药物出错: {e}")
            return None
    
    def compare_drug_similarities(self, drug_name, size=5):
        """
        比较一个药物在不同embedding字段下的相似药物
        
        Args:
            drug_name (str): 药物名称
            size (int): 每个字段返回的结果数量
        """
        results = {}
        
        for field in self.embedding_fields:
            field_name = field.replace("_embedding", "")
            print(f"基于 {field_name} 查找相似药物...")
            
            similar_drugs = self.find_most_similar_by_embedding(drug_name, field, size)
            results[field_name] = similar_drugs
        
        return results
    
    def format_results(self, response, query_info="", field_weights=None, hybrid=False):
        """
        格式化搜索结果
        
        Args:
            response: Elasticsearch响应
            query_info (str): 查询信息
            field_weights (dict): 字段权重信息
            hybrid (bool): 是否为混合搜索
        """
        results = {
            "query": query_info,
            "field_weights": field_weights,
            "is_hybrid": hybrid,
            "total": response['hits']['total']['value'],
            "took": response['took'],
            "hits": []
        }
        
        for hit in response['hits']['hits']:
            formatted_hit = {
                "score": hit['_score'],
                "药物名称": hit['_source'].get('药物名称', ''),
                "介绍": hit['_source'].get('介绍', ''),
                "功能与主治": hit['_source'].get('功能与主治', ''),
                "用法与用量": hit['_source'].get('用法与用量', ''),
                "主要成分": hit['_source'].get('主要成分', ''),
                "性味与归经": hit['_source'].get('性味与归经', ''),
                "注意": hit['_source'].get('注意', ''),
                "禁忌": hit['_source'].get('禁忌', '')
            }
            
            # 计算各字段的embedding相似度（如果不是混合搜索）
            if not hybrid and field_weights:
                formatted_hit["embedding_similarities"] = {}
                # 这里可以添加具体的相似度计算逻辑
            
            results['hits'].append(formatted_hit)
        
        return results

if __name__ == "__main__":
    searcher = MultiEmbeddingSearch()

    print("=== 多Embedding字段查询测试 ===\n")

    queries = [
        "清热解毒的中药",
        "治疗感冒发热",
        "消炎止痛药物",
        "心脏病用药"
    ]

    for query in queries:
        print(f"查询: {query}")
        print("-" * 60)

        # 1. 多embedding向量搜索
        print("1. 多embedding向量搜索:")
        results = searcher.multi_embedding_search(query, size=3)
        if results and results['hits']:
            print(f"找到 {results['total']} 条结果，耗时 {results['took']}ms")
            print(f"字段权重: {results['field_weights']}")
            for i, hit in enumerate(results['hits'], 1):
                print(f"{i}. {hit['药物名称']} (评分: {hit['score']:.3f})")
                print(f"功能与主治: {hit['功能与主治'][:60]}...")
        else:
            print("未找到结果")

        # 3. 混合搜索
        print("3. 混合搜索:")
        results = searcher.hybrid_multi_embedding_search(query, size=3)
        if results and results['hits']:
            print(f"找到 {results['total']} 条结果，耗时 {results['took']}ms")
            for i, hit in enumerate(results['hits'], 1):
                print(f"{i}. {hit['药物名称']} (综合评分: {hit['score']:.3f})")
        else:
            print("未找到结果")

        print("=" * 80)

    # 相似药物查找示例
    print("\n=== 相似药物查找测试 ===")
    drug_name = "阿司匹林"  # 可以根据实际数据调整
    print(f"查找与 '{drug_name}' 相似的药物:")

    # 比较不同字段的相似性
    comparison_results = searcher.compare_drug_similarities(drug_name, size=3)
    for field_name, results in comparison_results.items():
        if results and results['hits']:
            print(f"\n基于 {field_name} 的相似药物:")
            for i, hit in enumerate(results['hits'], 1):
                print(f"  {i}. {hit['药物名称']} (相似度: {hit['score']:.3f})")