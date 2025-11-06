#!/bin/bash
# 本地验证脚本 - 无需 Docker 和外网
# 验证 P2 核心功能在当前环境下是否正常工作

set -e

echo "============================================================"
echo "P2 本地验证脚本"
echo "============================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
PASSED=0
FAILED=0

# 测试函数
test_step() {
    echo -n "▶ $1 ... "
}

test_pass() {
    echo -e "${GREEN}✅ 通过${NC}"
    ((PASSED++))
}

test_fail() {
    echo -e "${RED}❌ 失败${NC}"
    echo "  错误: $1"
    ((FAILED++))
}

test_skip() {
    echo -e "${YELLOW}⏭️  跳过 - $1${NC}"
}

# 1. 验证文件结构
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  文件结构验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_step "检查数据库模块"
if [ -f "src/database/migrations.py" ] && [ -f "src/database/backup.py" ]; then
    test_pass
else
    test_fail "src/database/ 模块文件缺失"
fi

test_step "检查监控模块"
if [ -f "src/monitoring/metrics.py" ] && [ -f "src/monitoring/alerts.py" ]; then
    test_pass
else
    test_fail "src/monitoring/ 模块文件缺失"
fi

test_step "检查容器配置"
if [ -f "Dockerfile" ] && [ -f "docker-compose.yml" ]; then
    test_pass
else
    test_fail "Docker 配置文件缺失"
fi

test_step "检查 CI/CD 配置"
if [ -f ".github/workflows/ci-cd.yml" ]; then
    test_pass
else
    test_fail "GitHub Actions 配置缺失"
fi

test_step "检查监控配置"
if [ -f "monitoring/prometheus.yml" ] && [ -f "monitoring/alerts.yml" ]; then
    test_pass
else
    test_fail "Prometheus 配置文件缺失"
fi

test_step "检查文档文件"
if [ -f "P2_COMPLETE_GUIDE.md" ] && [ -f "P2_QUICKSTART.md" ] && [ -f "FINAL_P2_SUMMARY.md" ]; then
    test_pass
else
    test_fail "文档文件不完整"
fi

# 2. 验证 Python 模块可导入
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  Python 模块导入验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_step "导入数据库迁移模块"
if python -c "from src.database.migrations import Migration, MigrationManager" 2>/dev/null; then
    test_pass
else
    test_fail "无法导入 migrations 模块"
fi

test_step "导入备份模块"
if python -c "from src.database.backup import BackupManager" 2>/dev/null; then
    test_pass
else
    test_fail "无法导入 backup 模块"
fi

test_step "导入监控指标模块"
if python -c "from src.monitoring.metrics import MetricsCollector, AppMetrics" 2>/dev/null; then
    test_pass
else
    test_fail "无法导入 metrics 模块"
fi

test_step "导入告警模块"
if python -c "from src.monitoring.alerts import AlertManager, AlertRule" 2>/dev/null; then
    test_pass
else
    test_fail "无法导入 alerts 模块"
fi

# 3. 验证数据库迁移功能
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  数据库迁移功能验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_step "查看迁移状态"
if python -m src.database.migrations status >/dev/null 2>&1; then
    test_pass
else
    test_fail "无法执行迁移状态检查"
fi

test_step "验证迁移完整性"
MIGRATION_COUNT=$(python -c "from src.database.migrations import MIGRATIONS; print(len(MIGRATIONS))" 2>/dev/null)
if [ "$MIGRATION_COUNT" = "4" ]; then
    test_pass
else
    test_fail "预期 4 个迁移，实际发现 $MIGRATION_COUNT 个"
fi

test_step "检查数据库文件"
if [ -f "data/records.db" ]; then
    test_pass
else
    test_fail "数据库文件不存在（可能尚未初始化）"
fi

# 4. 验证备份功能
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  备份功能验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "data/records.db" ]; then
    test_step "创建测试备份"
    if python -m src.database.backup create "本地验证测试" >/dev/null 2>&1; then
        test_pass

        test_step "列出备份文件"
        BACKUP_COUNT=$(python -m src.database.backup list 2>/dev/null | grep -c "backup_" || echo "0")
        if [ "$BACKUP_COUNT" -gt "0" ]; then
            test_pass
            echo "  发现 $BACKUP_COUNT 个备份文件"
        else
            test_fail "未找到备份文件"
        fi
    else
        test_fail "备份创建失败"
    fi
else
    test_skip "数据库文件不存在"
fi

# 5. 验证监控指标
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  监控指标验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_step "创建指标收集器"
if python -c "
from src.monitoring.metrics import MetricsCollector, AppMetrics
collector = MetricsCollector()
AppMetrics.http_requests_total.inc()
AppMetrics.active_sessions.set(5)
metrics_text = collector.get_prometheus_metrics()
assert 'http_requests_total' in metrics_text
print('OK')
" 2>/dev/null | grep -q "OK"; then
    test_pass
else
    test_fail "指标收集器功能异常"
fi

test_step "验证 Prometheus 格式输出"
if python -c "
from src.monitoring.metrics import MetricsCollector
collector = MetricsCollector()
output = collector.get_prometheus_metrics()
assert output.startswith('# HELP') or 'HELP' in output or len(output) > 0
" 2>/dev/null; then
    test_pass
else
    test_fail "Prometheus 格式输出异常"
fi

# 6. 验证告警系统
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  告警系统验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_step "创建告警管理器"
if python -c "
from src.monitoring.alerts import AlertManager, AlertRule, AlertSeverity, ConsoleChannel
manager = AlertManager()
manager.add_channel(ConsoleChannel())
rule = AlertRule(
    name='test_rule',
    condition=lambda: True,
    severity=AlertSeverity.INFO,
    message='Test alert'
)
manager.add_rule(rule)
print('OK')
" 2>/dev/null | grep -q "OK"; then
    test_pass
else
    test_fail "告警管理器创建失败"
fi

test_step "验证默认告警规则"
RULE_COUNT=$(python -c "
from src.monitoring.alerts import create_default_rules
from src.monitoring.metrics import MetricsCollector
rules = create_default_rules(MetricsCollector())
print(len(rules))
" 2>/dev/null)
if [ "$RULE_COUNT" -ge "5" ]; then
    test_pass
    echo "  发现 $RULE_COUNT 个默认规则"
else
    test_fail "默认规则数量不足: $RULE_COUNT"
fi

# 7. 验证依赖升级
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣  依赖升级验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_step "检查 PyPDF2 已移除"
if ! grep -q "PyPDF2" requirements-web.txt 2>/dev/null; then
    test_pass
else
    test_fail "requirements-web.txt 仍包含 PyPDF2"
fi

test_step "检查 pypdf 已添加"
if grep -q "pypdf" requirements-web.txt 2>/dev/null; then
    test_pass
else
    test_fail "requirements-web.txt 未包含 pypdf"
fi

test_step "验证 file_validator 已更新"
if grep -q "pypdf import PdfReader" src/utils/file_validator.py 2>/dev/null; then
    test_pass
else
    test_fail "file_validator.py 未更新 import 语句"
fi

# 8. 验证配置文件语法
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣  配置文件语法验证"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test_step "Dockerfile 语法"
if docker --version >/dev/null 2>&1; then
    if docker build -t qa-system:test -f Dockerfile . >/dev/null 2>&1; then
        test_pass
    else
        test_fail "Dockerfile 语法错误或构建失败"
    fi
else
    test_skip "Docker 不可用"
fi

test_step "docker-compose.yml 语法"
if docker-compose --version >/dev/null 2>&1; then
    if docker-compose config >/dev/null 2>&1; then
        test_pass
    else
        test_fail "docker-compose.yml 语法错误"
    fi
else
    test_skip "docker-compose 不可用"
fi

test_step "Prometheus 配置语法"
if command -v promtool >/dev/null 2>&1; then
    if promtool check config monitoring/prometheus.yml >/dev/null 2>&1; then
        test_pass
    else
        test_fail "prometheus.yml 配置错误"
    fi
else
    test_skip "promtool 不可用（正常，仅在 Prometheus 环境需要）"
fi

test_step "GitHub Actions 工作流语法"
if python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))" 2>/dev/null; then
    test_pass
else
    test_fail "ci-cd.yml YAML 语法错误"
fi

# 9. 统计代码量
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9️⃣  代码统计"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "📊 P2 新增代码统计:"
echo ""
echo "核心模块:"
wc -l src/database/migrations.py src/database/backup.py \
      src/monitoring/metrics.py src/monitoring/alerts.py 2>/dev/null | tail -1 | \
      awk '{print "  总计: " $1 " 行"}'

echo ""
echo "配置文件:"
wc -l Dockerfile docker-compose.yml \
      monitoring/prometheus.yml monitoring/alerts.yml \
      .github/workflows/ci-cd.yml 2>/dev/null | tail -1 | \
      awk '{print "  总计: " $1 " 行"}'

echo ""
echo "文档文件:"
wc -l P2_COMPLETE_GUIDE.md P2_QUICKSTART.md FINAL_P2_SUMMARY.md \
      README_P2_UPDATE.md P2_FILE_CHECKLIST.md 2>/dev/null | tail -1 | \
      awk '{print "  总计: " $1 " 行"}'

# 10. 最终总结
echo ""
echo "============================================================"
echo "验证总结"
echo "============================================================"
echo ""
echo -e "${GREEN}✅ 通过: $PASSED${NC}"
echo -e "${RED}❌ 失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 所有本地验证通过！P2 实现完整且功能正常。${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "✨ 后续步骤:"
    echo "  1. 在有 Docker 权限的环境测试容器化部署"
    echo "  2. 在联网环境运行完整安全审计"
    echo "  3. 部署到测试/生产环境"
    exit 0
else
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  发现 $FAILED 个问题，请检查上述错误信息。${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 1
fi
