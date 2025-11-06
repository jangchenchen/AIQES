# P2 功能快速启动指南

🚀 **5分钟快速上手P2新功能**

---

## 1. 数据库迁移

```bash
# 运行所有迁移
python -m src.database.migrations migrate

# 查看迁移状态
python -m src.database.migrations status

# 回滚（如果需要）
python -m src.database.migrations rollback
```

**预期输出**:
```
✅ 迁移成功: 001_initial_schema (125ms)
✅ 迁移成功: 002_add_performance_indexes (45ms)
✅ 迁移成功: 003_add_user_tracking (32ms)
✅ 迁移成功: 004_add_ai_metrics (28ms)

✅ 所有迁移已应用完成
```

---

## 2. 数据备份

```bash
# 创建备份
python -m src.database.backup create

# 列出所有备份
python -m src.database.backup list

# 恢复备份（谨慎！）
python -m src.database.backup restore data/backups/backup_20250106_120000.db.gz
```

**自动备份**（在 `web_server.py` 中添加）:
```python
from src.database.backup import scheduled_backup
from pathlib import Path

# 每24小时自动备份
scheduled_backup(
    db_path=Path("data/records.db"),
    backup_dir=Path("data/backups"),
    interval_hours=24
)
```

---

## 3. 监控指标

### 3.1 添加指标端点

在 `web_server.py` 中添加：

```python
from src.monitoring.metrics import metrics

@app.route('/metrics')
def prometheus_metrics():
    return metrics.get_prometheus_metrics(), 200, {
        'Content-Type': 'text/plain; charset=utf-8'
    }
```

### 3.2 使用指标

```python
from src.monitoring.metrics import AppMetrics, Timer

# 计数
AppMetrics.http_requests_total.inc()
AppMetrics.api_calls_total.inc()

# 计时
with Timer(AppMetrics.http_request_duration):
    # 你的代码
    pass

# 仪表
AppMetrics.active_sessions.set(42)
```

### 3.3 访问指标

```bash
# 查看指标
curl http://localhost:5001/metrics

# 应该看到类似输出：
# http_requests_total 152.0
# api_calls_total 98.0
# active_sessions 5.0
```

---

## 4. 告警系统

```python
from src.monitoring.alerts import (
    alert_manager,
    create_default_rules,
    ConsoleChannel,
    WebhookChannel,
)
from src.monitoring.metrics import metrics

# 添加告警通道
alert_manager.add_channel(ConsoleChannel())

# Slack/Discord webhook（可选）
# alert_manager.add_channel(WebhookChannel(
#     webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK"
# ))

# 添加默认规则
for rule in create_default_rules(metrics):
    alert_manager.add_rule(rule)

# 启动监控（每60秒检查一次）
alert_manager.start(interval_seconds=60)
```

**告警示例输出**:
```
🚨 ALERT [ERROR] high_error_rate
   API 错误率超过 10%
   Time: 2025-11-06T10:30:00Z
```

---

## 5. Docker 快速启动

```bash
# 构建镜像
docker build -t qa-system:latest .

# 运行单个容器
docker run -p 5001:5001 \
  -v $(pwd)/data:/app/data \
  -e API_KEY=your-secret-key \
  qa-system:latest

# 或使用 docker-compose（推荐）
docker-compose up -d

# 查看日志
docker-compose logs -f qa-app

# 进入容器
docker-compose exec qa-app bash
```

---

## 6. 监控栈启动

```bash
# 启动 Prometheus + Grafana
docker-compose up -d prometheus grafana

# 访问
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)
```

**在 Grafana 中添加数据源**:
1. 登录 Grafana
2. Configuration → Data Sources → Add data source
3. 选择 Prometheus
4. URL: `http://prometheus:9090`
5. Save & Test

**创建仪表板**:
1. Create → Dashboard → Add new panel
2. 查询: `rate(http_requests_total[5m])`
3. Title: "Request Rate"
4. Apply

---

## 7. CI/CD 配置

### GitHub Actions（自动）

只需推送代码，Pipeline 会自动运行：

```bash
git add .
git commit -m "feat: add new feature"
git push origin main
```

**查看运行状态**:
https://github.com/your-repo/actions

### 本地测试 Pipeline

```bash
# 代码质量检查
black --check .
isort --check-only .
flake8 src/

# 安全扫描
safety check
bandit -r src/

# 运行测试
pytest test_security.py -v --cov=src
```

---

## 8. 安全审计

```bash
# 运行完整审计
chmod +x scripts/security-audit.sh
./scripts/security-audit.sh

# 查看报告
cat reports/audit-summary.json
```

**预期输出**:
```
============================================================
安全审计开始
============================================================

📦 检查依赖漏洞...
✅ 未发现已知漏洞

🔍 代码静态分析...
✅ 未发现严重问题

🔎 运行 Semgrep...
✅ 未发现漏洞模式

============================================================
✅ 安全审计完成
============================================================
```

---

## 9. 生产部署速查

```bash
# 1. 服务器准备
ssh user@your-server
sudo apt-get update
sudo apt-get install docker docker-compose

# 2. 部署代码
git clone https://github.com/your/qa-system.git /opt/qa-system
cd /opt/qa-system

# 3. 配置环境
cp .env.example .env
vim .env  # 设置 API_KEY, ALLOWED_ORIGINS 等

# 4. 启动服务
docker-compose --profile production up -d

# 5. 运行迁移
docker-compose exec qa-app python -m src.database.migrations migrate

# 6. 验证
curl https://your-domain.com/api/ai-config

# 7. 查看日志
docker-compose logs -f
```

---

## 10. 故障排查速查

### 服务启动失败

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs qa-app --tail=100

# 重启服务
docker-compose restart qa-app
```

### 数据库问题

```bash
# 检查数据库完整性
docker-compose exec qa-app \
  sqlite3 data/records.db "PRAGMA integrity_check;"

# 查看迁移状态
docker-compose exec qa-app \
  python -m src.database.migrations status

# 恢复备份
docker-compose exec qa-app \
  python -m src.database.backup restore \
  data/backups/backup_YYYYMMDD_HHMMSS.db.gz
```

### 监控不工作

```bash
# 检查 Prometheus
curl http://localhost:9090/-/healthy

# 检查指标端点
curl http://localhost:5001/metrics

# 重启监控栈
docker-compose restart prometheus grafana
```

---

## 11. 常用 API

### 指标 API

```bash
# 获取所有指标（JSON）
curl http://localhost:5001/api/metrics

# Prometheus 格式
curl http://localhost:5001/metrics
```

### 健康检查

```bash
curl http://localhost:5001/api/health
```

应该返回：
```json
{
  "status": "healthy",
  "database": "ok",
  "sessions": 5,
  "uptime": 3600
}
```

---

## 12. 性能测试

```bash
# 使用 ab（Apache Bench）
ab -n 1000 -c 10 http://localhost:5001/api/ai-config

# 使用 k6（如果安装）
k6 run tests/performance/load-test.js
```

---

## 13. 环境变量速查

创建 `.env` 文件：

```bash
# API 安全
API_KEY=your-generated-key-here

# CORS
ALLOWED_ORIGINS=http://localhost:5001,https://yourdomain.com

# 会话
SESSION_TTL=3600

# 速率限制
RATE_LIMIT_PER_MINUTE=60

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=your-secure-password
```

---

## 14. 日常维护命令

```bash
# 每天
docker-compose logs qa-app --since=24h | grep ERROR

# 每周
./scripts/security-audit.sh
docker-compose exec qa-app python -m src.database.backup create

# 每月
pip list --outdated
docker system prune -f
```

---

## 15. 有用的链接

| 服务 | 本地 URL | 生产 URL |
|------|---------|----------|
| QA 应用 | http://localhost:5001 | https://qa.yourdomain.com |
| Prometheus | http://localhost:9090 | https://prometheus.yourdomain.com |
| Grafana | http://localhost:3000 | https://grafana.yourdomain.com |
| 指标端点 | http://localhost:5001/metrics | - |

---

## 📚 完整文档

- **完整指南**: `P2_COMPLETE_GUIDE.md`
- **P0 修复**: `SECURITY_FIXES_P0.md`
- **快速参考**: `SECURITY_QUICK_REFERENCE.md`
- **集成指南**: `INTEGRATION_GUIDE.md`

---

## ⚡ 下一步

1. ✅ 运行数据库迁移
2. ✅ 配置环境变量
3. ✅ 启动 Docker Compose
4. ✅ 访问 Grafana 创建仪表板
5. ✅ 配置告警通道
6. ✅ 运行安全审计

**祝你使用愉快！** 🎉

---

**问题反馈**:
- 查看日志: `docker-compose logs -f`
- 运行测试: `pytest test_security.py -v`
- 安全审计: `./scripts/security-audit.sh`
