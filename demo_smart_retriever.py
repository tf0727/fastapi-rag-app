"""
快速演示智能 Elasticsearch 检索工具

运行这个脚本来测试升级后的检索功能
"""

from src.agent.retriever7 import ask_question

def main():
    print("\n" + "="*100)
    print("智能 Elasticsearch 检索工具 - 快速演示")
    print("="*100)
    
    # 定义测试案例
    test_cases = [
        {
            "title": "测试 1：产品参数查询（混合搜索）",
            "question": "小米14 Pro的处理器配置如何？",
            "description": "预期：使用混合搜索，提高产品名称和参数权重"
        },
        {
            "title": "测试 2：价格区间查询（价格范围搜索）",
            "question": "3000到6000元之间的手机推荐",
            "description": "预期：使用价格范围搜索，过滤指定价格区间"
        },
        {
            "title": "测试 3：类别查询（类别搜索）",
            "question": "给我看看智能穿戴类别的产品",
            "description": "预期：使用类别精确搜索"
        },
        {
            "title": "测试 4：相似产品查询（相似度搜索）",
            "question": "有没有和小米15相似的其他产品？",
            "description": "预期：使用相似产品搜索"
        }
    ]
    
    # 执行测试
    for i, test in enumerate(test_cases, 1):
        print(f"\n\n{'#'*100}")
        print(f"# {test['title']}")
        print(f"{'#'*100}")
        print(f"\n说明: {test['description']}")
        print(f"\n问题: {test['question']}")
        print(f"\n{'-'*100}")
        
        try:
            # 调用智能问答系统
            ask_question(test['question'])
            
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}")
        
        # 询问是否继续
        if i < len(test_cases):
            user_input = input("\n按 Enter 继续下一个测试，输入 'q' 退出: ")
            if user_input.lower() == 'q':
                print("\n测试已终止")
                break
    
    print("\n" + "="*100)
    print("演示完成！")
    print("="*100)

if __name__ == "__main__":
    main()



