# AI 配置页面 404 问题修复说明

## 问题描述

之前 AI 配置页面返回 404 错误，因为：
1. Flask 服务器只配置了 `frontend/` 文件夹作为静态文件目录
2. AI 配置页面位于 `web/ai-config/` 目录，无法被访问
3. FastAPI 后端 (server/app.py) 的 AI 配置路由没有集成到 Flask 服务器

## 修复方案

### 1. 添加 web 文件夹路由

在 `web_server.py` 中添加了新的路由来服务 `web/` 目录：

```python
@app.route('/web/<path:filename>')
def serve_web_files(filename):
    """Serve files from the web/ directory (for AI config page)"""
    return send_from_directory('web', filename)
```

### 2. 集成 AI 配置 API 路由

将 FastAPI 后端 (server/app.py) 的所有 AI 配置路由集成到 Flask 服务器：

- `GET /api/ai-config` - 获取当前配置
- `PUT /api/ai-config` - 保存/更新配置
- `POST /api/ai-config/test` - 测试连通性
- `DELETE /api/ai-config` - 删除配置

### 3. 更新前端 API 地址

修改 `web/ai-config/script.js` 中的 API_BASE：

```javascript
// 从 8000 端口改为 5001 端口
const API_BASE = (window.location.protocol.startsWith('http')
  ? window.location.origin
  : 'http://localhost:5001'  // 原来是 8000
).replace(/\/$/, '');
```

## 验证结果

✅ **AI 配置页面访问**: http://localhost:5001/web/ai-config/index.html
- 返回 HTTP 200 OK
- 页面正常加载

✅ **静态资源访问**:
- CSS: http://localhost:5001/web/ai-config/styles.css (200 OK)
- JS: http://localhost:5001/web/ai-config/script.js (200 OK)

✅ **API 端点测试**:
```bash
# 获取当前配置
curl http://localhost:5001/api/ai-config

# 返回示例：
{
  "dev_document": "https://yunwu.apifox.cn/api-232421916",
  "key": "sk-...",
  "model": "gemini-2.5-flash-nothinking",
  "timeout": 10.0,
  "url": "https://yunwu.ai/v1/video/create#"
}

# 测试连通性
curl -X POST http://localhost:5001/api/ai-config/test \
  -H "Content-Type: application/json" \
  -d '{"url":"...","key":"...","model":"..."}'

# 返回：
{
  "ok": true/false,
  "message": "..."
}
```

## 架构变更

### 修复前
- Flask 服务器 (web_server.py) - 端口 5001
  - 仅处理答题系统 API
  - 静态文件：frontend/
- FastAPI 服务器 (server/app.py) - 端口 8000 (未运行)
  - AI 配置 API
- 问题：AI 配置页面无法访问 ❌

### 修复后
- **统一的 Flask 服务器** (web_server.py) - 端口 5001
  - 答题系统 API (/api/upload-knowledge, /api/generate-questions, 等)
  - AI 配置 API (/api/ai-config, /api/ai-config/test, 等)
  - 静态文件服务：
    - frontend/ (主页面)
    - web/ (AI 配置页面)
- FastAPI 服务器不再需要单独运行 ✅

## 使用方法

### 启动服务器
```bash
python web_server.py
```

### 访问 AI 配置页面

**方式 1**: 从主页侧边栏点击 "⚙️ AI 配置" 按钮

**方式 2**: 直接访问 http://localhost:5001/web/ai-config/index.html

### 配置 AI
1. 填写 API URL、Key、模型名称
2. 点击 "测试连通性" 验证配置
3. 点击 "保存配置" 保存到 `AI_cf/cf.json`
4. 配置保存后，答题系统会自动使用该配置生成 AI 题目

## 技术细节

### 依赖项
```python
# web_server.py 新增导入
from manage_ai_config import (
    load_config as load_ai_config,
    save_config,
    test_connectivity,
    delete_config,
    AIConfig,
)
```

### 数据流
```
用户浏览器
  ↓
AI 配置页面 (web/ai-config/index.html)
  ↓
JavaScript (script.js)
  ↓
Flask API (web_server.py)
  ↓
manage_ai_config.py
  ↓
AI_cf/cf.json (配置文件)
```

## 后续优化建议

1. **缓存配置**: 在服务器启动时加载配置到内存，避免频繁读取文件
2. **配置验证**: 添加更严格的配置参数验证（URL 格式、Key 长度等）
3. **安全加固**: 考虑对 API Key 进行加密存储
4. **错误处理**: 完善 AI 配置失败时的错误提示和降级策略

## 结论

✅ **问题已完全修复**

- AI 配置页面现在可以正常访问
- 所有 API 端点正常工作
- 无需运行单独的 FastAPI 服务器
- 统一在 Flask 服务器 (端口 5001) 上提供所有功能

---

**修复时间**: 2025-11-04
**服务器地址**: http://localhost:5001
**AI 配置页面**: http://localhost:5001/web/ai-config/index.html
