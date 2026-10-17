"""
多轮对话功能演示脚本

这个脚本演示了如何使用 ConversationManager 实现多轮对话
"""

import sys
import os

# 添加项目路径到 sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.agent.retriever8 import ConversationManager


def demo_product_inquiry():
    """演示产品咨询的多轮对话（带问题补全）"""
    print("\n" + "="*100)
    print("演示场景1：产品咨询 - 多轮追问（展示问题补全功能）")
    print("="*100)
    print("\n💡 本场景将展示问题补全功能：")
    print("   - 第2轮使用指代词'它'，系统会自动替换为'小米15'")
    print("   - 第3轮省略主语，系统会自动补全'小米15的'")
    print("   - 可以在【中间步骤】中看到补全后的问题")
    print("="*100)
    
    # 开启 verbose 模式以查看问题补全效果
    conversation = ConversationManager(verbose=True)
    
    # 第一轮：询问产品价格
    print("\n>>> 用户：小米15的价格多少？")
    conversation.ask_question("小米15的价格多少？")
    
    # 第二轮：追问颜色（使用指代词"它"）
    print("\n>>> 用户：它有哪些颜色可选？（使用指代词）")
    conversation.ask_question("它有哪些颜色可选？")
    
    # 第三轮：追问内存配置（省略主语）
    print("\n>>> 用户：内存配置有哪些？（省略主语）")
    conversation.ask_question("内存配置有哪些？")
    
    # 显示完整对话历史
    conversation.show_history()
    
    return conversation


def demo_company_inquiry():
    """演示公司信息咨询的多轮对话（带问题补全）"""
    print("\n" + "="*100)
    print("演示场景2：公司信息咨询 - 深入追问（展示问题补全功能）")
    print("="*100)
    print("\n💡 本场景将展示问题补全功能：")
    print("   - 第2轮省略主语'小米集团碳排放目标'")
    print("   - 第3轮使用指代词'这些'")
    print("   - 系统会根据历史自动补全完整问题")
    print("="*100)
    
    # 开启 verbose 模式以查看问题补全效果
    conversation = ConversationManager(verbose=True)
    
    # 第一轮：询问碳排放目标
    print("\n>>> 用户：小米集团在2024年的碳排放目标是什么？")
    conversation.ask_question("小米集团在2024年的碳排放目标是什么？")
    
    # 第二轮：追问具体措施（省略主语）
    print("\n>>> 用户：具体采取了哪些措施？（省略主语）")
    conversation.ask_question("具体采取了哪些措施？")
    
    # 第三轮：追问效果（使用指代词"这些"）
    print("\n>>> 用户：效果如何？（简短追问）")
    conversation.ask_question("效果如何？")
    
    # 显示完整对话历史
    conversation.show_history()
    
    return conversation


def demo_topic_switch():
    """演示话题切换"""
    print("\n" + "="*100)
    print("演示场景3：话题切换 - 从产品到公司")
    print("="*100)
    
    conversation = ConversationManager()
    
    # 第一个话题：产品
    print("\n>>> 用户：小米手环的价格是多少？")
    conversation.ask_question("小米手环的价格是多少？")
    
    print("\n>>> 用户：它有什么功能？")
    conversation.ask_question("它有什么功能？")
    
    # 显示当前历史
    print("\n【当前对话历史】")
    conversation.show_history()
    
    # 清空历史，切换话题
    print("\n>>> 【清空历史，切换话题】")
    conversation.clear_history()
    
    # 第二个话题：公司信息
    print("\n>>> 用户：小米集团的ESG战略是什么？")
    conversation.ask_question("小米集团的ESG战略是什么？")
    
    # 显示新话题的历史
    print("\n【新话题的对话历史】")
    conversation.show_history()
    
    return conversation


def demo_interactive_mode():
    """演示交互式对话模式"""
    print("\n" + "="*100)
    print("演示场景4：交互式对话模式")
    print("="*100)
    print("\n命令说明：")
    print("  - 输入问题：进行对话")
    print("  - 'quit' 或 'exit'：退出")
    print("  - 'clear'：清空历史")
    print("  - 'history'：查看历史")
    print("="*100)
    
    conversation = ConversationManager()
    
    while True:
        try:
            user_input = input("\n>>> 用户: ").strip()
            
            if not user_input:
                print("请输入有效的问题")
                continue
            
            if user_input.lower() in ['quit', 'exit']:
                print("\n感谢使用，再见！")
                break
            
            elif user_input.lower() == 'clear':
                conversation.clear_history()
                continue
            
            elif user_input.lower() == 'history':
                conversation.show_history()
                continue
            
            else:
                conversation.ask_question(user_input)
        
        except KeyboardInterrupt:
            print("\n\n对话被中断，正在退出...")
            break
        
        except Exception as e:
            print(f"\n发生错误：{str(e)}")
            print("请重试或输入 'quit' 退出")


def main():
    """主函数：运行所有演示场景"""
    print("\n" + "="*100)
    print("多轮对话功能演示")
    print("="*100)
    print("\n本演示包含以下场景：")
    print("1. 产品咨询 - 多轮追问")
    print("2. 公司信息咨询 - 深入追问")
    print("3. 话题切换 - 从产品到公司")
    print("4. 交互式对话模式")
    print("\n选择演示场景（输入数字 1-4，或 'all' 运行所有场景）：")
    
    choice = input(">>> ").strip()
    
    if choice == '1':
        demo_product_inquiry()
    
    elif choice == '2':
        demo_company_inquiry()
    
    elif choice == '3':
        demo_topic_switch()
    
    elif choice == '4':
        demo_interactive_mode()
    
    elif choice.lower() == 'all':
        demo_product_inquiry()
        input("\n按回车继续下一个场景...")
        
        demo_company_inquiry()
        input("\n按回车继续下一个场景...")
        
        demo_topic_switch()
        input("\n按回车进入交互式模式（输入 'quit' 可跳过）...")
        
        demo_interactive_mode()
    
    else:
        print("无效的选择，请重新运行脚本")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程序被中断")
    except Exception as e:
        print(f"\n程序发生错误：{str(e)}")
        import traceback
        traceback.print_exc()

