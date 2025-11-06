# 答题考试系统（AI版）部署指南

## 🎯 系统概述

这是一个完整的 Web 版答题考试系统，集成了后端 API 和前端界面，支持：
- ✅ 知识文件上传（txt/md/pdf）
- ✅ 智能题目生成（单选/多选/填空/问答）
- ✅ 实时答题判分
- ✅ AI 题目生成（可选）
- ✅ 答题历史和错题本

---

## 📦 快速启动（5 分钟）

### 1. 安装依赖

```bash
# 安装Web依赖
pip install -r requirements-web.txt
```

### 2. 启动服务器

```bash
python web_server.py
```

服务器将在 **http://localhost:5001** 启动

### 3. 访问系统

在浏览器中打开：**http://localhost:5001**

---

## 🔧 系统架构

```
┌─────────────────────────────────────────┐
│           浏览器 (前端)                    │
│  ┌─────────────────────────────────┐    │
│  │  上传界面  │  答题界面  │  结果界面 │    │
│  └─────────────────────────────────┘    │
└──────────────┬──────────────────────────┘
               │ HTTP/REST API
┌──────────────▼──────────────────────────┐
│        Flask Web Server                  │
│  ┌────────────────────────────────┐     │
│  │  API 路由:                       │     │
│  │  - /api/upload-knowledge        │     │
│  │  - /api/generate-questions      │     │
│  │  - /api/get-question            │     │
│  │  - /api/submit-answer           │     │
│  │  - /api/session-status          │     │
│  └────────────────────────────────┘     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│           后端核心模块                     │
│  ┌────────────────────────────────┐     │
│  │  knowledge_loader.py           │     │
│  │  question_generator.py         │     │
│  │  record_manager.py             │     │
│  │  ai_client.py (可选)           │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘
```

---

## 📁 完整文件清单

### 核心文件

```
├── web_server.py              # Flask Web 服务器（后端 API）
├── frontend/
│   ├── app.html              # 前端主页面
│   └── assets/
│       ├── app.js            # 前端逻辑（对接后端）
│       └── styles.css        # UI 样式
├── src/
│   ├── knowledge_loader.py   # 知识文件解析
│   ├── question_generator.py # 题目生成器
│   ├── record_manager.py     # 答题记录管理
│   ├── ai_client.py          # AI 客户端
│   └── question_models.py    # 数据模型
├── manage_ai_config.py        # AI 配置工具
└── main.py                    # CLI 版本（命令行）
```

### 数据目录

```
├── uploads/                   # 用户上传的知识文件
├── data/
│   ├── answer_history.jsonl  # 答题历史记录
│   └── wrong_questions.json   # 错题本
└── AI_cf/
    └── cf.json                # AI 配置文件
```

---

## 🚀 完整使用流程

### 步骤 1：上传知识文件

1. 点击上传区域或拖拽文件
2. 支持格式：`.txt`、`.md`、`.pdf`
3. 文件大小：≤ 700KB
4. 系统自动解析知识条目

**示例文件结构（Markdown）**：

```markdown
| 部件 | 知识点 |
| :--- | :--- |
| 称重装置 | 必须确认电梯在满载和超载时的信号准确无误。 |
| 限速器 | 检查要点：调节螺钉上的铅封或封记必须完整... |
```

---

### 步骤 2：配置题目参数

#### 题型选择（多选）
- ✅ 单选题
- ✅ 多选题
- ✅ 填空题
- ✅ 问答题

#### 题目数量
- 范围：1-100 题
- 建议：10-20 题（快速练习）

#### AI 生成（可选）
- 范围：0-20 题
- 需要先配置 AI（点击侧边栏"⚙️ AI 配置"按钮）
- AI 失败不影响主流程

#### 出题顺序
- **顺序**：按知识条目顺序
- **随机**：打乱题目顺序

---

### 步骤 3：开始答题

#### 单选题
- 点击选项 A/B/C/D
- 点击"提交答案"

#### 多选题
- 可以选择多个选项
- 点击已选择的选项可取消
- 点击"提交答案"

#### 填空题
- 在文本框输入答案
- 点击"提交答案"

#### 问答题
- 在文本框输入详细回答
- 建议 ≥10 字
- 点击"提交答案"

---

### 步骤 4：查看反馈

#### 即时反馈
- ✅ **正确**：绿色提示框 + 正确解析
- ❌ **错误**：红色提示框 + 正确答案 + 解析

#### 统计信息（侧边栏实时更新）
- 已答题数
- 总题数
- 正确率

#### 下一题
- 点击"下一题"继续
- 最后一题自动跳转结果页

---

### 步骤 5：查看结果

- 最终得分（百分比）
- 正确题数 / 总题数
- 点击"重新开始"返回首页

---

## ⚙️ AI 配置（可选）

### 打开 AI 配置页面

1. 点击侧边栏的 **"⚙️ AI 配置"** 按钮
2. 在新标签页打开 AI 配置界面

### 配置 AI API

**必填字段**：
- **请求 URL**：`https://api.openai.com/v1/chat/completions`
- **API Key**：`sk-your-api-key`
- **模型名称**：`gpt-4o-mini`

**可选字段**：
- **超时时间**：默认 10 秒
- **开发者文档**：API 文档链接

### 测试连通性

1. 填写完配置后，点击"测试连通性"
2. 系统会发起真实 HTTP 请求
3. 查看测试结果：
   - ✅ 成功：HTTP 200
   - ❌ 失败：显示错误原因（如无网络、密钥错误）

### 保存配置

1. 点击"保存"按钮
2. 配置保存到 `AI_cf/cf.json`
3. CLI 版本（`main.py`）也可共享此配置

---

## 📊 API 接口文档

### 1. 上传知识文件

**请求**：
```http
POST /api/upload-knowledge
Content-Type: multipart/form-data

file: <binary>
```

**响应**：
```json
{
  "success": true,
  "filename": "uuid.txt",
  "filepath": "uploads/uuid.txt",
  "entry_count": 10,
  "entries_preview": [
    {
      "component": "称重装置",
      "text": "必须确认电梯在满载和超载时的信号准确无误..."
    }
  ]
}
```

---

### 2. 生成题目

**请求**：
```http
POST /api/generate-questions
Content-Type: application/json

{
  "filepath": "uploads/uuid.txt",
  "types": ["single", "multi", "cloze", "qa"],
  "count": 10,
  "ai_count": 2,
  "mode": "sequential",
  "seed": null
}
```

**响应**：
```json
{
  "success": true,
  "session_id": "session-uuid",
  "total_count": 12,
  "question_types": ["SINGLE_CHOICE", "MULTI_CHOICE", "CLOZE", "QA"]
}
```

---

### 3. 获取当前题目

**请求**：
```http
POST /api/get-question
Content-Type: application/json

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
    "prompt": "关于称重装置，以下哪项描述是正确的？",
    "options": ["选项A", "选项B", "选项C", "选项D"],
    "correct_options": [2],
    "answer_text": null,
    "explanation": "解析内容...",
    "keywords": []
  },
  "current_index": 1,
  "total_count": 12
}
```

---

### 4. 提交答案

**请求**：
```http
POST /api/submit-answer
Content-Type: application/json

{
  "session_id": "session-uuid",
  "answer": "C"
}
```

**响应**：
```json
{
  "success": true,
  "is_correct": true,
  "explanation": "✓ 回答正确！正确答案是 C 选项：...",
  "correct_answer": "C. 选项内容",
  "next_available": true
}
```

---

## 🎓 判分规则详解

### 单选题
- **输入格式**：`A`、`B`、`C`、`D`（单个字母）
- **判分逻辑**：精确匹配正确选项索引
- **示例**：
  - 正确答案：`B`
  - 用户输入：`B` → ✅ 正确
  - 用户输入：`A` → ❌ 错误

### 多选题
- **输入格式**：`ABC`、`BD`、`ACD`（多个字母，无空格）
- **判分逻辑**：所有选项都必须正确（顺序不限）
- **示例**：
  - 正确答案：`ABC`
  - 用户输入：`ABC` → ✅ 正确
  - 用户输入：`CBA` → ✅ 正确（顺序不限）
  - 用户输入：`AB` → ❌ 错误（缺少 C）
  - 用户输入：`ABCD` → ❌ 错误（多选了 D）

### 填空题
- **输入格式**：任意文本
- **判分逻辑**：关键词匹配（不区分大小写）
- **示例**：
  - 关键词：`["声光报警", "轿门开启"]`
  - 用户输入：`发出声光报警` → ✅ 正确（包含"声光报警"）
  - 用户输入：`保持轿门开启状态` → ✅ 正确（包含"轿门开启"）
  - 用户输入：`自动停止` → ❌ 错误（不包含任一关键词）

### 问答题
- **输入格式**：任意文本（建议 ≥10 字）
- **判分逻辑**：关键词匹配（包含任一关键词即正确）
- **示例**：
  - 关键词：`["铅封", "完整", "破坏"]`
  - 用户输入：`检查铅封是否完好` → ✅ 正确（包含"铅封"和"完整"）
  - 用户输入：`确保调节螺钉的铅封不能有破坏痕迹` → ✅ 正确（包含所有关键词）
  - 用户输入：`定期检查设备` → ❌ 错误（不包含任一关键词）

---

## 💾 数据持久化

### 答题历史（JSONL 格式）

**文件路径**：`data/answer_history.jsonl`

**格式说明**：
- 每行一条 JSON 记录
- 追加模式写入（append-only）

**示例记录**：
```json
{
  "timestamp": "2025-11-04T12:34:56.789Z",
  "session_id": "session-uuid",
  "question": {
    "identifier": "question-1",
    "question_type": "SINGLE_CHOICE",
    "prompt": "...",
    "options": [...],
    "correct_options": [2]
  },
  "user_answer": "C",
  "is_correct": true,
  "plain_explanation": "✓ 回答正确！...",
  "session_context": {
    "filepath": "uploads/uuid.txt",
    "mode": "web"
  }
}
```

---

### 错题本（JSON 格式）

**文件路径**：`data/wrong_questions.json`

**格式说明**：
- JSON 数组格式
- 答错自动添加
- 答对自动移除

**示例记录**：
```json
[
  {
    "question": {
      "identifier": "question-1",
      "question_type": "SINGLE_CHOICE",
      "prompt": "...",
      "options": [...],
      "correct_options": [2]
    },
    "last_plain_explanation": "✗ 回答错误。正确答案是 C 选项...",
    "last_wrong_at": "2025-11-04T12:34:56.789Z"
  }
]
```

---

## 🔍 常见问题

### 1. 端口被占用
**问题**：`Address already in use`

**解决方案**：
```python
# 修改 web_server.py 最后一行
app.run(debug=True, host='0.0.0.0', port=5002)  # 改成其他端口
```

同时修改 `frontend/assets/app.js`：
```javascript
const API_BASE = 'http://localhost:5002/api';  // 修改端口号
```

---

### 2. 跨域问题
**问题**：`CORS policy: No 'Access-Control-Allow-Origin' header`

**解决方案**：已使用 `flask-cors` 解决，无需额外配置

---

### 3. AI 生成失败
**问题**：AI 题目生成失败

**原因**：
- 未配置 AI（`AI_cf/cf.json` 不存在）
- API Key 错误
- 无网络连接
- API 额度不足

**解决方案**：
- AI 失败不影响主流程，系统会自动跳过
- 配置 AI：点击侧边栏"⚙️ AI 配置"按钮
- 测试连通性：确保 API 可访问

---

### 4. 文件上传失败
**问题**：文件上传后报错

**原因**：
- 文件格式不支持（仅支持 txt/md/pdf）
- 文件过大（>700KB）
- 文件内容无法解析

**解决方案**：
- 检查文件格式和大小
- 确保文件内容格式正确
- 查看服务器日志：`/tmp/web_server.log`

---

### 5. 题目生成数量不足
**问题**：知识条目太少，无法生成足够题目

**解决方案**：
- 上传更多知识内容
- 减少题目数量
- 启用 AI 生成（增加题目数量）

---

## 🚀 生产部署

### 使用 Gunicorn（推荐）

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务（4个工作进程）
gunicorn -w 4 -b 0.0.0.0:5001 web_server:app

# 后台运行
nohup gunicorn -w 4 -b 0.0.0.0:5001 web_server:app > gunicorn.log 2>&1 &
```

---

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /uploads {
        alias /path/to/QA/uploads;
    }

    client_max_body_size 1M;  # 上传文件大小限制
}
```

---

### 使用 Docker（推荐）

**Dockerfile**：
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-web.txt

COPY . .

EXPOSE 5001

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "web_server:app"]
```

**启动容器**：
```bash
# 构建镜像
docker build -t qa-system .

# 运行容器
docker run -d -p 5001:5001 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/AI_cf:/app/AI_cf \
  qa-system
```

---

## 📈 性能优化

### 1. 使用缓存
- 知识文件解析结果缓存（避免重复解析）
- 题目生成结果缓存（同一文件同一配置）

### 2. 数据库升级
- 将会话数据存储到 Redis（替代内存字典）
- 将答题历史存储到 PostgreSQL/MySQL（替代 JSONL）

### 3. 异步处理
- AI 题目生成异步化（使用 Celery）
- 文件上传异步处理

### 4. CDN 加速
- 前端静态资源（CSS/JS）使用 CDN
- 上传文件使用对象存储（如 AWS S3）

---

## 🔐 安全建议

### 1. API Key 安全
- ❌ 不要将 `AI_cf/cf.json` 提交到 Git
- ✅ 使用环境变量存储敏感信息
- ✅ 生产环境使用密钥管理服务（如 AWS Secrets Manager）

### 2. 文件上传安全
- ✅ 限制文件大小（≤700KB）
- ✅ 限制文件类型（仅 txt/md/pdf）
- ✅ 使用唯一文件名（UUID）
- ⚠️ 定期清理过期文件

### 3. 会话管理
- ⚠️ 当前使用内存字典存储会话（重启丢失）
- ✅ 生产环境使用 Redis 存储会话
- ✅ 设置会话过期时间（如 24 小时）

---

## 📝 更新日志

### v1.0 (2025-11-04)
- ✅ 完整的 Web 前端界面
- ✅ Flask REST API 后端
- ✅ 文件上传功能（点击/拖拽）
- ✅ 实时答题和判分
- ✅ 答题历史和错题本
- ✅ AI 题目生成支持
- ✅ AI 配置入口（侧边栏按钮）
- ✅ 响应式设计
- ✅ 完整的判分逻辑

---

## 📞 技术支持

### 遇到问题？

1. 查看服务器日志：`/tmp/web_server.log`
2. 查看浏览器控制台（F12）
3. 检查网络请求（Network 标签）
4. 参考本文档的"常见问题"章节

### 反馈建议

- GitHub Issues
- 邮件联系

---

## 📄 许可证

MIT License

---

**🎉 祝您使用愉快！**
