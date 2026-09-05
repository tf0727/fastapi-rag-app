import os
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import json

class XiaomiProductSearch:
    def __init__(self, model_path=None, host=None, index_name="xiaomi_products"):
        """
        初始化小米产品搜索器
        
        Args:
            model_path (str): embedding模型路径
            host (str): Elasticsearch地址
            index_name (str): 索引名称
        """
        model_path = model_path or os.getenv("EMBEDDING_MODEL", "E:/demo/minerU-rag-agent/models/bge-base-zh-v1.5")
        host = host or os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")
        self.es = Elasticsearch(host)
        self.index_name = index_name
        
        # 加载embedding模型
        try:
            self.model = SentenceTransformer(model_path, device=os.getenv("EMBEDDING_DEVICE", "cpu"))
            print(f"成功加载模型: {model_path}")
        except Exception as e:
            print(f"加载模型失败，尝试使用CPU: {e}")
            try:
                self.model = SentenceTransformer(model_path, device='cpu')
                print(f"成功加载模型（CPU模式）: {model_path}")
            except Exception as e2:
                print(f"加载模型完全失败: {e2}")
                self.model = None
        
        # 定义embedding字段
        self.embedding_fields = [
            "商品名称_embedding",
            "简介_embedding",
            "类别_embedding",
            "详细参数_embedding"
        ]
    
    def generate_query_embedding(self, query_text):
        """
        为查询文本生成embedding向量
        
        Args:
            query_text (str): 查询文本
            
        Returns:
            list: embedding向量
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
            field_weights (dict): 字段权重
            size (int): 返回结果数量
            min_score (float): 最小相似度阈值
            
        Returns:
            dict: 搜索结果
        """
        # 生成查询向量
        query_embedding = self.generate_query_embedding(query_text)
        if query_embedding is None:
            return None
        
        # 默认权重设置
        if field_weights is None:
            field_weights = {
                "商品名称_embedding": 2.5,
                "简介_embedding": 2.0,
                "类别_embedding": 1.0,
                "详细参数_embedding": 1.5
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
    
    def hybrid_multi_embedding_search(self, query_text, field_weights=None, text_weight=0.7, vector_weight=0.3, size=10, price_range=None, category_filter=None):
        """
        混合搜索：结合文本搜索和多embedding向量搜索
        
        Args:
            query_text (str): 查询文本
            field_weights (dict): embedding字段权重
            text_weight (float): 文本搜索权重
            vector_weight (float): 向量搜索权重
            size (int): 返回结果数量
            price_range (dict): 价格范围过滤 {"gte": min_price, "lte": max_price}
            category_filter (str or list): 类别过滤
            
        Returns:
            dict: 搜索结果
        """
        # 生成查询向量
        query_embedding = self.generate_query_embedding(query_text)
        if query_embedding is None:
            return None
        
        # 默认权重设置
        if field_weights is None:
            field_weights = {
                "商品名称_embedding": 5,
                "简介_embedding": 1.0,
                "类别_embedding": 1.0,
                "详细参数_embedding": 1.5
            }
        
        # 构建查询
        should_queries = []
        
        # 添加文本搜索
        text_fields = ["商品名称^2.0", "简介^1.5", "详细参数_文本^1.2", "类别"]
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
        
        # 构建完整查询体
        search_body = {
            "query": {
                "bool": {
                    "should": should_queries
                }
            },
            "size": size
        }
        
        # 添加过滤条件
        filter_queries = []
        
        # 价格范围过滤
        if price_range:
            filter_queries.append({
                "range": {
                    "价格": price_range
                }
            })
        
        # 类别过滤
        if category_filter:
            if isinstance(category_filter, list):
                filter_queries.append({
                    "terms": {
                        "类别": category_filter
                    }
                })
            else:
                filter_queries.append({
                    "term": {
                        "类别": category_filter
                    }
                })
        
        if filter_queries:
            search_body["query"]["bool"]["filter"] = filter_queries
        
        try:
            response = self.es.search(index=self.index_name, body=search_body)
            return self.format_results(response, query_text, field_weights, hybrid=True)
        except Exception as e:
            print(f"混合多embedding搜索出错: {e}")
            return None
    
    def find_similar_products(self, product_name, embedding_field="简介_embedding", size=10, exclude_self=True):
        """
        根据指定embedding字段找到最相似的产品
        
        Args:
            product_name (str): 产品名称
            embedding_field (str): 用于比较的embedding字段
            size (int): 返回结果数量
            exclude_self (bool): 是否排除自身
            
        Returns:
            dict: 搜索结果
        """
        if embedding_field not in self.embedding_fields:
            print(f"无效的embedding字段: {embedding_field}")
            return None
        
        # 首先获取该产品的指定embedding
        get_product_body = {
            "query": {
                "match": {
                    "商品名称": product_name
                }
            },
            "size": 1
        }
        
        try:
            response = self.es.search(index=self.index_name, body=get_product_body)
            if response['hits']['total']['value'] == 0:
                print(f"未找到产品: {product_name}")
                return None
            
            product_embedding = response['hits']['hits'][0]['_source'].get(embedding_field)
            if product_embedding is None:
                print(f"产品 {product_name} 没有 {embedding_field}")
                return None
            
            # 使用该产品的embedding查找相似产品
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
                                "query_vector": product_embedding
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
                                "商品名称.keyword": product_name
                            }
                        }
                    }
                }
            
            response = self.es.search(index=self.index_name, body=search_body)
            return self.format_results(response, f"与{product_name}在{embedding_field}字段最相似的产品")
            
        except Exception as e:
            print(f"查找最相似产品出错: {e}")
            return None
    
    def search_by_category(self, category, size=20):
        """
        按类别搜索产品
        
        Args:
            category (str): 类别名称
            size (int): 返回结果数量
            
        Returns:
            dict: 搜索结果
        """
        search_body = {
            "query": {
                "term": {
                    "类别": category
                }
            },
            "size": size,
            "sort": [
                {"价格": {"order": "asc"}}
            ],
            "track_scores": True  # 即使排序也计算评分
        }
        
        try:
            response = self.es.search(index=self.index_name, body=search_body)
            return self.format_results(response, f"类别为 {category} 的产品")
        except Exception as e:
            print(f"按类别搜索出错: {e}")
            return None
    
    def search_by_price_range(self, min_price=None, max_price=None, size=20):
        """
        按价格范围搜索产品
        
        Args:
            min_price (float): 最低价格
            max_price (float): 最高价格
            size (int): 返回结果数量
            
        Returns:
            dict: 搜索结果
        """
        price_range = {}
        if min_price is not None:
            price_range["gte"] = min_price
        if max_price is not None:
            price_range["lte"] = max_price
        
        search_body = {
            "query": {
                "range": {
                    "价格": price_range
                }
            },
            "size": size,
            "sort": [
                {"价格": {"order": "asc"}}
            ],
            "track_scores": True  # 即使排序也计算评分
        }
        
        try:
            response = self.es.search(index=self.index_name, body=search_body)
            price_desc = f"{min_price or '0'}元 - {max_price or '无上限'}元"
            return self.format_results(response, f"价格范围 {price_desc} 的产品")
        except Exception as e:
            print(f"按价格搜索出错: {e}")
            return None
    
    def get_category_stats(self):
        """
        获取各类别的统计信息
        
        Returns:
            dict: 类别统计
        """
        search_body = {
            "size": 0,
            "aggs": {
                "categories": {
                    "terms": {
                        "field": "类别",
                        "size": 100
                    },
                    "aggs": {
                        "avg_price": {
                            "avg": {
                                "field": "价格"
                            }
                        },
                        "min_price": {
                            "min": {
                                "field": "价格"
                            }
                        },
                        "max_price": {
                            "max": {
                                "field": "价格"
                            }
                        }
                    }
                }
            }
        }
        
        try:
            response = self.es.search(index=self.index_name, body=search_body)
            return response['aggregations']['categories']['buckets']
        except Exception as e:
            print(f"获取类别统计出错: {e}")
            return None

    def search_by_cmd(self,query_text,search_body):
        response = self.es.search(index=self.index_name, body=search_body)
        return self.format_results(response, query_text)

    def format_results(self, response, query_info="", field_weights=None, hybrid=False):
        """
        格式化搜索结果为字符串
        
        Args:
            response: Elasticsearch响应
            query_info (str): 查询信息
            field_weights (dict): 字段权重信息
            hybrid (bool): 是否为混合搜索
            
        Returns:
            str: 格式化的结果字符串
        """
        total_hits = response['hits']['total']['value']
        
        if total_hits == 0:
            return f"未找到相关产品。查询信息：{query_info}"
        
        # 构建结果字符串
        result_lines = []
        # result_lines.append(f"查询：{query_info}")
        # result_lines.append(f"找到 {total_hits} 条结果")
        #
        # if hybrid:
        #     result_lines.append("搜索类型：混合搜索（文本+向量）")
        
        # if field_weights:
        #     weights_str = ", ".join([f"{k}: {v}" for k, v in field_weights.items()])
        #     result_lines.append(f"字段权重：{weights_str}")
        
        # result_lines.append("=" * 80)
        
        for i, hit in enumerate(response['hits']['hits'], 1):
            source = hit['_source']
            score = hit.get('_score')
            
            # 商品基本信息
            result_lines.append(f"\n{i}. {source.get('商品名称', '未知产品')}")
            
            # 类别和价格
            category = source.get('类别', '未分类')
            price = source.get('价格', None)
            price_str = f"¥{price}" if price is not None else "价格未知"
            score_str = f"{score:.3f}" if score is not None else "N/A"
            
            result_lines.append(f"   类别: {category} | 价格: {price_str} | 评分: {score_str}")
            
            # 简介
            intro = source.get('简介', '')
            if intro:
                intro_display = intro if len(intro) <= 150 else intro[:150] + "..."
                result_lines.append(f"   简介: {intro_display}")
            
            # 链接
            link = source.get('相关链接', '')
            if link:
                result_lines.append(f"   链接: {link}")
            
            # 详细参数（显示前5个）
            params = source.get('详细参数', {})
            if params and isinstance(params, dict):
                result_lines.append("   主要参数:")
                for key, value in list(params.items())[:5]:
                    result_lines.append(f"     • {key}: {value}")
            
            result_lines.append("-" * 80)
        
        return "\n".join(result_lines)
    
    def print_results(self, results, show_details=False):
        """
        打印搜索结果
        
        Args:
            results (dict): 搜索结果
            show_details (bool): 是否显示详细信息
        """
        if not results or not results.get('hits'):
            print("未找到结果")
            return
        
        print(f"\n查询: {results['query']}")
        print(f"找到 {results['total']} 条结果，耗时 {results['took']}ms")
        
        if results.get('field_weights'):
            print(f"字段权重: {results['field_weights']}")
        
        if results.get('is_hybrid'):
            print("搜索类型: 混合搜索（文本+向量）")
        
        print("\n" + "="*80)
        
        for i, hit in enumerate(results['hits'], 1):
            print(f"\n{i}. {hit['商品名称']}")
            价格显示 = f"¥{hit['价格']}" if hit['价格'] is not None else "价格未知"
            评分显示 = f"{hit['score']:.3f}" if hit['score'] is not None else "N/A"
            print(f"   类别: {hit['类别']} | 价格: {价格显示} | 评分: {评分显示}")
            print(f"   简介: {hit['简介'][:120]}...")
            
            if show_details:
                print(f"   链接: {hit['相关链接']}")
                if hit['详细参数']:
                    print("   详细参数:")
                    for key, value in list(hit['详细参数'].items())[:3]:
                        print(f"     - {key}: {value}")
            
            print("-" * 80)


def main():
    # 创建搜索器实例
    searcher = XiaomiProductSearch()
    
    print("="*80)
    print("小米产品搜索系统")
    print("="*80)
    
    # 1. 类别统计
    print("\n【类别统计】")
    stats = searcher.get_category_stats()
    if stats:
        print(f"共有 {len(stats)} 个类别:")
        for bucket in stats[:10]:
            avg_price = bucket['avg_price']['value']
            avg_price_str = f"¥{avg_price:.2f}" if avg_price is not None else "无价格信息"
            print(f"  - {bucket['key']}: {bucket['doc_count']}个产品, "
                  f"平均价格: {avg_price_str}")
    
    # 2. 示例查询
    print("\n\n" + "="*80)
    print("【示例查询】")
    print("="*80)
    
    queries = [
        "小米15价格",
        "适合商务出行的背包",
        "智能家居设备",
        "运动健康监测"
    ]
    
    for query in queries:
        print(f"\n\n查询: {query}")
        print("-" * 80)
        
        # 混合搜索
        results = searcher.hybrid_multi_embedding_search(query, size=3)


    # 3. 价格范围搜索
    print("\n\n" + "="*80)
    print("【价格范围搜索：100-500元】")
    print("="*80)
    price_results = searcher.search_by_price_range(min_price=100, max_price=500, size=5)
    searcher.print_results(price_results)
    
    # 4. 类别搜索
    print("\n\n" + "="*80)
    print("【类别搜索：智能穿戴】")
    print("="*80)
    category_results = searcher.search_by_category("智能穿戴", size=5)
    searcher.print_results(category_results)

searcher = XiaomiProductSearch()

if __name__ == "__main__":
    results = searcher.hybrid_multi_embedding_search("小米15的官方售价及各版本价格详情", size=3)
    print(results)
