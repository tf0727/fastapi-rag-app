"""
测试智能 Elasticsearch 检索工具

这个脚本演示了新的 elasticsearch_retriever_tool 如何使用 LLM 智能分析用户查询
并自动选择最优的搜索策略
"""

from src.agent.retriever7 import elasticsearch_retriever_tool

def test_queries():
    """测试不同类型的查询"""
    
    test_cases = [
        {
            "name": "产品价格查询",
            "query": "小米14 Pro的价格是多少？",
            "expected": "应该使用混合搜索，重点关注产品名称"
        },
        {
            "name": "价格区间查询",
            "query": "2000元到5000元之间的手机有哪些？",
            "expected": "应该使用价格范围搜索"
        },
        {
            "name": "类别查询",
            "query": "智能穿戴设备有哪些？",
            "expected": "应该使用类别搜索"
        },
        {
            "name": "参数配置查询",
            "query": "哪些手机支持5G并且有高刷屏？",
            "expected": "应该使用混合搜索，提高参数字段权重"
        },
        {
            "name": "相似产品查询",
            "query": "有没有和小米14相似的产品？",
            "expected": "应该使用相似产品搜索"
        }
    ]
    
    print("="*100)
    print("智能 Elasticsearch 检索工具测试")
    print("="*100)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'='*100}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"{'='*100}")
        print(f"查询: {test_case['query']}")
        print(f"预期策略: {test_case['expected']}")
        print(f"{'-'*100}")
        
        try:
            # 调用智能检索工具
            result = elasticsearch_retriever_tool.invoke(test_case['query'])
            
            print("\n检索结果:")
            print(result)
            
        except Exception as e:
            print(f"错误: {e}")
        
        print(f"\n{'='*100}\n")

if __name__ == "__main__":
    test_queries()



