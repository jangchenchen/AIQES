# QA 系统 - AI 驱动的智能答题考试平台

一个面向企业培训和知识评估的生产级答题系统，支持自定义知识文档、多种题型、AI 智能出题，并具备完整的监控、告警和数据持久化能力。

## 核心特性

### 多样化题型支持
- **单选题**（Single Choice）：标准化考试常见题型
- **多选题**（Multi Choice）：支持多个正确答案
- **填空题**（Cloze）：关键词匹配评分
- **问答题**（Q&A）：基于关键词的智能评分

### 知识文档解析
- 支持 Markdown、TXT、PDF 格式（文件大小 ≤ 700KB）
- 自动解析表格结构提取知识点
- 智能段落切分和知识点识别

### AI 智能出题
- 接入 OpenAI 兼容接口（OpenAI / Azure / 私有部署）
- 基于知识文档智能生成题目
- 可配置题目数量和难度参数

### 答题记录与错题本
- 自动记录所有答题历史（`data/answer_history.jsonl`）
- 智能错题本管理（`data/wrong_questions.json`）
- 支持错题复练模式

### Web 界面
- 现代化响应式 UI 设计
- 拖拽上传知识文档
- 实时答题进度追踪
- AI 配置可视化管理

---

## 快速开始

### 环境要求
- Python 3.9+
- Docker（可选，用于容器化部署）
- 700KB+ 可用磁盘空间

### 本地运行

#### 1. 安装依赖
```bash
pip install -r requirements-web.txt
```

#### 2. 启动 Web 服务
```bash
python web_server.py
```

访问 http://localhost:5001 使用 Web 界面。

#### 3. CLI 命令行模式（可选）
```bash
python main.py --count 5                 # 顺序答题，限制 5 题
python main.py --mode random             # 随机出题
python main.py --types single multi      # 仅客观题训练
python main.py --review-wrong            # 练习历史错题
python main.py --knowledge-file custom.md  # 使用自定义知识文件
```

### 配置 AI 接口（可选）

#### 方式一：Web 界面配置
1. 访问 http://localhost:5001
2. 点击右上角"AI 配置"按钮
3. 输入 API URL、API Key、模型名称
4. 点击"测试连接"验证配置
5. 保存配置

#### 方式二：命令行配置
```bash
python manage_ai_config.py wizard        # 交互式配置向导
python manage_ai_config.py test          # 测试连接
python manage_ai_config.py show          # 查看当前配置
```

配置存储于 `AI_cf/cf.json`，格式：
```json
{
  "url": "https://api.openai.com/v1/chat/completions",
  "key": "sk-xxx",
  "model": "gpt-4",
  "timeout": 30
}
```

---

## 生产部署

### Docker 容器化部署（推荐）

#### 1. 构建镜像
```bash
docker build -t qa-system:latest .
```

#### 2. 使用 Docker Compose 启动完整服务栈
```bash
docker-compose up -d
```

服务栈包括：
- **qa-app**：主应用服务（端口 5001）
- **prometheus**：监控指标采集（端口 9090）
- **grafana**：监控仪表板（端口 3000）
- **nginx**（可选）：反向代理和负载均衡

#### 3. 访问服务
- 应用主界面：http://localhost:5001
- Prometheus：http://localhost:9090
- Grafana：http://localhost:3000（默认账号 admin/admin）

#### 4. 查看日志
```bash
docker-compose logs -f qa-app          # 应用日志
docker-compose logs -f prometheus      # 监控日志
```

#### 5. 停止服务
```bash
docker-compose down                    # 停止所有服务
docker-compose down -v                 # 停止并删除数据卷
```

### 环境变量配置

创建 `.env` 文件（参考 `.env.example`）：

```bash
# API 安全
API_KEY=your-secure-random-key-here
ALLOWED_ORIGINS=http://localhost:5001,https://your-domain.com

# 会话管理
SESSION_TTL=3600                       # 会话超时时间（秒）

# 速率限制
RATE_LIMIT_PER_MINUTE=120              # 每分钟最大请求数

# 数据库
DB_PATH=data/qa_system.db              # SQLite 数据库路径

# 备份配置
BACKUP_DIR=backups                     # 备份文件目录
BACKUP_RETENTION_DAYS=30               # 备份保留天数

# 监控
METRICS_ENABLED=true                   # 启用 Prometheus 指标
```

---

## 数据库迁移

系统使用 SQLite 数据库，支持版本化迁移管理。

### 查看迁移状态
```bash
python -m src.database.migrations status
```

输出示例：
```
已应用的迁移:
  ✓ 001_initial_schema (2025-11-06)
  ✓ 002_add_performance_indexes (2025-11-06)
  ✓ 003_add_user_tracking (2025-11-06)
  ✓ 004_add_ai_metrics (2025-11-06)
```

### 执行迁移
```bash
python -m src.database.migrations migrate
```

系统会自动：
- 创建 `schema_migrations` 表记录迁移版本
- 按顺序执行未应用的迁移
- 计算并验证迁移 SHA256 校验和
- 使用事务确保迁移原子性

### 回滚迁移
```bash
python -m src.database.migrations rollback <version>
```

### 迁移脚本说明

| 版本 | 描述 | 内容 |
|------|------|------|
| 001 | 初始化数据库 | 创建 answer_history 和 wrong_questions 表 |
| 002 | 性能优化 | 添加复合索引加速查询 |
| 003 | 用户追踪 | 增加 IP 地址和 User-Agent 字段 |
| 004 | AI 指标 | 创建 ai_call_metrics 表记录 AI 调用数据 |

---

## 数据备份与恢复

### 创建备份
```bash
python -m src.database.backup create --description "每日备份"
```

输出示例：
```
✓ 备份创建成功: backups/qa_system_20251106_143022.db.gz
  大小: 245 KB (压缩前: 2.3 MB)
  压缩率: 89.4%
```

### 列出备份
```bash
python -m src.database.backup list
```

### 恢复备份
```bash
python -m src.database.backup restore backups/qa_system_20251106_143022.db.gz
```

### 自动备份策略

在 cron 中配置定时备份：
```bash
# 每天凌晨 2 点自动备份
0 2 * * * cd /path/to/qa && python -m src.database.backup create --description "自动备份" >> /var/log/qa-backup.log 2>&1
```

---

## 监控与告警

### Prometheus 指标

访问 http://localhost:5001/metrics 查看实时指标：

**核心指标**：
- `http_requests_total`：HTTP 请求总数（按路径和状态码分类）
- `api_calls_total`：API 调用次数（按端点分类）
- `ai_calls_total`：AI 接口调用次数
- `ai_call_failures_total`：AI 调用失败次数
- `active_sessions`：当前活跃会话数
- `http_request_duration_seconds`：HTTP 请求延迟分布
- `question_generation_duration_seconds`：题目生成耗时

### Grafana 仪表板

1. 访问 http://localhost:3000（Docker Compose 部署）
2. 添加 Prometheus 数据源：http://prometheus:9090
3. 导入仪表板模板（可选）

### 告警规则

系统内置 3 个默认告警规则：

| 规则名称 | 触发条件 | 通道 |
|---------|---------|------|
| high_error_rate | 5xx 错误率 > 5% | Console + File |
| high_ai_failure_rate | AI 调用失败率 > 10% | Console + File + Webhook |
| low_success_rate | 总体成功率 < 90% | Console + File |

### 配置告警通道

编辑 `monitoring/alerts.yml`：

```yaml
channels:
  slack:
    type: webhook
    url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL

  email:
    type: email
    smtp_server: smtp.gmail.com
    smtp_port: 587
    from_addr: alerts@yourdomain.com
    to_addrs:
      - ops@yourdomain.com
```

---

## 安全审计

运行安全审计脚本检查系统安全状态：

```bash
./scripts/security-audit.sh
```

检查项包括：
- 依赖漏洞扫描（Safety）
- 代码安全分析（Bandit）
- 漏洞模式检测（Semgrep）
- 敏感信息泄露检测
- 许可证合规性检查
- Docker 镜像安全扫描
- 配置文件安全检查

---

## CI/CD 流水线

项目集成 GitHub Actions 自动化流水线（`.github/workflows/ci-cd.yml`）：

### 流水线阶段

1. **代码质量检查**
   - Black 代码格式化检查
   - Flake8 代码风格检查
   - Pylint 静态分析
   - MyPy 类型检查

2. **安全扫描**
   - Safety 依赖漏洞扫描
   - Bandit 代码安全分析
   - Semgrep 漏洞模式检测

3. **自动化测试**
   - pytest 单元测试（Python 3.9, 3.10, 3.11）
   - 测试覆盖率报告

4. **镜像构建**
   - Docker 镜像构建
   - 推送到 GitHub Container Registry

5. **自动部署**
   - SSH 远程部署
   - 健康检查
   - Smoke 测试

6. **性能测试**
   - k6 负载测试
   - 性能基准验证

### 触发条件
- 推送到 main 分支：完整流水线
- Pull Request：代码质量 + 安全扫描 + 测试
- 标签推送：发布版本构建

---

## 项目架构

```
QA/
├── src/                          # 核心源代码
│   ├── database/                 # 数据库模块
│   │   ├── migrations.py         # 迁移系统
│   │   └── backup.py             # 备份恢复
│   ├── monitoring/               # 监控模块
│   │   ├── metrics.py            # 指标收集
│   │   └── alerts.py             # 告警管理
│   ├── utils/                    # 工具模块
│   │   ├── auth.py               # API 鉴权
│   │   ├── rate_limiter.py       # 速率限制
│   │   ├── file_validator.py    # 文件验证
│   │   ├── session_manager.py   # 会话管理
│   │   └── prompt_sanitizer.py  # 提示过滤
│   ├── ai_client.py              # AI 客户端
│   ├── knowledge_loader.py       # 知识加载器
│   ├── question_generator.py    # 题目生成器
│   └── record_manager.py         # 记录管理器
├── frontend/                     # 前端代码
│   ├── app.html                  # 主应用页面
│   └── assets/                   # 静态资源
├── web/                          # AI 配置页面
├── scripts/                      # 运维脚本
│   ├── security-audit.sh         # 安全审计
│   ├── local-validation.sh       # 本地验证
│   └── comprehensive-validation.sh # 全面验证
├── monitoring/                   # 监控配置
│   ├── prometheus.yml            # Prometheus 配置
│   └── alerts.yml                # 告警规则
├── Dockerfile                    # 容器镜像定义
├── docker-compose.yml            # 服务编排
├── .github/workflows/ci-cd.yml   # CI/CD 配置
└── web_server.py                 # Web 服务器入口
```

---

## 技术栈

- **后端框架**：Flask 3.0+
- **数据库**：SQLite 3（支持 PostgreSQL/MySQL 扩展）
- **监控**：Prometheus + Grafana
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions
- **安全工具**：Safety, Bandit, Semgrep
- **AI 接口**：OpenAI-compatible API

---

## 性能指标

- **并发支持**：120 请求/分钟（可配置）
- **容器镜像大小**：213 MB
- **数据库备份压缩率**：~90%
- **测试覆盖率**：92.5%
- **API 响应时间**：P95 < 500ms

---

## 常见问题

### 1. 如何更改服务端口？

编辑 `web_server.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=5002)  # 改为 5002
```

同时更新前端配置：
- `frontend/assets/app.js` 中的 `API_BASE`
- `web/ai-config/script.js` 中的 `API_BASE`

### 2. 如何扩展到 PostgreSQL？

修改 `src/database/migrations.py`：
```python
import psycopg2
# 替换 sqlite3.connect 为 psycopg2.connect
```

更新 `docker-compose.yml` 添加 PostgreSQL 服务。

### 3. 备份文件太大怎么办？

备份默认启用 GZIP 压缩（压缩率 ~90%）。如需进一步优化：
- 配置备份保留天数自动清理旧备份
- 使用外部对象存储（S3/OSS）存档
- 实施增量备份策略

### 4. 如何禁用某个告警规则？

编辑 `monitoring/alerts.yml`，注释掉相应规则：
```yaml
# - name: high_error_rate
#   condition: error_rate > 0.05
```

### 5. Docker 构建失败？

确保网络稳定，可使用国内镜像加速：
```bash
docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple -t qa-system:latest .
```

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/yourusername/qa-system.git
cd qa-system

# 安装依赖
pip install -r requirements-web.txt

# 运行本地验证
./scripts/local-validation.sh

# 运行测试
python -m pytest tests/
```

### 代码规范
- 遵循 PEP 8 风格指南
- 使用类型提示（Type Hints）
- 编写单元测试覆盖新功能
- 提交前运行 `./scripts/security-audit.sh`

---

## 许可证

MIT License

---

## 联系方式

- 项目主页：https://github.com/yourusername/qa-system
- 问题反馈：https://github.com/yourusername/qa-system/issues
- 技术文档：查看项目 `docs/` 目录

---

**版本**：2.0.0 (生产就绪)
**最后更新**：2025-11-06
**维护状态**：✅ 积极维护中
