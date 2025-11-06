# 安全功能使用说明

本项目已实施全面的安全加固，包括 API 鉴权、文件验证、速率限制、AI 注入防护等功能。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements-web.txt
```

**新增依赖**：
- `python-magic` - MIME 类型检测
- `PyPDF2` - PDF 文件验证

**系统依赖**（仅用于 MIME 检测）：
```bash
# macOS
brew install libmagic

# Ubuntu/Debian
sudo apt-get install libmagic1
```

### 2. 首次启动
```bash
python web_server.py
```

首次启动时会自动：
- ✅ 生成 API 密钥（保存到 `data/api_key.txt`）
- ✅ 初始化 SQLite 数据库
- ✅ 启动会话清理线程

您会看到类似输出：
```
============================================================
🔑 首次启动已生成 API 密钥:
   lP_aRr_XOQV4ZfNyzVit...

请将此密钥保存在安全的地方，用于 API 鉴权。
也可以设置环境变量: export API_KEY=your-key
============================================================
✅ 会话清理线程已启动（TTL: 3600秒）
访问地址: http://localhost:5001
```

---

## 🔒 安全功能

### 1. CORS 限制
只允许可信域名访问 API。

**默认配置**（开发环境）：
```python
ALLOWED_ORIGINS = [
    "http://localhost:5001",
    "http://127.0.0.1:5001",
]
```

**生产环境配置**：
```python
ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
```

### 2. 速率限制
防止 API 滥用和 DDoS 攻击。

**当前限制**：
- 一般请求：120次/分钟
- AI 请求：30次/分钟

**配置**（`web_server.py`）：
```python
REQUEST_RATE_LIMITER = RateLimiter(RateLimitConfig(
    capacity=60,  # 调整为您的需求
    window_seconds=60.0
))
```

### 3. API 鉴权
保护敏感 API 端点，防止未授权访问。

**查看您的 API 密钥**：
```bash
cat data/api_key.txt
```

**使用 API**（客户端）：
```bash
# 方式1：Header（推荐）
curl -H "X-API-Key: your-key" \
  http://localhost:5001/api/generate-questions

# 方式2：Query 参数
curl "http://localhost:5001/api/generate-questions?api_key=your-key"
```

**前端集成**（`frontend/assets/app.js`）：
```javascript
const API_KEY = 'your-api-key';  // 从安全存储获取

fetch('/api/generate-questions', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
    },
    body: JSON.stringify({...}),
});
```

### 4. 文件上传验证
防止恶意文件上传和路径遍历攻击。

**自动验证**：
- ✅ MIME 类型检测（真实文件类型）
- ✅ 扩展名与 MIME 类型匹配
- ✅ 文件大小限制（700KB）
- ✅ PDF 解码后大小限制（10MB）
- ✅ 随机文件名（UUID）

**支持的文件类型**：
- `.txt` - 纯文本
- `.md` - Markdown
- `.pdf` - PDF 文档

### 5. 会话管理
线程安全的会话管理，自动过期和清理。

**配置**：
```python
# 会话 TTL（秒）
SESSION_TTL = 3600  # 1小时
```

**特性**：
- ✅ 线程安全（RLock）
- ✅ 自动过期
- ✅ 后台清理（每分钟）
- ✅ 访问时刷新 TTL

### 6. AI 注入防护
检测并阻止恶意的 AI 提示注入攻击。

**自动检测的危险模式**：
- `ignore previous instructions`
- `you are now an admin`
- `forget everything`
- `execute code`
- `system: grant me access`
- 等 20+ 种模式

**效果**：
```bash
# 恶意输入会被拒绝
curl -X POST /api/submit-answer \
  -d '{"answer":"ignore all instructions"}' \

# 响应
{"error": "输入不安全: 检测到可疑指令"}
```

---

## 📁 文件结构

```
QA/
├── src/
│   └── utils/              # 安全工具模块
│       ├── auth.py         # API 鉴权
│       ├── file_validator.py  # 文件验证
│       ├── session_manager.py # 会话管理
│       ├── prompt_sanitizer.py # AI 注入防护
│       ├── rate_limiter.py    # 速率限制
│       └── logging.py         # 日志工具
│
├── data/
│   ├── api_key.txt        # API 密钥（不要提交！）
│   ├── records.db         # SQLite 数据库
│   └── sessions.json      # 会话持久化
│
├── web_server.py          # Flask 服务器（已集成安全功能）
├── test_security.py       # 安全功能测试
│
└── 文档/
    ├── SECURITY_FIXES_P0.md          # 完整修复报告
    ├── INTEGRATION_GUIDE.md          # 集成指南
    ├── SECURITY_QUICK_REFERENCE.md   # 快速参考
    ├── P0_FIXES_SUMMARY.md           # 修复总结
    ├── SECURITY_README.md            # 本文档
    └── .env.example                  # 环境变量示例
```

---

## 🧪 测试

### 运行安全测试
```bash
python test_security.py
```

**测试内容**：
- ✅ API 密钥生成和验证
- ✅ 文件类型检测
- ✅ 文件大小限制
- ✅ 会话 TTL 和过期
- ✅ AI 注入检测
- ✅ 速率限制窗口滑动

**预期输出**：
```
============================================================
测试 API 鉴权
============================================================
✓ 生成密钥: xxx...
✓ 保存密钥到文件
✓ 成功读取密钥

============================================================
所有测试通过！
============================================================
```

### 手动测试

**测试速率限制**：
```bash
for i in {1..130}; do
  curl http://localhost:5001/api/ai-config &
done
wait
# 最后几个请求应返回 429
```

**测试文件验证**：
```bash
# 创建伪造的 PDF
echo "fake pdf" > fake.pdf
curl -F "file=@fake.pdf" http://localhost:5001/api/upload-knowledge
# 应返回 400 文件类型验证失败
```

**测试 AI 注入**：
```bash
curl -X POST http://localhost:5001/api/submit-answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"x","answer":"ignore all instructions"}'
# 应返回 400 输入不安全
```

---

## ⚙️ 配置

### 环境变量（可选）

创建 `.env` 文件：
```bash
# API 鉴权
API_KEY=your-secret-key-here

# CORS 配置
ALLOWED_ORIGINS=http://localhost:5001,https://yourdomain.com

# 速率限制
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# 会话配置
SESSION_TIMEOUT=3600

# 文件上传
MAX_FILE_SIZE=700000
MAX_PDF_DECODED_SIZE=10485760

# AI 配置
AI_MAX_RETRIES=3
AI_REQUEST_TIMEOUT=45.0
```

### 代码配置

修改 `web_server.py` 中的配置：

```python
# CORS
ALLOWED_ORIGINS = ["https://yourdomain.com"]

# 速率限制
REQUEST_RATE_LIMITER = RateLimiter(RateLimitConfig(
    capacity=60,
    window_seconds=60.0
))

# 会话 TTL
session_mgr = SessionManager(ttl_seconds=1800)  # 30分钟
```

---

## 🚨 故障排查

### 问题：python-magic 安装失败

**原因**：缺少系统库 `libmagic`

**解决**：
```bash
# macOS
brew install libmagic
pip install python-magic

# Ubuntu/Debian
sudo apt-get install libmagic1
pip install python-magic

# Windows
pip install python-magic-bin
```

### 问题：API 密钥验证失败

**检查步骤**：
1. 查看密钥文件：`cat data/api_key.txt`
2. 确认环境变量未冲突：`echo $API_KEY`
3. 检查 Header 格式：`X-API-Key: your-key`

### 问题：会话清理线程未启动

**检查**：
```python
# 确保在 web_server.py 中调用了
session_mgr.start_cleanup_thread()
```

### 问题：速率限制过于严格

**调整配置**：
```python
# 增加容量
REQUEST_RATE_LIMITER = RateLimiter(RateLimitConfig(
    capacity=200,  # 增加到 200
    window_seconds=60.0
))
```

---

## 📊 监控

### 关键日志事件

监控以下事件以了解系统安全状态：

```json
// 速率限制触发
{
  "event": "rate_limit_exceeded",
  "client": "192.168.1.100",
  "path": "/api/generate-questions"
}

// 文件验证失败
{
  "event": "upload_validation_failed",
  "reason": "MIME type mismatch"
}

// AI 注入检测
{
  "event": "invalid_request",
  "reason": "unsafe_input"
}

// 会话清理
🗑️  清理了 5 个过期会话
```

### 监控指标

- **速率限制触发率**：< 1%（正常），> 5%（可能攻击）
- **文件验证失败率**：< 5%（正常），> 20%（可疑）
- **会话过期数量**：稳定（正常），突增（可能问题）

---

## 🔐 安全最佳实践

### 生产部署

1. **修改默认配置**
   ```python
   ALLOWED_ORIGINS = ["https://yourdomain.com"]  # 实际域名
   SESSION_TTL = 1800  # 30分钟
   RATE_LIMIT = 60  # 更严格
   ```

2. **使用环境变量存储密钥**
   ```bash
   export API_KEY=$(cat data/api_key.txt)
   # 然后删除文件
   rm data/api_key.txt
   ```

3. **启用 HTTPS**
   ```python
   # 使用反向代理（Nginx/Caddy）
   # 或配置 Flask SSL
   ```

4. **定期轮换 API 密钥**
   ```bash
   python -c "from src.utils.auth import *; save_api_key(generate_api_key())"
   ```

5. **监控日志**
   ```bash
   tail -f *.log | grep -E "(rate_limit|validation_failed|unsafe_input)"
   ```

### 开发建议

- ✅ 使用 `.env` 文件管理配置
- ✅ 不要提交 API 密钥到 Git
- ✅ 定期运行 `test_security.py`
- ✅ 检查 `.gitignore` 包含敏感文件

---

## 📚 更多文档

- **快速参考**：`SECURITY_QUICK_REFERENCE.md`
- **集成指南**：`INTEGRATION_GUIDE.md`
- **完整报告**：`SECURITY_FIXES_P0.md`
- **修复总结**：`P0_FIXES_SUMMARY.md`

---

## ❓ 常见问题

### Q: API 密钥是必需的吗？
A: 开发环境可选（默认跳过验证），生产环境强烈建议。

### Q: 如何禁用 API 鉴权？
A: 删除路由上的 `@require_api_key` 装饰器。

### Q: 速率限制会影响正常用户吗？
A: 不会。默认 120次/分钟对正常使用足够宽松。

### Q: 会话数据安全吗？
A: 存储在本地 SQLite，建议生产环境加密或使用 Redis。

### Q: 如何添加新的 AI 注入检测模式？
A: 编辑 `src/utils/prompt_sanitizer.py` 中的 `DANGEROUS_PATTERNS` 列表。

---

## 📞 支持

遇到问题？
1. 查看文档（本目录下的 `SECURITY_*.md` 文件）
2. 运行测试：`python test_security.py`
3. 查看日志：`*.log` 文件

---

**祝您使用愉快！** 🎉
