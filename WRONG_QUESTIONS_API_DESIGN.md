# 错题功能 API 设计方案

## 📋 目录
1. [需求分析](#需求分析)
2. [API 端点设计](#api-端点设计)
3. [数据结构](#数据结构)
4. [实现方案](#实现方案)
5. [前端集成](#前端集成)
6. [开发优先级](#开发优先级)

---

## 需求分析

### 当前状态
- ✅ CLI 模式下已实现错题记录
- ✅ `RecordManager` 类提供底层错题管理
- ✅ 数据存储：`data/wrong_questions.json`
- ❌ Web 模式无错题功能接口
- ❌ 前端无法查看/复练错题

### 功能需求
1. **查询错题**：获取错题列表、分页、筛选
2. **复练错题**：创建错题专项练习会话
3. **错题管理**：删除单题、清空错题本
4. **统计分析**：错题率、题型分布、知识点弱项

---

## API 端点设计

### 1. 获取错题列表
```
GET /api/wrong-questions
```

**Query Parameters**:
```json
{
  "page": 1,              // 页码（可选，默认 1）
  "page_size": 20,        // 每页数量（可选，默认 20）
  "question_type": "SINGLE_CHOICE",  // 题型筛选（可选）
  "sort_by": "last_wrong_at",  // 排序字段（可选：last_wrong_at, identifier）
  "order": "desc"         // 排序方向（可选：asc, desc）
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "questions": [
      {
        "identifier": "限速器-SC-2",
        "question_type": "SINGLE_CHOICE",
        "prompt": "关于限速器，以下哪项描述是正确的？",
        "options": ["选项A", "选项B", "选项C", "选项D"],
        "correct_options": [0],
        "answer_text": "校验周期...",
        "explanation": "检查要点：...",
        "keywords": [],
        "last_plain_explanation": "✗ 回答错误...",
        "last_wrong_at": "2025-11-03T17:55:38Z",
        "wrong_count": 3  // 累计答错次数
      }
    ],
    "pagination": {
      "total": 45,
      "page": 1,
      "page_size": 20,
      "total_pages": 3
    }
  }
}
```

---

### 2. 获取错题统计
```
GET /api/wrong-questions/stats
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "total_wrong": 45,
    "by_type": {
      "SINGLE_CHOICE": 20,
      "MULTI_CHOICE": 15,
      "CLOZE": 5,
      "QA": 5
    },
    "recent_wrong": 12,  // 最近7天新增
    "avg_wrong_rate": 0.35,  // 平均错误率（需要从 answer_history 计算）
    "weakest_topics": [  // 错误最多的知识点（从 identifier 提取）
      {"topic": "限速器", "count": 8},
      {"topic": "安全钳", "count": 6}
    ]
  }
}
```

---

### 3. 创建错题复练会话
```
POST /api/wrong-questions/practice
```

**Request Body**:
```json
{
  "question_types": ["SINGLE_CHOICE", "MULTI_CHOICE"],  // 可选，筛选题型
  "count": 10,         // 可选，限制题数
  "mode": "random"     // 可选：sequential, random（默认 random）
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "session_id": "uuid-here",
  "total_count": 10,
  "question_types": ["SINGLE_CHOICE", "MULTI_CHOICE"],
  "mode": "wrong_question_practice"  // 标识为错题练习模式
}
```

**说明**：
- 返回标准的会话 ID
- 后续使用现有的 `/api/get-question` 和 `/api/submit-answer` 接口
- 答对的题会自动从错题本移除（已实现）

---

### 4. 删除单个错题
```
DELETE /api/wrong-questions/{identifier}
```

**Path Parameter**:
- `identifier`: 题目唯一标识符

**Response** (200 OK):
```json
{
  "success": true,
  "message": "错题已删除"
}
```

**Response** (404 Not Found):
```json
{
  "success": false,
  "error": "题目不存在"
}
```

---

### 5. 清空错题本
```
DELETE /api/wrong-questions
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "已清空错题本",
  "deleted_count": 45
}
```

---

### 6. 获取单个错题详情
```
GET /api/wrong-questions/{identifier}
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "identifier": "限速器-SC-2",
    "question": { /* 完整题目信息 */ },
    "last_plain_explanation": "✗ 回答错误...",
    "last_wrong_at": "2025-11-03T17:55:38Z",
    "wrong_history": [  // 历史错误记录（从 answer_history.jsonl 提取）
      {
        "timestamp": "2025-11-03T15:30:00Z",
        "user_answer": "B",
        "session_id": "uuid-1"
      },
      {
        "timestamp": "2025-11-03T17:55:38Z",
        "user_answer": "C",
        "session_id": "uuid-2"
      }
    ],
    "wrong_count": 2
  }
}
```

---

## 数据结构

### 错题本数据结构（现有）

文件：`data/wrong_questions.json`

```json
[
  {
    "question": {
      "identifier": "限速器-SC-2",
      "question_type": "SINGLE_CHOICE",
      "prompt": "...",
      "options": [...],
      "correct_options": [0],
      "answer_text": "...",
      "explanation": "...",
      "keywords": []
    },
    "last_plain_explanation": "✗ 回答错误。正确答案是 A 选项，你选择了 B。",
    "last_wrong_at": "2025-11-03T17:55:38Z"
  }
]
```

### 扩展数据结构（建议）

为了支持更丰富的功能，建议扩展为：

```json
[
  {
    "question": { /* 题目对象 */ },
    "last_plain_explanation": "...",
    "last_wrong_at": "2025-11-03T17:55:38Z",
    "wrong_count": 3,           // 新增：累计答错次数
    "first_wrong_at": "2025-11-01T10:00:00Z",  // 新增：首次答错时间
    "tags": ["限速器", "校验周期"],  // 新增：知识点标签
    "difficulty": "medium"      // 新增：难度标记（可选）
  }
]
```

---

## 实现方案

### Phase 1: 基础 CRUD（优先级 HIGH）

#### 1. 扩展 `RecordManager` 类

文件：`src/record_manager.py`

```python
def get_wrong_questions_paginated(
    self,
    page: int = 1,
    page_size: int = 20,
    question_type: Optional[QuestionType] = None,
    sort_by: str = "last_wrong_at",
    order: str = "desc",
) -> Dict[str, Any]:
    """获取分页的错题列表"""
    entries = self._load_wrong_payloads()

    # 筛选题型
    if question_type:
        entries = [
            e for e in entries
            if e.get("question", {}).get("question_type") == question_type.name
        ]

    # 排序
    reverse = (order == "desc")
    if sort_by == "last_wrong_at":
        entries.sort(key=lambda x: x.get("last_wrong_at", ""), reverse=reverse)
    elif sort_by == "identifier":
        entries.sort(
            key=lambda x: x.get("question", {}).get("identifier", ""),
            reverse=reverse
        )

    # 分页
    total = len(entries)
    start = (page - 1) * page_size
    end = start + page_size
    page_entries = entries[start:end]

    return {
        "questions": page_entries,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    }

def get_wrong_question_stats(self) -> Dict[str, Any]:
    """获取错题统计信息"""
    entries = self._load_wrong_payloads()

    by_type = {}
    for entry in entries:
        q_type = entry.get("question", {}).get("question_type")
        by_type[q_type] = by_type.get(q_type, 0) + 1

    # 提取知识点（从 identifier 中提取）
    topics = {}
    for entry in entries:
        identifier = entry.get("question", {}).get("identifier", "")
        topic = identifier.split("-")[0] if "-" in identifier else "未分类"
        topics[topic] = topics.get(topic, 0) + 1

    weakest_topics = [
        {"topic": k, "count": v}
        for k, v in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        "total_wrong": len(entries),
        "by_type": by_type,
        "weakest_topics": weakest_topics,
    }

def get_wrong_question_detail(self, identifier: str) -> Optional[Dict[str, Any]]:
    """获取单个错题详情"""
    entries = self._load_wrong_payloads(as_dict=True)
    return entries.get(identifier)

def clear_all_wrong_questions(self) -> int:
    """清空错题本，返回删除数量"""
    entries = self._load_wrong_payloads()
    count = len(entries)
    if self.wrong_path.exists():
        self.wrong_path.unlink()
    return count
```

#### 2. 添加 Web API 端点

文件：`web_server.py`

```python
from src.record_manager import RecordManager

record_manager = RecordManager()  # 全局实例

# ============ 错题功能 API Routes ============

@app.route('/api/wrong-questions', methods=['GET'])
def get_wrong_questions():
    """获取错题列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        question_type_str = request.args.get('question_type')
        sort_by = request.args.get('sort_by', 'last_wrong_at')
        order = request.args.get('order', 'desc')

        question_type = None
        if question_type_str:
            try:
                question_type = QuestionType[question_type_str]
            except KeyError:
                return jsonify({"error": f"无效的题型: {question_type_str}"}), 400

        result = record_manager.get_wrong_questions_paginated(
            page=page,
            page_size=page_size,
            question_type=question_type,
            sort_by=sort_by,
            order=order,
        )

        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({"error": f"获取错题失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/stats', methods=['GET'])
def get_wrong_questions_stats():
    """获取错题统计"""
    try:
        stats = record_manager.get_wrong_question_stats()
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        return jsonify({"error": f"获取统计失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/practice', methods=['POST'])
def start_wrong_question_practice():
    """创建错题复练会话"""
    try:
        data = request.json or {}
        question_types = data.get('question_types', [])
        count = data.get('count')
        mode = data.get('mode', 'random')

        # 加载错题
        wrong_questions = record_manager.load_wrong_questions()

        if not wrong_questions:
            return jsonify({"error": "当前没有错题"}), 400

        # 筛选题型
        if question_types:
            type_filters = [QuestionType[t] for t in question_types if t in QuestionType.__members__]
            wrong_questions = [q for q in wrong_questions if q.question_type in type_filters]

        # 随机/顺序
        if mode == 'random':
            import random
            random.shuffle(wrong_questions)

        # 限制数量
        if count and count < len(wrong_questions):
            wrong_questions = wrong_questions[:count]

        # 创建会话
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "questions": wrong_questions,
            "current_index": 0,
            "answers": [],
            "correct_count": 0,
            "total_count": len(wrong_questions),
            "mode": "wrong_question_practice",  # 标识为错题练习
        }

        return jsonify({
            "success": True,
            "session_id": session_id,
            "total_count": len(wrong_questions),
            "question_types": list(set(q.question_type.name for q in wrong_questions)),
            "mode": "wrong_question_practice"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"创建练习失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/<identifier>', methods=['GET'])
def get_wrong_question_detail(identifier: str):
    """获取单个错题详情"""
    try:
        detail = record_manager.get_wrong_question_detail(identifier)
        if not detail:
            return jsonify({"error": "题目不存在"}), 404

        return jsonify({
            "success": True,
            "data": detail
        })
    except Exception as e:
        return jsonify({"error": f"获取详情失败：{str(e)}"}), 500


@app.route('/api/wrong-questions/<identifier>', methods=['DELETE'])
def delete_wrong_question(identifier: str):
    """删除单个错题"""
    try:
        record_manager.remove_wrong_question(identifier)
        return jsonify({
            "success": True,
            "message": "错题已删除"
        })
    except Exception as e:
        return jsonify({"error": f"删除失败：{str(e)}"}), 500


@app.route('/api/wrong-questions', methods=['DELETE'])
def clear_wrong_questions():
    """清空错题本"""
    try:
        count = record_manager.clear_all_wrong_questions()
        return jsonify({
            "success": True,
            "message": "已清空错题本",
            "deleted_count": count
        })
    except Exception as e:
        return jsonify({"error": f"清空失败：{str(e)}"}), 500
```

---

### Phase 2: 前端集成（优先级 MEDIUM）

#### 1. 错题本页面组件

文件：`frontend/wrong-questions.html`

**功能**：
- 显示错题列表（卡片式布局）
- 分页导航
- 题型筛选下拉菜单
- "开始复练"按钮
- 单题删除/清空按钮
- 统计数据展示（饼图/柱状图）

#### 2. 前端 API 调用

文件：`frontend/assets/wrong-questions.js`

```javascript
const API_BASE = 'http://localhost:5001/api';

// 获取错题列表
async function fetchWrongQuestions(page = 1, pageSize = 20, filters = {}) {
  const params = new URLSearchParams({
    page,
    page_size: pageSize,
    ...filters
  });

  const response = await fetch(`${API_BASE}/wrong-questions?${params}`);
  return await response.json();
}

// 开始错题复练
async function startWrongQuestionPractice(config = {}) {
  const response = await fetch(`${API_BASE}/wrong-questions/practice`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(config)
  });

  const result = await response.json();
  if (result.success) {
    // 跳转到答题界面，传递 session_id
    window.location.href = `/quiz.html?session=${result.session_id}`;
  }
  return result;
}

// 删除单个错题
async function deleteWrongQuestion(identifier) {
  const response = await fetch(`${API_BASE}/wrong-questions/${identifier}`, {
    method: 'DELETE'
  });
  return await response.json();
}

// 获取统计信息
async function fetchWrongQuestionStats() {
  const response = await fetch(`${API_BASE}/wrong-questions/stats`);
  return await response.json();
}
```

#### 3. 在主页添加入口

文件：`frontend/app.html`

在侧边栏添加"错题本"按钮：

```html
<section class="stats-card">
  <button class="btn-wrong-questions" onclick="window.location.href='/wrong-questions.html'">
    📚 错题本
  </button>
  <p id="wrong-count" style="font-size: 12px; color: var(--muted); margin-top: 8px; text-align: center;">
    当前错题：加载中...
  </p>
</section>
```

在页面加载时获取错题数量：

```javascript
async function updateWrongQuestionCount() {
  try {
    const response = await fetch(`${API_BASE}/wrong-questions/stats`);
    const data = await response.json();
    if (data.success) {
      document.getElementById('wrong-count').textContent =
        `当前错题：${data.data.total_wrong} 题`;
    }
  } catch (error) {
    console.error('Failed to fetch wrong question count:', error);
  }
}

// 页面加载时调用
window.addEventListener('DOMContentLoaded', updateWrongQuestionCount);
```

---

### Phase 3: 高级功能（优先级 LOW）

#### 1. 答题历史分析

从 `answer_history.jsonl` 分析：
- 每题的答题次数
- 错误率趋势
- 学习曲线
- 知识点掌握度

#### 2. 智能复练

- 基于遗忘曲线的复习提醒
- 错误率高的题增加复习频率
- 知识点关联推荐

#### 3. 数据导出

- 导出错题为 PDF/Excel
- 生成学习报告
- 错题打印功能

---

## 开发优先级

### 🔴 Phase 1: 核心功能（立即开发）

**预计工时**: 4-6 小时

1. ✅ 扩展 `RecordManager` 类（2小时）
   - 分页查询
   - 统计功能
   - 详情查询

2. ✅ 添加 Web API 端点（2小时）
   - GET /api/wrong-questions
   - GET /api/wrong-questions/stats
   - POST /api/wrong-questions/practice
   - DELETE /api/wrong-questions/:id
   - DELETE /api/wrong-questions

3. ✅ API 测试（1小时）

4. ✅ 更新文档（1小时）

### 🟡 Phase 2: 前端集成（后续开发）

**预计工时**: 6-8 小时

1. 错题本页面 UI（3小时）
2. 前端 API 集成（2小时）
3. 主页入口集成（1小时）
4. 用户体验优化（2小时）

### 🟢 Phase 3: 高级功能（可选）

**预计工时**: 10-15 小时

1. 数据分析和可视化（5小时）
2. 智能复练算法（5小时）
3. 导出和打印功能（5小时）

---

## 注意事项

### 1. 用户标识问题

**当前方案**（无用户系统）：
- 所有错题共享，不区分用户
- 适合单用户或信任环境

**未来扩展**（多用户支持）：
- 添加用户登录/会话管理
- 错题数据按用户隔离
- 数据结构需要添加 `user_id` 字段

### 2. 数据一致性

- 错题本与答题历史的同步
- 题目更新时的版本管理
- 并发写入的锁机制

### 3. 性能优化

- 大量错题时的分页性能
- 答题历史文件过大时的读取优化
- 考虑使用 SQLite 替代 JSON 文件

---

## 总结

这套方案提供了：
- ✅ 完整的 RESTful API 设计
- ✅ 清晰的数据结构
- ✅ 分阶段的实现计划
- ✅ 前后端集成方案
- ✅ 可扩展的架构设计

**建议**：先实现 Phase 1 的核心功能，验证可行性后再进行前端开发。

---

**设计完成时间**: 2025-11-04
**预计开发周期**: Phase 1 (1天) + Phase 2 (2天) = 3天
