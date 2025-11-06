# 参数简化 - AI 生成逻辑优化

## 更新日期
2025-11-04

## 问题背景

用户反馈题目配置界面的参数设计不合理：

**之前的设计：**
- ❌ "题目数量" - 本地生成的题目数量
- ❌ "AI 生成题目数量" - AI额外生成的数量
- ❌ 总题目 = 两者相加

**存在的问题：**
1. 用户需要理解两个来源的区别
2. 概念复杂，增加认知负担
3. 对于已上传题目的场景，"AI 生成"概念不清晰
4. 需要手动计算总题目数量

## 优化方案

### 新设计

✅ **单一"题目数量"参数** - 用户想做多少题就填多少
✅ **"使用 AI 增强"复选框** - 题目不足时自动补充

### 核心逻辑

```python
# 1. 优先本地生成题目
questions = generator.generate_questions(...)

# 2. 如果启用AI且本地题目不足，自动补充
if use_ai and len(questions) < count:
    ai_needed = count - len(questions)
    ai_questions = ai_client.generate_additional_questions(count=ai_needed)
    questions.extend(ai_questions)

# 3. 最终截取用户要求的数量
questions = questions[:count]
```

## 详细改动

### 1. 前端界面 (`frontend/app.html`)

#### 之前
```html
<div class="form-group">
  <label class="form-label">题目数量</label>
  <input type="number" id="question-count" value="10" />
</div>

<div class="form-group">
  <label class="form-label">AI 生成题目数量（可选）</label>
  <input type="number" id="ai-count" value="0" />
  <div class="form-hint">需要在 AI 配置中设置 API</div>
</div>
```

#### 现在
```html
<div class="form-group">
  <label class="form-label">题目数量</label>
  <input type="number" id="question-count" value="10" min="1" max="100" />
</div>

<div class="form-group">
  <label class="checkbox-item">
    <input type="checkbox" id="use-ai" />
    <span>使用 AI 增强（题目不足时自动补充）</span>
  </label>
  <div class="form-hint">需要在 AI 配置中设置 API</div>
</div>
```

### 2. 前端逻辑 (`frontend/assets/app.js`)

#### 之前
```javascript
const count = parseInt(document.getElementById('question-count').value);
const aiCount = parseInt(document.getElementById('ai-count').value);

fetch(API_BASE + '/generate-questions', {
  body: JSON.stringify({
    count,
    ai_count: aiCount,
    ...
  })
})
```

#### 现在
```javascript
const count = parseInt(document.getElementById('question-count').value);
const useAI = document.getElementById('use-ai').checked;

fetch(API_BASE + '/generate-questions', {
  body: JSON.stringify({
    count,
    use_ai: useAI,
    ...
  })
})
```

### 3. 后端逻辑 (`web_server.py`)

#### 之前
```python
count = data.get('count', 10)
ai_count = data.get('ai_count', 0)

# 生成本地题目
questions = generator.generate_questions(...)

# AI 生成额外题目
if ai_count > 0:
    ai_questions = ai_client.generate_additional_questions(count=ai_count)
    questions.extend(ai_questions)

# 截取 count 数量
questions = questions[:count]
```

#### 现在
```python
count = data.get('count', 10)
use_ai = data.get('use_ai', False)

# 优先本地生成题目
questions = generator.generate_questions(...)

# 如果启用AI且本地题目不足，用AI补充
local_count = len(questions)
if use_ai and local_count < count:
    ai_needed = count - local_count
    ai_questions = ai_client.generate_additional_questions(count=ai_needed)
    questions.extend(ai_questions)

# 截取 count 数量
questions = questions[:count]
```

### 4. AI 提示词优化 (`src/ai_client.py`)

同步优化了 AI 的系统提示词，明确角色定位：

```python
"你是答题考试系统的助手，帮助教育工作者将内容数字化。\n\n"
"教育工作者会上传以下类型的文本：\n"
"1. 已经拟定好的题目和答案 - **直接识别并提取**\n"
"2. 知识纲要/教材内容 - 基于内容辅助生成题目\n\n"
"**优先级**：如果文本中包含现成的题目和答案，直接提取使用。"
```

## 用户体验提升

### 之前的用户流程

1. 上传知识文件
2. 选择题型
3. ❌ **思考**：我要 15 道题，本地有多少？要AI生成几道？
4. ❌ **计算**：本地可能 10 道，AI 生成 5 道
5. ❌ **填写**：题目数量 = 10，AI 数量 = 5
6. ❌ **困惑**：如果本地题目不足 10 道怎么办？

### 现在的用户流程

1. 上传知识文件
2. 选择题型
3. ✅ **直接填写**：题目数量 = 15
4. ✅ **勾选**："使用 AI 增强"（如果需要）
5. ✅ **系统自动处理**：本地不足时AI自动补充

## 逻辑对比表

| 场景 | 本地题目 | 用户设置 | 之前结果 | 现在结果 |
|------|---------|---------|---------|---------|
| 本地充足 | 20 道 | 需要 10 道 | 10 道（本地） | 10 道（本地） ✅ |
| 本地不足（启用AI） | 5 道 | 需要 10 道 + AI增强 | 5 道（用户需手动计算） ❌ | 10 道（5 本地 + 5 AI） ✅ |
| 本地不足（不启用AI） | 5 道 | 需要 10 道 | 5 道（不足） ❌ | 5 道（本地全部） ✅ |
| 已有题目 | 15 道 | 需要 15 道 | 15 道 | 15 道（直接提取） ✅ |

## 兼容性说明

### API 向后兼容

新版后端仍然接受旧参数 `ai_count`（虽然前端不再发送）：

```python
# 旧客户端（仍然可用）
{
  "count": 10,
  "ai_count": 5  # 会被忽略
}

# 新客户端
{
  "count": 15,
  "use_ai": true
}
```

### 数据迁移

不需要数据迁移，只是逻辑调整。

## 测试场景

### 场景 1：本地题目充足
```
输入：知识文件（20 道题）
配置：题目数量 = 10
结果：返回 10 道本地题目
```

### 场景 2：本地不足 + 启用 AI
```
输入：知识文件（5 道题）
配置：题目数量 = 10，启用 AI 增强
结果：5 道本地 + 5 道 AI = 10 道总计
```

### 场景 3：本地不足 + 未启用 AI
```
输入：知识文件（5 道题）
配置：题目数量 = 10，不启用 AI
结果：返回 5 道本地题目（全部可用）
```

### 场景 4：已有题目文本
```
输入：测验题目和答案文本
配置：题目数量 = 5，启用 AI
结果：直接提取 5 道现成题目（AI 识别并提取）
```

## 文件变更摘要

```
修改文件：
  frontend/app.html (159 行)
    - 移除 "AI 生成数量" 输入框
    + 添加 "使用 AI 增强" 复选框

  frontend/assets/app.js
    - 移除 aiCount 变量
    + 添加 useAI 布尔值
    - 发送 ai_count 参数
    + 发送 use_ai 参数

  web_server.py (generate_questions 函数)
    - 移除 ai_count 参数处理
    + 添加 use_ai 参数处理
    - 无条件调用 AI（如果 ai_count > 0）
    + 智能调用 AI（仅在需要补充时）

  src/ai_client.py
    + 优化系统提示词
    + 明确角色定位（教育数字化助手）
    + 优先提取现成题目

新增文档：
  PARAMETER_SIMPLIFICATION.md - 本文档
```

## 优势总结

### 用户体验
1. ✅ **更简单** - 只需填写想要的题目总数
2. ✅ **更直观** - 复选框清楚表达"AI 增强"功能
3. ✅ **更智能** - 系统自动计算 AI 补充数量
4. ✅ **更灵活** - 适配已有题目和知识纲要两种场景

### 系统设计
1. ✅ **更合理** - 符合"总数优先"的用户心智模型
2. ✅ **更高效** - 避免不必要的 AI 调用
3. ✅ **更清晰** - 代码逻辑更易理解
4. ✅ **更专业** - 符合教育数字化工具的定位

### 成本优化
1. ✅ **AI 调用优化** - 仅在真正需要时调用
2. ✅ **Token 节省** - 按需补充，不浪费
3. ✅ **响应更快** - 减少不必要的 AI 请求

## 未来扩展

### 可选功能（未实现）

#### 1. 自动检测模式
```
如果勾选"自动模式"：
- 系统自动判断是否需要AI
- 无需用户手动勾选
```

#### 2. AI 生成比例控制
```
滑块：AI 生成占比 0% - 100%
- 0%：纯本地
- 50%：一半本地一半AI
- 100%：纯AI生成
```

#### 3. 智能推荐
```
系统提示："检测到本地题目仅 5 道，建议启用 AI 增强"
```

## 总结

通过这次优化：

✅ **用户无需理解**"本地题目"和"AI 题目"的区别
✅ **系统自动处理**题目来源分配
✅ **符合直觉**的"总数优先"设计
✅ **适配多种场景**：知识纲要、已有题目、混合模式

这是一次以**用户为中心**的设计优化，大幅降低了使用门槛！

---

**更新时间**：2025-11-04
**影响范围**：前端界面、API 参数、后端逻辑
**兼容性**：向后兼容（旧参数被忽略）
**测试状态**：✅ 已通过手动测试
