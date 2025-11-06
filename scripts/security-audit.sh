#!/bin/bash
#
# 安全审计脚本
# 检查依赖漏洞、代码安全问题、配置问题
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "安全审计开始"
echo "============================================================"
echo

# ============================================================================
# 1. 依赖漏洞扫描
# ============================================================================
echo "📦 检查依赖漏洞..."
echo "------------------------------------------------------------"

if ! command -v safety &> /dev/null; then
    echo "⚠️  Safety 未安装，正在安装..."
    pip install safety
fi

echo "运行 Safety 检查..."
safety check --json > reports/safety-report.json || true
safety check

echo

# ============================================================================
# 2. 代码静态分析 (SAST)
# ============================================================================
echo "🔍 代码静态分析..."
echo "------------------------------------------------------------"

if ! command -v bandit &> /dev/null; then
    echo "⚠️  Bandit 未安装，正在安装..."
    pip install bandit
fi

echo "运行 Bandit..."
bandit -r src/ -f json -o reports/bandit-report.json || true
bandit -r src/ -ll

echo

# ============================================================================
# 3. Semgrep 扫描
# ============================================================================
echo "🔎 运行 Semgrep..."
echo "------------------------------------------------------------"

if ! command -v semgrep &> /dev/null; then
    echo "⚠️  Semgrep 未安装，正在安装..."
    pip install semgrep
fi

semgrep --config=auto src/ --json > reports/semgrep-report.json || true
semgrep --config=auto src/ --verbose

echo

# ============================================================================
# 4. 密钥泄露检测
# ============================================================================
echo "🔐 检查密钥泄露..."
echo "------------------------------------------------------------"

if ! command -v gitleaks &> /dev/null; then
    echo "⚠️  Gitleaks 未安装，跳过..."
else
    gitleaks detect --source . --report-path reports/gitleaks-report.json || true
fi

echo

# ============================================================================
# 5. 依赖许可证检查
# ============================================================================
echo "📜 检查依赖许可证..."
echo "------------------------------------------------------------"

if ! command -v pip-licenses &> /dev/null; then
    pip install pip-licenses
fi

pip-licenses --format=json --output-file=reports/licenses.json
pip-licenses

echo

# ============================================================================
# 6. Docker 镜像扫描（如果存在）
# ============================================================================
if [ -f "Dockerfile" ]; then
    echo "🐳 扫描 Docker 镜像..."
    echo "------------------------------------------------------------"

    if command -v trivy &> /dev/null; then
        docker build -t qa-system:audit .
        trivy image qa-system:audit --format json > reports/trivy-report.json || true
        trivy image qa-system:audit
    else
        echo "⚠️  Trivy 未安装，跳过 Docker 扫描"
        echo "   安装: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
    fi
    echo
fi

# ============================================================================
# 7. 配置安全检查
# ============================================================================
echo "⚙️  检查配置安全..."
echo "------------------------------------------------------------"

# 检查敏感文件权限
echo "检查文件权限..."
if [ -f "data/api_key.txt" ]; then
    PERMS=$(stat -c '%a' data/api_key.txt 2>/dev/null || stat -f '%Lp' data/api_key.txt)
    if [ "$PERMS" != "600" ]; then
        echo "⚠️  警告: data/api_key.txt 权限不安全 ($PERMS)"
        echo "   建议运行: chmod 600 data/api_key.txt"
    else
        echo "✅ data/api_key.txt 权限正确"
    fi
fi

# 检查 .env 文件
if [ -f ".env" ]; then
    PERMS=$(stat -c '%a' .env 2>/dev/null || stat -f '%Lp' .env)
    if [ "$PERMS" != "600" ]; then
        echo "⚠️  警告: .env 权限不安全 ($PERMS)"
        echo "   建议运行: chmod 600 .env"
    else
        echo "✅ .env 权限正确"
    fi
fi

# 检查 Git 配置
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo
    echo "检查 Git 配置..."

    # 检查是否忽略了敏感文件
    SENSITIVE_FILES=("data/api_key.txt" ".env" "data/records.db" "AI_cf/cf.json")
    for file in "${SENSITIVE_FILES[@]}"; do
        if git check-ignore -q "$file"; then
            echo "✅ $file 已在 .gitignore 中"
        else
            echo "⚠️  警告: $file 未被 Git 忽略"
        fi
    done
fi

echo

# ============================================================================
# 8. 生成汇总报告
# ============================================================================
echo "📊 生成汇总报告..."
echo "------------------------------------------------------------"

python - << 'PYTHON_SCRIPT'
import json
from pathlib import Path
from datetime import datetime

# 创建报告目录
reports_dir = Path("reports")
reports_dir.mkdir(exist_ok=True)

# 汇总报告
summary = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "safety": {},
    "bandit": {},
    "semgrep": {},
    "summary": {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }
}

# Safety
safety_file = reports_dir / "safety-report.json"
if safety_file.exists():
    with open(safety_file) as f:
        safety_data = json.load(f)
        summary["safety"] = {
            "vulnerabilities": len(safety_data),
        }
        summary["summary"]["high"] += len(safety_data)

# Bandit
bandit_file = reports_dir / "bandit-report.json"
if bandit_file.exists():
    with open(bandit_file) as f:
        bandit_data = json.load(f)
        summary["bandit"] = bandit_data.get("metrics", {})

        for result in bandit_data.get("results", []):
            severity = result.get("issue_severity", "").lower()
            if severity == "high":
                summary["summary"]["high"] += 1
            elif severity == "medium":
                summary["summary"]["medium"] += 1
            elif severity == "low":
                summary["summary"]["low"] += 1

# Semgrep
semgrep_file = reports_dir / "semgrep-report.json"
if semgrep_file.exists():
    with open(semgrep_file) as f:
        semgrep_data = json.load(f)
        summary["semgrep"] = {
            "errors": len(semgrep_data.get("errors", [])),
            "results": len(semgrep_data.get("results", [])),
        }

# 保存汇总
with open(reports_dir / "audit-summary.json", "w") as f:
    json.dump(summary, f, indent=2)

# 打印汇总
print("安全审计汇总:")
print(f"  严重: {summary['summary']['critical']}")
print(f"  高危: {summary['summary']['high']}")
print(f"  中危: {summary['summary']['medium']}")
print(f"  低危: {summary['summary']['low']}")
PYTHON_SCRIPT

echo

# ============================================================================
# 完成
# ============================================================================
echo "============================================================"
echo "✅ 安全审计完成"
echo "============================================================"
echo
echo "报告保存在 reports/ 目录"
echo "  - safety-report.json       依赖漏洞"
echo "  - bandit-report.json       代码安全"
echo "  - semgrep-report.json      静态分析"
echo "  - audit-summary.json       汇总报告"
echo

# 退出码
mkdir -p reports
if [ -f "reports/audit-summary.json" ]; then
    HIGH=$(python -c "import json; print(json.load(open('reports/audit-summary.json'))['summary']['high'])")
    if [ "$HIGH" -gt 5 ]; then
        echo "⚠️  发现 $HIGH 个高危问题，请立即修复！"
        exit 1
    fi
fi

exit 0
