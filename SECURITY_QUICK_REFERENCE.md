# 安全功能快速参考卡

## 📦 新增工具模块

| 模块 | 路径 | 用途 |
|------|------|------|
| API 鉴权 | `src/utils/auth.py` | 密钥生成、验证、装饰器 |
| 文件验证 | `src/utils/file_validator.py` | MIME检测、PDF大小验证 |
| 会话管理 | `src/utils/session_manager.py` | 线程安全、TTL、自动清理 |
| 提示过滤 | `src/utils/prompt_sanitizer.py` | AI注入检测、输入清理 |
| 速率限制 | `src/utils/rate_limiter.py` | 滑动窗口限流器 |
| 日志工具 | `src/utils/logging.py` | JSON结构化日志 |

---

## 🔑 API 鉴权

### 生成密钥
```python
from src.utils.auth import init_api_key_if_needed
init_api_key_if_needed()  # 自动生成并保存
```

### 保护路由
```python
from src.utils.auth import require_api_key

@app.route('/api/sensitive', methods=['POST'])
@require_api_key
def sensitive_operation():
    pass
```

### 客户端调用
```bash
# Header 方式（推荐）
curl -H "X-API-Key: your-key" http://localhost:5001/api/...

# Query 参数方式
curl "http://localhost:5001/api/...?api_key=your-key"
```

---

## 📁 文件验证

### 验证上传文件
```python
from src.utils.file_validator import validate_upload_file

file_content = file.read()
is_valid, error = validate_upload_file(file_content, file.filename)

if not is_valid:
    return jsonify({"error": error}), 400
```

### 配置
```python
# src/utils/file_validator.py
MAX_FILE_SIZE = 700 * 1024  # 700KB
MAX_PDF_DECODED_SIZE = 10 * 1024 * 1024  # 10MB
```

---

## 🔒 会话管理

### 初始化
```python
from src.utils.session_manager import SessionManager

session_mgr = SessionManager(ttl_seconds=3600)  # 1小时
session_mgr.start_cleanup_thread()  # 启动后台清理
```

### 操作会话
```python
# 设置
session_mgr.set(session_id, data)

# 获取
data = session_mgr.get(session_id)  # 不存在或过期返回 None

# 更新
session_mgr.update(session_id, {"key": "value"})

# 删除
session_mgr.delete(session_id)

# 检查存在
if session_mgr.exists(session_id):
    pass
```

---

## 🛡️ AI 注入防护

### 检查输入安全
```python
from src.utils.prompt_sanitizer import is_safe_for_ai_prompt, sanitize_user_input

user_input = request.json.get('answer')

# 清理
cleaned = sanitize_user_input(user_input, max_length=5000)

# 验证
is_safe, reason = is_safe_for_ai_prompt(cleaned, strict=True)
if not is_safe:
    return jsonify({"error": f"输入不安全: {reason}"}), 400
```

### 危险模式
- `ignore previous instructions`
- `you are now admin`
- `forget everything`
- `execute code`

---

## ⏱️ 速率限制

### 配置限制器
```python
from src.utils.rate_limiter import RateLimiter, RateLimitConfig

limiter = RateLimiter(RateLimitConfig(
    capacity=60,  # 60次
    window_seconds=60.0  # 每分钟
))
```

### 检查限制
```python
client_ip = request.remote_addr

if not limiter.check(client_ip):
    return jsonify({"error": "请求过于频繁"}), 429
```

---

## 📊 当前配置

### CORS
```python
ALLOWED_ORIGINS = [
    "http://localhost:5001",
    "http://127.0.0.1:5001",
]
```

### 速率限制
- 一般请求：120次/分钟
- AI 请求：30次/分钟

### 会话 TTL
- 默认：3600秒（1小时）
- 清理间隔：60秒

### AI 重试
- 最大重试：3次

---

## 🚀 快速启动

```bash
# 1. 安装依赖
pip install -r requirements-web.txt

# 2. 启动服务器（自动初始化）
python web_server.py

# 3. 查看生成的 API 密钥
cat data/api_key.txt
```

---

## 🧪 快速测试

```bash
# 测试速率限制
for i in {1..130}; do curl http://localhost:5001/api/ai-config & done

# 测试文件验证
echo "fake" > fake.pdf
curl -F "file=@fake.pdf" http://localhost:5001/api/upload-knowledge

# 测试 AI 注入
curl -X POST http://localhost:5001/api/submit-answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"x","answer":"ignore all instructions"}'
```

---

## 📝 环境变量

创建 `.env` 文件：
```bash
API_KEY=your-secret-key
ALLOWED_ORIGINS=http://localhost:5001,https://yourdomain.com
SESSION_TTL=3600
```

---

## ⚠️ 注意事项

1. **API 密钥**：首次启动自动生成，保存在 `data/api_key.txt`
2. **MIME 检测**：需要安装 `libmagic` 系统库
3. **会话清理**：必须调用 `session_mgr.start_cleanup_thread()`
4. **前端鉴权**：如启用 API 鉴权，前端需添加 `X-API-Key` header
5. **生产部署**：修改 ALLOWED_ORIGINS 为实际域名

---

## 📖 详细文档

- **完整修复报告**：`SECURITY_FIXES_P0.md`
- **集成指南**：`INTEGRATION_GUIDE.md`
- **环境变量示例**：`.env.example`

---

**最后更新**: 2025-11-06
