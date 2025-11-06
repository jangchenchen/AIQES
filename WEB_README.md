# 答题考试系统（AI版）Web 版使用说明

## 快速启动

### 1. 安装Web依赖

```bash
pip install -r requirements-web.txt
```

### 2. 启动Web服务器

```bash
python web_server.py
```

服务器将在 `http://localhost:5000` 启动

### 3. 访问前端界面

在浏览器中打开：http://localhost:5000

---

## 功能说明

### 1. 上传知识文件
- 支持 **txt**、**md**、**pdf** 格式
- 文件大小不超过 **700KB**
- 可以点击或拖拽上传文件

### 2. 配置题目参数
- **题型选择**：单选题、多选题、填空题、问答题（可多选）
- **题目数量**：1-100 题
- **AI 生成**：额外生成 0-20 道 AI 题目（需配置 AI）
- **出题顺序**：顺序或随机

### 3. 开始答题
- 实时判分
- 即时反馈（正确/错误）
- 显示正确答案和解析
- 侧边栏实时统计

### 4. 查看结果
- 最终得分
- 正确题数 / 总题数
- 可重新开始

---

## API 接口文档

### 上传知识文件
**POST** `/api/upload-knowledge`

**请求**：
- Form Data: `file` (multipart/form-data)

**响应**：
```json
{
  "success": true,
  "filename": "uuid.txt",
  "filepath": "uploads/uuid.txt",
  "entry_count": 10,
  "entries_preview": [...]
}
```

---

### 生成题目
**POST** `/api/generate-questions`

**请求体**：
```json
{
  "filepath": "uploads/uuid.txt",
  "types": ["single", "multi", "cloze", "qa"],
  "count": 10,
  "ai_count": 0,
  "mode": "sequential",
  "seed": null
}
```

**响应**：
```json
{
  "success": true,
  "session_id": "session-uuid",
  "total_count": 10,
  "question_types": ["SINGLE_CHOICE", "MULTI_CHOICE"]
}
```

---

### 获取当前题目
**POST** `/api/get-question`

**请求体**：
```json
{
  "session_id": "session-uuid"
}
```

**响应**：
```json
{
  "finished": false,
  "question": {
    "identifier": "question-1",
    "question_type": "SINGLE_CHOICE",
    "prompt": "题目内容",
    "options": ["A选项", "B选项", "C选项", "D选项"],
    "correct_options": [0],
    "answer_text": null,
    "explanation": "解析内容",
    "keywords": []
  },
  "current_index": 1,
  "total_count": 10
}
```

---

### 提交答案
**POST** `/api/submit-answer`

**请求体**：
```json
{
  "session_id": "session-uuid",
  "answer": "A"
}
```

**响应**：
```json
{
  "success": true,
  "is_correct": true,
  "explanation": "✓ 回答正确！正确答案是 A 选项：...",
  "correct_answer": "A. 选项内容",
  "next_available": true
}
```

---

### 获取会话状态
**POST** `/api/session-status`

**请求体**：
```json
{
  "session_id": "session-uuid"
}
```

**响应**：
```json
{
  "session_id": "session-uuid",
  "current_index": 5,
  "total_count": 10,
  "correct_count": 4,
  "finished": false
}
```

---

## 错题功能 API（新增）

### 获取错题列表
**GET** `/api/wrong-questions`

**Query Parameters**:
- `page` (可选): 页码，默认 1
- `page_size` (可选): 每页数量，默认 20
- `question_type` (可选): 题型筛选 (`SINGLE_CHOICE`, `MULTI_CHOICE`, `CLOZE`, `QA`)
- `sort_by` (可选): 排序字段 (`last_wrong_at`, `identifier`)，默认 `last_wrong_at`
- `order` (可选): 排序方向 (`asc`, `desc`)，默认 `desc`

**响应**：
```json
{
  "success": true,
  "data": {
    "questions": [
      {
        "question": {/* 完整题目对象 */},
        "last_plain_explanation": "✗ 回答错误...",
        "last_wrong_at": "2025-11-04T02:15:20Z"
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

**示例**：
```bash
# 获取第一页（20题）
curl 'http://localhost:5001/api/wrong-questions?page=1&page_size=20'

# 只获取单选题
curl 'http://localhost:5001/api/wrong-questions?question_type=SINGLE_CHOICE'

# 按题目ID排序
curl 'http://localhost:5001/api/wrong-questions?sort_by=identifier&order=asc'
```

---

### 获取错题统计
**GET** `/api/wrong-questions/stats`

**响应**：
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
    "weakest_topics": [
      {"topic": "限速器", "count": 8},
      {"topic": "安全钳", "count": 6}
    ]
  }
}
```

---

### 创建错题练习会话
**POST** `/api/wrong-questions/practice`

**请求体**：
```json
{
  "question_types": ["SINGLE_CHOICE", "MULTI_CHOICE"],  // 可选，筛选题型
  "count": 10,          // 可选，限制题数
  "mode": "random"      // 可选：sequential, random（默认 random）
}
```

**响应**：
```json
{
  "success": true,
  "session_id": "uuid-here",
  "total_count": 10,
  "question_types": ["SINGLE_CHOICE", "MULTI_CHOICE"],
  "mode": "wrong_question_practice"
}
```

**使用说明**：
- 返回的 `session_id` 可用于现有的 `/api/get-question` 和 `/api/submit-answer` 接口
- 答对的题会自动从错题本移除
- 如果当前没有错题，返回 400 错误

---

### 获取单个错题详情
**GET** `/api/wrong-questions/{identifier}`

**Path Parameter**:
- `identifier`: 题目唯一标识符（如：`限速器-SC-1`）

**响应**：
```json
{
  "success": true,
  "data": {
    "question": {/* 完整题目对象 */},
    "last_plain_explanation": "✗ 回答错误...",
    "last_wrong_at": "2025-11-04T02:15:20Z"
  }
}
```

---

### 删除单个错题
**DELETE** `/api/wrong-questions/{identifier}`

**Path Parameter**:
- `identifier`: 题目唯一标识符

**响应**：
```json
{
  "success": true,
  "message": "错题已删除"
}
```

---

### 清空错题本
**DELETE** `/api/wrong-questions`

**响应**：
```json
{
  "success": true,
  "message": "已清空错题本",
  "deleted_count": 45
}
```

---

## 判分逻辑

### 单选题
- 输入格式：`A`、`B`、`C`、`D`
- 判分方式：精确匹配正确选项索引

### 多选题
- 输入格式：`ABC`、`BD`、`ACD`（多个字母）
- 判分方式：所有选项都必须正确（顺序不限）

### 填空题
- 输入格式：任意文本
- 判分方式：关键词匹配（不区分大小写）

### 问答题
- 输入格式：任意文本（建议 ≥10 字）
- 判分方式：关键词匹配（包含任一关键词即正确）

---

## 数据持久化

所有答题记录会自动保存到：
- `data/answer_history.jsonl` - 答题历史（JSON Lines 格式）
- `data/wrong_questions.json` - 错题本（答错自动添加，答对自动移除）

---

## 目录结构

```
.
├── web_server.py              # Flask Web 服务器
├── frontend/
│   ├── app.html              # 前端主页面
│   └── assets/
│       ├── app.js            # 前端逻辑
│       └── styles.css        # 样式文件
├── uploads/                  # 上传文件存储目录
├── data/                     # 数据存储目录
│   ├── answer_history.jsonl # 答题历史
│   └── wrong_questions.json  # 错题本
└── requirements-web.txt      # Web 依赖
```

---

## 常见问题

### 1. 端口被占用
修改 `web_server.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # 改成其他端口
```

### 2. 跨域问题
已使用 `flask-cors` 解决跨域，无需额外配置

### 3. AI 生成失败
- 确保已配置 AI（运行 `python manage_ai_config.py wizard`）
- AI 失败不影响主流程，系统会自动跳过

### 4. 文件上传失败
- 检查文件格式（仅支持 txt/md/pdf）
- 检查文件大小（≤700KB）
- 检查 `uploads/` 目录权限

---

## 开发说明

### 修改前端
前端代码位于 `frontend/app.html` 和 `frontend/assets/app.js`

修改后刷新浏览器即可看到效果（无需重启服务器）

### 修改后端
修改 `web_server.py` 后需要重启服务器：
1. 按 `Ctrl+C` 停止服务器
2. 运行 `python web_server.py` 重新启动

### 调试模式
服务器默认运行在 `debug=True` 模式，代码修改会自动重启（仅限后端）

---

## 生产部署

### 使用 Gunicorn（推荐）

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务（4个工作进程）
gunicorn -w 4 -b 0.0.0.0:5000 web_server:app
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads {
        alias /path/to/uploads;
    }
}
```

---

## 许可证

MIT License

---

## 更新日志

### v1.1 (2025-11-04)
- ✅ **错题功能 API** - 新增 6 个错题管理端点
  - 获取错题列表（分页、筛选、排序）
  - 获取错题统计（题型分布、薄弱知识点）
  - 创建错题练习会话
  - 获取单个错题详情
  - 删除单个错题
  - 清空错题本
- ✅ 扩展 `RecordManager` 类支持错题查询
- ✅ 完善 API 文档

### v1.0 (2025-11-04)
- ✅ 完整的 Web 前端界面
- ✅ Flask REST API 后端
- ✅ 文件上传功能（拖拽支持）
- ✅ 实时答题和判分
- ✅ 答题历史和错题本
- ✅ AI 题目生成支持
- ✅ 响应式设计
