# P2 快速参考卡片

## 🚀 5 分钟验证

```bash
# 1. 检查文件
ls -1 src/database/*.py src/monitoring/*.py

# 2. 测试迁移
python -m src.database.migrations migrate

# 3. 测试指标
python -c "
from src.monitoring.metrics import metrics, AppMetrics
AppMetrics.http_requests_total.inc()
print(metrics.get_prometheus_metrics()[:200])
"

# 4. 查看文档
cat P2_VALIDATION_REPORT.md
```

## 📁 关键文件速查

| 文件 | 用途 | 命令 |
|------|------|------|
| `src/database/migrations.py` | 数据库迁移 | `python -m src.database.migrations migrate` |
| `src/database/backup.py` | 备份恢复 | `python -m src.database.backup create` |
| `src/monitoring/metrics.py` | 指标收集 | 集成到 Flask `/metrics` 端点 |
| `src/monitoring/alerts.py` | 告警管理 | 在 `web_server.py` 中配置 |
| `Dockerfile` | 容器镜像 | `docker build -t qa-system .` |
| `docker-compose.yml` | 服务编排 | `docker-compose up -d` |
| `.github/workflows/ci-cd.yml` | CI/CD | Git push 自动触发 |
| `scripts/security-audit.sh` | 安全审计 | `./scripts/security-audit.sh` |

## 🔧 常用命令

### 数据库
```bash
python -m src.database.migrations status     # 查看状态
python -m src.database.migrations migrate    # 应用迁移
python -m src.database.migrations rollback   # 回滚
```

### 备份
```bash
python -m src.database.backup create         # 创建备份
python -m src.database.backup list           # 列出备份
python -m src.database.backup restore <file> # 恢复备份
```

### Docker
```bash
docker build -t qa-system:latest .           # 构建镜像
docker-compose up -d                         # 启动服务
docker-compose logs -f qa-app                # 查看日志
docker-compose exec qa-app bash              # 进入容器
```

### 监控
```bash
curl http://localhost:5001/metrics           # Prometheus 格式
curl http://localhost:5001/api/metrics       # JSON 格式
```

## 📊 服务端口

| 服务 | 端口 | URL |
|------|------|-----|
| QA 应用 | 5001 | http://localhost:5001 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3000 | http://localhost:3000 |

## 📚 文档导航

| 需求 | 文档 |
|------|------|
| 快速上手 | `P2_QUICKSTART.md` |
| 完整指南 | `P2_COMPLETE_GUIDE.md` |
| 验证报告 | `P2_VALIDATION_REPORT.md` |
| 总结报告 | `FINAL_P2_SUMMARY.md` |
| 文件清单 | `P2_FILE_CHECKLIST.md` |

## 🐛 故障排查

### 服务启动失败
```bash
docker-compose logs qa-app --tail=50
docker-compose restart qa-app
```

### 数据库问题
```bash
python -m src.database.migrations status
sqlite3 data/records.db "PRAGMA integrity_check;"
```

### 监控不工作
```bash
curl http://localhost:5001/metrics
docker-compose restart prometheus grafana
```

## ✅ 验证检查表

- [x] 数据库迁移成功
- [x] 模块可正常导入
- [x] 指标输出正常
- [ ] Docker 构建成功 (需 Docker 环境)
- [ ] 安全审计通过 (需联网)
- [ ] Grafana 仪表板配置
- [ ] 生产环境部署

---

**最后更新**: 2025-11-06
**P2 状态**: ✅ 核心功能验证通过
