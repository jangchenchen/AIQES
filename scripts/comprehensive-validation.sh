#!/bin/bash
# P0 + P1 + P2 全面验证脚本
# 验证所有安全修复、架构改进和系统改进

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0

echo "══════════════════════════════════════════════════════════════"
echo "           P0 + P1 + P2 全面验证脚本"
echo "══════════════════════════════════════════════════════════════"
echo ""

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
    ((SKIPPED++))
}

# ============================================================================
# P0 验证：紧急安全修复
# ============================================================================

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}P0 验证：紧急安全修复${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# P0.1: CORS + 速率限制 + API 鉴权
test_step "P0.1: 检查 CORS 配置"
if grep -q "CORS(app" web_server.py && grep -q "origins=" web_server.py; then
    test_pass
else
    test_fail "web_server.py 未配置 CORS"
fi

test_step "P0.2: 检查 API 鉴权"
if grep -q "API_KEY" web_server.py || grep -q "check_api_key" web_server.py; then
    test_pass
else
    test_fail "未找到 API 鉴权实现"
fi

test_step "P0.3: 检查速率限制"
if grep -q "Limiter" web_server.py || grep -q "limiter" web_server.py; then
    test_pass
else
    test_fail "未找到速率限制实现"
fi

# P0.2: 文件上传安全
test_step "P0.4: 检查文件验证器"
if [ -f "src/utils/file_validator.py" ]; then
    test_pass
else
    test_fail "src/utils/file_validator.py 不存在"
fi

test_step "P0.5: 检查 MIME 类型验证"
if [ -f "src/utils/file_validator.py" ]; then
    if grep -q "python-magic\|magic" src/utils/file_validator.py; then
        test_pass
    else
        test_fail "未使用 python-magic 进行 MIME 验证"
    fi
else
    test_skip "file_validator.py 不存在"
fi

test_step "P0.6: 检查文件大小限制"
if grep -q "MAX.*SIZE\|max.*size" src/utils/file_validator.py src/knowledge_loader.py 2>/dev/null; then
    test_pass
else
    test_fail "未找到文件大小限制"
fi

test_step "P0.7: 检查随机文件名生成"
if grep -q "uuid\|random.*filename" web_server.py src/utils/file_validator.py 2>/dev/null; then
    test_pass
else
    test_fail "未使用随机文件名"
fi

# P0.3: 会话并发安全
test_step "P0.8: 检查会话管理器"
if [ -f "src/session_manager.py" ]; then
    test_pass
else
    test_fail "src/session_manager.py 不存在"
fi

test_step "P0.9: 检查线程锁"
if [ -f "src/session_manager.py" ]; then
    if grep -q "threading.Lock\|Lock()" src/session_manager.py; then
        test_pass
    else
        test_fail "会话管理器未使用线程锁"
    fi
else
    test_skip "session_manager.py 不存在"
fi

test_step "P0.10: 检查 RecordManager 线程安全"
if grep -q "Lock\|threading" src/record_manager.py 2>/dev/null; then
    test_pass
else
    test_fail "RecordManager 未实现线程安全"
fi

# P0.4: 会话 TTL 和清理
test_step "P0.11: 检查会话 TTL 配置"
if [ -f "src/session_manager.py" ]; then
    if grep -q "ttl\|TTL\|expire\|timeout" src/session_manager.py; then
        test_pass
    else
        test_fail "未找到 TTL 配置"
    fi
else
    test_skip "session_manager.py 不存在"
fi

test_step "P0.12: 检查会话清理机制"
if [ -f "src/session_manager.py" ]; then
    if grep -q "cleanup\|clean_up\|remove_expired" src/session_manager.py; then
        test_pass
    else
        test_fail "未找到清理机制"
    fi
else
    test_skip "session_manager.py 不存在"
fi

# P0.5: AI 调用保护
test_step "P0.13: 检查提示注入过滤"
if grep -q "sanitize\|filter.*prompt\|validate.*input" src/ai_client.py web_server.py 2>/dev/null; then
    test_pass
else
    test_fail "未找到提示注入过滤"
fi

test_step "P0.14: 检查 AI 重试限制"
if grep -q "max.*retr\|retry.*limit\|MAX_RETRIES" src/ai_client.py 2>/dev/null; then
    test_pass
else
    test_fail "未找到重试限制"
fi

# ============================================================================
# P1 验证：架构改进
# ============================================================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}P1 验证：架构改进${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# P1.1: SQLite 迁移
test_step "P1.1: 检查数据库模块"
if [ -f "src/database/migrations.py" ] && [ -f "src/database/backup.py" ]; then
    test_pass
else
    test_fail "数据库模块不完整"
fi

test_step "P1.2: 检查 SQLite 使用"
if grep -q "sqlite3" src/record_manager.py 2>/dev/null; then
    test_pass
else
    test_fail "RecordManager 未迁移到 SQLite"
fi

test_step "P1.3: 验证数据库迁移"
if python -m src.database.migrations status >/dev/null 2>&1; then
    test_pass
else
    test_fail "数据库迁移脚本无法运行"
fi

# P1.2: 速率限制和监控
test_step "P1.4: 检查速率限制实现"
if grep -q "limiter\|rate_limit\|RateLimiter" web_server.py 2>/dev/null; then
    test_pass
else
    test_fail "未实现完整的速率限制"
fi

test_step "P1.5: 检查 AI 费用监控"
if grep -q "token.*usage\|cost.*tracking\|usage.*log" src/ai_client.py web_server.py 2>/dev/null; then
    test_pass
else
    test_fail "未找到 AI 费用监控"
fi

# P1.3: RecordManager 单例
test_step "P1.6: 检查 RecordManager 实例化"
if grep -q "_instance\|singleton\|get_instance" src/record_manager.py 2>/dev/null; then
    test_pass
else
    test_fail "RecordManager 未使用单例模式"
fi

# P1.4: 输入验证和日志
test_step "P1.7: 检查输入验证"
if [ -f "src/utils/validators.py" ] || grep -q "validate.*input\|schema.*validation" src/ -r 2>/dev/null; then
    test_pass
else
    test_fail "未找到统一的输入验证"
fi

test_step "P1.8: 检查结构化日志"
if grep -q "import logging" web_server.py && grep -q "logger\." web_server.py; then
    test_pass
else
    test_fail "未使用结构化日志"
fi

# ============================================================================
# P2 验证：系统改进
# ============================================================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}P2 验证：系统改进${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# P2.1: 数据库迁移系统
test_step "P2.1: 数据库迁移文件"
if [ -f "src/database/migrations.py" ]; then
    test_pass
else
    test_fail "src/database/migrations.py 不存在"
fi

test_step "P2.2: 备份恢复系统"
if [ -f "src/database/backup.py" ]; then
    test_pass
else
    test_fail "src/database/backup.py 不存在"
fi

test_step "P2.3: 迁移脚本功能"
MIGRATION_COUNT=$(python -c "from src.database.migrations import MIGRATIONS; print(len(MIGRATIONS))" 2>/dev/null || echo "0")
if [ "$MIGRATION_COUNT" -ge "4" ]; then
    test_pass
else
    test_fail "迁移脚本数量不足: $MIGRATION_COUNT"
fi

# P2.2: 监控和告警
test_step "P2.4: 监控指标模块"
if [ -f "src/monitoring/metrics.py" ]; then
    test_pass
else
    test_fail "src/monitoring/metrics.py 不存在"
fi

test_step "P2.5: 告警管理器"
if [ -f "src/monitoring/alerts.py" ]; then
    test_pass
else
    test_fail "src/monitoring/alerts.py 不存在"
fi

test_step "P2.6: Prometheus 指标"
if python -c "from src.monitoring.metrics import metrics, AppMetrics; AppMetrics.http_requests_total.inc(); output = metrics.get_prometheus_metrics(); assert 'http_requests_total' in output" 2>/dev/null; then
    test_pass
else
    test_fail "Prometheus 指标输出异常"
fi

# P2.3: 容器化
test_step "P2.7: Dockerfile"
if [ -f "Dockerfile" ]; then
    test_pass
else
    test_fail "Dockerfile 不存在"
fi

test_step "P2.8: docker-compose.yml"
if [ -f "docker-compose.yml" ]; then
    test_pass
else
    test_fail "docker-compose.yml 不存在"
fi

test_step "P2.9: Docker 镜像构建"
if docker images | grep -q "qa-system"; then
    test_pass
else
    test_fail "未找到 qa-system Docker 镜像"
fi

# P2.4: CI/CD
test_step "P2.10: GitHub Actions 配置"
if [ -f ".github/workflows/ci-cd.yml" ]; then
    test_pass
else
    test_fail ".github/workflows/ci-cd.yml 不存在"
fi

# P2.5: 安全审计
test_step "P2.11: 安全审计脚本"
if [ -f "scripts/security-audit.sh" ]; then
    test_pass
else
    test_fail "scripts/security-audit.sh 不存在"
fi

test_step "P2.12: 依赖升级 (PyPDF2→pypdf)"
if grep -q "pypdf==" requirements-web.txt && ! grep -q "PyPDF2" requirements-web.txt 2>/dev/null; then
    test_pass
else
    test_fail "依赖未正确升级"
fi

# ============================================================================
# 功能集成测试
# ============================================================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}功能集成测试${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_step "集成: Python 模块导入"
if python -c "
from src.database.migrations import MigrationManager
from src.database.backup import BackupManager
from src.monitoring.metrics import MetricsCollector
from src.monitoring.alerts import AlertManager
from src.session_manager import SessionManager
from src.record_manager import RecordManager
print('OK')
" 2>/dev/null | grep -q "OK"; then
    test_pass
else
    test_fail "模块导入失败"
fi

test_step "集成: 会话管理器功能"
if python -c "
from src.session_manager import SessionManager
sm = SessionManager()
session_id = sm.create_session({'test': 'data'})
assert sm.get_session(session_id) is not None
sm.cleanup_expired()
print('OK')
" 2>/dev/null | grep -q "OK"; then
    test_pass
else
    test_fail "会话管理器功能异常"
fi

test_step "集成: 数据库操作"
if [ -f "data/records.db" ]; then
    if sqlite3 data/records.db "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        test_pass
    else
        test_fail "数据库完整性检查失败"
    fi
else
    test_skip "数据库文件不存在"
fi

# ============================================================================
# 代码质量检查
# ============================================================================

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}代码质量检查${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

test_step "代码: Python 语法检查"
if python -m py_compile web_server.py src/**/*.py 2>/dev/null; then
    test_pass
else
    test_fail "Python 语法错误"
fi

test_step "代码: 导入检查"
if python -c "import web_server" 2>/dev/null; then
    test_pass
else
    test_fail "web_server.py 无法导入"
fi

# ============================================================================
# 总结
# ============================================================================

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "验证总结"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}✅ 通过: $PASSED${NC}"
echo -e "${RED}❌ 失败: $FAILED${NC}"
echo -e "${YELLOW}⏭️  跳过: $SKIPPED${NC}"
echo ""

TOTAL=$((PASSED + FAILED))
if [ $TOTAL -gt 0 ]; then
    PASS_RATE=$((PASSED * 100 / TOTAL))
    echo "通过率: $PASS_RATE% ($PASSED/$TOTAL)"
fi

echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 所有测试通过！P0+P1+P2 全部验证成功。${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}⚠️  发现 $FAILED 个问题，请检查上述错误信息。${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "修复建议："
    echo "1. 检查上述标记为 ❌ 的项目"
    echo "2. 查看相关文档了解修复方法"
    echo "3. 修复后重新运行此脚本"
    exit 1
fi
