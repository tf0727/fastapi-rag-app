# 多轮对话快速开始指南

## 🎯 修改内容总结

### 核心问题
原代码的 `ask_question()` 函数每次都创建新的消息列表，无法保持对话历史，导致多轮对话失败。

### 解决方案
1. **新增 `ConversationManager` 类**：维护对话历史
2. **修复所有工作流节点**：从固定索引改为动态查找消息
3. **改进答案生成逻辑**：自动提取并使用历史上下文
4. **🆕 新增问题补全功能**：根据历史自动补全用户输入的主谓宾（新增）

---

## 🚀 快速开始

### 基础用法（推荐）

```python
from src.agent.retriever8 import ConversationManager

# 1. 创建对话管理器（可选开启 verbose 模式查看问题补全效果）
conversation = ConversationManager(verbose=True)  # verbose=True 显示中间步骤

# 2. 开始对话
conversation.ask_question("小米15的价格多少？")

# 3. 追问（系统会自动理解"它"指的是"小米15"）
conversation.ask_question("它有哪些颜色？")
# 💡 问题补全：系统自动将"它"替换为"小米15"
# 📋 中间步骤会显示：[问题补全] 小米15有哪些颜色？

# 4. 继续追问（省略主语）
conversation.ask_question("内存配置有哪些？")
# 💡 问题补全：系统自动补全为"小米15的内存配置有哪些？"

# 5. 查看历史
conversation.show_history()

# 6. 清空历史，开始新话题
conversation.clear_history()
```

### 交互式模式

```python
from src.agent.retriever8 import ConversationManager

conversation = ConversationManager()

while True:
    user_input = input("请输入问题: ").strip()
    
    if user_input == 'quit':
        break
    elif user_input == 'clear':
        conversation.clear_history()
    elif user_input == 'history':
        conversation.show_history()
    else:
        conversation.ask_question(user_input)
```

---

## 📋 API 说明

### ConversationManager 类

#### 初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `verbose` | bool | False | 是否显示详细的中间步骤（包括问题补全、改写、路由等） |

#### 方法

| 方法 | 说明 | 参数 | 返回值 |
|------|------|------|--------|
| `ask_question(question)` | 提问并获取答案 | question: str | str (AI的回复) |
| `clear_history()` | 清空对话历史 | 无 | 无 |
| `show_history()` | 显示对话历史 | 无 | 无 |

#### 属性

| 属性 | 说明 | 类型 |
|------|------|------|
| `history` | 对话历史消息列表 | List[Message] |
| `verbose` | 是否显示详细步骤 | bool |

---

## 💻 运行演示

### 方式1：运行内置示例

```bash
cd E:\shoushixiaomi\demo\rag-xiaomi
python src\agent\retriever8.py
```

这将运行内置的多轮对话示例，包括：
- 产品价格查询
- 颜色追问
- 内存配置追问
- 公司信息查询

### 方式2：运行完整演示脚本

```bash
cd E:\shoushixiaomi\demo\rag-xiaomi
python demo_multi_turn.py
```

这将提供交互式菜单，可以选择不同的演示场景：
1. 产品咨询 - 多轮追问
2. 公司信息咨询 - 深入追问
3. 话题切换 - 从产品到公司
4. 交互式对话模式

---

## 🔍 核心技术改进

### 1. 🆕 问题补全（新增）

在工作流中新增 `query_completion` 节点，位于相关性判断之后、问题改写之前：

```python
# 工作流：
relevance_check → query_completion → rewrite → query_router → ...
                      👆 新增节点
```

**功能**：根据对话历史自动补全用户输入
```python
用户输入："它有哪些颜色？"
历史：上一轮讨论的是"小米15"
补全后："小米15有哪些颜色？"
```

### 2. 动态消息查找

**之前（有问题）：**
```python
rewritten_question = state["messages"][-2].content  # ❌ 固定索引
```

**现在（正确）：**
```python
# ✅ 通过 tool_call_id 动态查找
for msg in reversed(state["messages"]):
    if isinstance(msg, ToolMessage) and msg.tool_call_id == "rewrite_tool":
        rewritten_question = msg.content
        break
```

### 3. 历史上下文集成

答案生成时自动提取最近3轮对话作为上下文：

```python
# 构建历史上下文
history_context = "\n\n历史对话：\n"
recent_pairs = min(3, len(human_messages) - 1)
for i in range(...):
    history_context += f"- 用户: {human_messages[i][:100]}...\n"
    history_context += f"- AI: {ai_messages[i][:100]}...\n"
```

### 3. 智能消息管理

只保存用户问题和最终AI回复，不保存中间的工具消息：

```python
# 只保存 AIMessage
if isinstance(final_answer, AIMessage):
    self.history.append(final_answer)
```

---

## 📊 对话示例

### 示例1：产品追问

```
用户: 小米15的价格多少？
AI: 小米15的价格为4499元起...

用户: 它有哪些颜色？          👈 使用指代词
AI: 小米15有以下颜色可选：钛金属、岩石青...

用户: 内存配置呢？            👈 省略主语
AI: 小米15提供以下内存配置：
    - 12GB+256GB: 4499元
    - 12GB+512GB: 4799元
```

### 示例2：话题切换

```
用户: 小米SU7的价格？
AI: 小米SU7售价为...

[清空历史]

用户: 小米的ESG战略？         👈 新话题
AI: 小米集团的ESG战略包括...
```

---

## ⚙️ 配置选项

### 调整历史长度限制

在 `generate_answer_with_retriever()` 中修改：

```python
recent_pairs = min(3, len(human_messages) - 1)  # 默认保留3轮
```

### 调整历史显示长度

在 `show_history()` 中修改：

```python
print(f"{i+1}. [{role}]: {content[:100]}...")  # 显示前100个字符
```

---

## 🐛 常见问题

### Q1: 追问时无法理解上下文？

**检查**：
```python
conversation.show_history()  # 查看历史是否保存
```

**解决**：确保使用同一个 `ConversationManager` 实例

### Q2: 历史消息过多影响性能？

**解决**：定期清理
```python
if len(conversation.history) > 20:
    conversation.clear_history()
```

### Q3: 多个用户的对话如何隔离？

**解决**：为每个用户创建独立的实例
```python
user_sessions = {}
user_sessions[user_id] = ConversationManager()
```

---

## 📚 相关文档

- **详细说明**：`src/agent/MULTI_TURN_CONVERSATION_README.md`
- **🆕 问题补全功能**：`src/agent/QUERY_COMPLETION_FEATURE.md`（新增）
- **工作流文档**：`src/agent/RETRIEVER6_WORKFLOW.md`
- **源代码**：`src/agent/retriever8.py`
- **演示脚本**：`demo_multi_turn.py`

---

## ✅ 关键改进点

| 功能 | retriever7.py | retriever8.py |
|------|---------------|---------------|
| ✅ 多轮对话 | ❌ | ✅ |
| ✅ 历史管理 | ❌ | ✅ |
| ✅ 指代消解 | ❌ | ✅ |
| 🆕 问题补全 | ❌ | ✅（新增） |
| ✅ 动态消息查找 | ❌ (固定索引) | ✅ |
| ✅ 上下文感知 | ❌ | ✅ |
| 🆕 Verbose 模式 | ❌ | ✅（新增） |

---

## 🎓 下一步

1. **测试**：运行 `python demo_multi_turn.py` 体验功能
2. **集成**：在你的应用中使用 `ConversationManager`
3. **优化**：根据实际需求调整历史长度等参数
4. **扩展**：添加会话持久化、用户隔离等功能

---

**祝使用愉快！** 🎉

