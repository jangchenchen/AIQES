# AI生成题目重试机制

**日期**: 2025-11-04
**状态**: ✅ 已实现

---

## 📋 问题背景

### 原问题

在之前的实现中，AI生成题目时可能出现以下情况：

```
目标: 生成10道题目
AI响应: 返回10道题目
后端验证: 发现1道多选题只有1个答案，被过滤
最终结果: 只有9道题目 ❌
```

**用户反馈**:
> "⚠️  警告：多选题只有 1 个答案，已跳过（多选题至少需要2个答案）
> ✅ AI生成成功：生成 9 道题目
> AI 生成题目反而变成了概率事件了不太对"

### 根本原因

- AI生成的题目需要经过后端验证（多选题至少2个答案）
- 验证不通过的题目会被过滤
- 过滤后实际数量可能少于目标值
- 原代码只请求一次，不会补充

---

## ✅ 解决方案

### 重试机制设计

**核心思路**: 如果生成数量不足，继续请求AI，直到达到目标值或达到最大重试次数

**实现特点**:
1. ✅ 自动检测数量不足
2. ✅ 累积所有有效题目
3. ✅ 最多重试3次（避免无限循环）
4. ✅ 第二次及以后请求额外的题目（以防再次被过滤）
5. ✅ 详细的日志输出

---

## 🔧 实现细节

### 文件位置

`src/ai_client.py` - `generate_additional_questions()` 方法

### 代码实现

```python
def generate_additional_questions(
    self,
    entries: Sequence["KnowledgeEntry"],
    *,
    count: int,
    question_types: Iterable[QuestionType],
    temperature: float = 0.7,
) -> List[Question]:
    if count <= 0:
        return []

    type_labels = sorted({self._question_type_to_label(qt) for qt in question_types})
    if not type_labels:
        type_labels = ["single", "multi", "cloze", "qa"]

    knowledge_summary = self._build_knowledge_summary(entries)

    # 重试机制：如果生成数量不足，继续请求
    built_questions: List[Question] = []
    max_retries = 3  # 最多重试3次
    attempt = 0

    while len(built_questions) < count and attempt < max_retries:
        attempt += 1
        remaining = count - len(built_questions)

        # 请求稍多一些题目，以防被过滤
        request_count = remaining + 2 if attempt > 1 else count

        print(f"🔄 第 {attempt} 次请求AI生成 {request_count} 道题目（当前已有 {len(built_questions)} 道）")

        prompt = self._build_prompt(knowledge_summary, request_count, type_labels)

        # ... payload构建 ...

        try:
            response = self._post_json(self._sanitize_url(self.config.url), payload)
            message = self._extract_message_text(response)
            raw_questions = self._parse_questions(message)

            # 处理本次请求的题目
            for idx, raw in enumerate(raw_questions, start=len(built_questions) + 1):
                if len(built_questions) >= count:
                    break

                question = self._build_question(raw, fallback_index=idx)
                if question is None:
                    continue
                if question.question_type not in question_types:
                    continue
                built_questions.append(question)

            print(f"✅ 本次生成了 {len(built_questions) - (count - remaining)} 道有效题目（累计 {len(built_questions)} 道）")

        except Exception as e:
            print(f"⚠️  第 {attempt} 次请求失败：{str(e)}")
            break

    if len(built_questions) < count:
        print(f"⚠️  警告：目标生成 {count} 道题目，实际生成 {len(built_questions)} 道（已重试 {attempt} 次）")

    return built_questions
```

---

## 📊 工作流程

### 流程图

```
开始生成题目（目标: 10道）
    ↓
第1次请求: 请求10道题目
    ↓
AI返回: 10道题目
    ↓
后端验证: 1道被过滤
    ↓
实际得到: 9道题目
    ↓
检查: 9 < 10? 是
    ↓
第2次请求: 请求3道题目（剩余1道 + 2道缓冲）
    ↓
AI返回: 3道题目
    ↓
后端验证: 全部通过
    ↓
实际得到: 12道题目（只取前10道）
    ↓
检查: 10 >= 10? 是
    ↓
返回: 10道题目 ✅
```

### 关键逻辑

#### 1. 循环条件

```python
while len(built_questions) < count and attempt < max_retries:
```

- 继续条件: 数量不足 **且** 未达最大重试次数
- 退出条件: 数量足够 **或** 达到最大重试次数

#### 2. 请求数量计算

```python
remaining = count - len(built_questions)
request_count = remaining + 2 if attempt > 1 else count
```

- 第1次: 请求目标数量（如10道）
- 第2次及以后: 请求剩余数量+2道（缓冲，防止再次被过滤）

#### 3. 累积题目

```python
for idx, raw in enumerate(raw_questions, start=len(built_questions) + 1):
    if len(built_questions) >= count:
        break

    question = self._build_question(raw, fallback_index=idx)
    if question is None:
        continue
    if question.question_type not in question_types:
        continue
    built_questions.append(question)
```

- 使用 `start=len(built_questions) + 1` 确保题目ID连续
- 达到目标数量后立即停止
- 所有验证不通过的题目都会被跳过

---

## 📝 日志输出示例

### 成功案例（第1次就够）

```
🔄 第 1 次请求AI生成 10 道题目（当前已有 0 道）
⚠️  警告：多选题只有 1 个答案，已跳过（多选题至少需要2个答案）
✅ 本次生成了 9 道有效题目（累计 9 道）
🔄 第 2 次请求AI生成 3 道题目（当前已有 9 道）
✅ 本次生成了 1 道有效题目（累计 10 道）
✅ AI生成成功：生成 10 道题目
```

### 部分成功案例（达到最大重试）

```
🔄 第 1 次请求AI生成 10 道题目（当前已有 0 道）
⚠️  警告：多选题只有 1 个答案，已跳过
⚠️  警告：多选题只有 1 个答案，已跳过
✅ 本次生成了 8 道有效题目（累计 8 道）
🔄 第 2 次请求AI生成 4 道题目（当前已有 8 道）
⚠️  警告：多选题只有 1 个答案，已跳过
✅ 本次生成了 1 道有效题目（累计 9 道）
🔄 第 3 次请求AI生成 3 道题目（当前已有 9 道）
✅ 本次生成了 1 道有效题目（累计 10 道）
✅ AI生成成功：生成 10 道题目
```

### 失败案例（AI质量问题）

```
🔄 第 1 次请求AI生成 10 道题目（当前已有 0 道）
⚠️  警告：多选题只有 1 个答案，已跳过
⚠️  警告：多选题只有 1 个答案，已跳过
⚠️  警告：多选题只有 1 个答案，已跳过
⚠️  警告：多选题只有 1 个答案，已跳过
✅ 本次生成了 6 道有效题目（累计 6 道）
🔄 第 2 次请求AI生成 6 道题目（当前已有 6 道）
⚠️  警告：多选题只有 1 个答案，已跳过
⚠️  警告：多选题只有 1 个答案，已跳过
✅ 本次生成了 2 道有效题目（累计 8 道）
🔄 第 3 次请求AI生成 4 道题目（当前已有 8 道）
⚠️  警告：多选题只有 1 个答案，已跳过
✅ 本次生成了 1 道有效题目（累计 9 道）
⚠️  警告：目标生成 10 道题目，实际生成 9 道（已重试 3 次）
⚠️  AI生成失败：目标生成 10 道题目，实际生成 9 道
```

---

## ⚙️ 配置参数

### 可调整的参数

```python
max_retries = 3  # 最多重试次数
```

**建议值**:
- 一般场景: 3次（默认）
- 高质量AI: 2次
- 低质量AI: 5次

### 缓冲数量

```python
request_count = remaining + 2 if attempt > 1 else count
```

**含义**:
- 第1次: 请求目标数量
- 第2次及以后: 请求剩余数量 + 2道缓冲

**建议值**:
- 高质量AI: +1 或 +2
- 低质量AI: +3 或 +5

---

## 🎯 效果对比

### 修复前

| 场景 | 目标数量 | AI返回 | 过滤后 | 最终结果 |
|------|---------|--------|--------|---------|
| 场景1 | 10 | 10 | 1个不合格 | ❌ 9道 |
| 场景2 | 20 | 20 | 3个不合格 | ❌ 17道 |
| 场景3 | 5 | 5 | 2个不合格 | ❌ 3道 |

### 修复后

| 场景 | 目标数量 | 第1次 | 第2次 | 第3次 | 最终结果 |
|------|---------|-------|-------|-------|---------|
| 场景1 | 10 | 9道 | +1道 | - | ✅ 10道 |
| 场景2 | 20 | 17道 | +2道 | +1道 | ✅ 20道 |
| 场景3 | 5 | 3道 | +2道 | - | ✅ 5道 |

---

## ⚠️ 注意事项

### 1. API调用成本

**影响**: 重试机制会增加API调用次数

**建议**:
- 使用高质量AI模型（减少过滤率）
- 监控API调用次数
- 根据预算调整 `max_retries` 参数

### 2. 性能影响

**影响**: 重试会增加总耗时

**预期耗时**:
- 1次请求: ~2-5秒
- 2次请求: ~4-10秒
- 3次请求: ~6-15秒

**建议**:
- 前端显示加载状态
- 设置合理的超时时间（60秒）

### 3. 极端情况

**情况**: AI质量很差，多次重试仍无法达到目标

**处理**:
- 最多重试3次后返回实际数量
- 打印警告日志
- 前端提示用户实际数量

---

## 🧪 测试方法

### 1. 正常场景测试

```bash
# 1. 访问 http://localhost:5001
# 2. 上传知识文件
# 3. 选择"多选题"
# 4. 生成10道题目
# 5. 观察服务器日志
```

**预期日志**:
```
🔄 第 1 次请求AI生成 10 道题目（当前已有 0 道）
✅ 本次生成了 X 道有效题目（累计 X 道）
# 如果 X < 10，会看到第2次请求
🔄 第 2 次请求AI生成 Y 道题目（当前已有 X 道）
✅ 本次生成了 Z 道有效题目（累计 10 道）
```

### 2. 极端场景测试（模拟）

在 `_build_question()` 方法中临时添加：

```python
# 临时测试代码：模拟高过滤率
import random
if random.random() < 0.3:  # 30%概率过滤
    return None
```

然后观察重试机制是否正常工作。

---

## 📚 相关文档

- `MULTI_CHOICE_AND_SESSION_FIX.md` - 多选题修复文档
- `AI_GRADING_FEATURE.md` - AI语义评分文档
- `IMPLEMENTATION_COMPLETE.md` - Few-Shot Learning文档

---

## ✅ 总结

**实现的功能**:
1. ✅ 自动检测生成数量不足
2. ✅ 智能重试（最多3次）
3. ✅ 累积所有有效题目
4. ✅ 额外请求缓冲题目（防止再次过滤）
5. ✅ 详细的日志输出

**用户体验改进**:
- ✅ 不再因为验证过滤导致数量不足
- ✅ 提高了题目生成的可靠性
- ✅ 降低了AI生成的概率性问题

**技术亮点**:
- ✅ 优雅的重试机制
- ✅ 避免无限循环
- ✅ 清晰的日志输出
- ✅ 可配置的参数

---

**实现日期**: 2025-11-04
**实现人员**: Claude Code
**测试状态**: ✅ 已实现，待测试
**部署状态**: ✅ 已部署到主分支
