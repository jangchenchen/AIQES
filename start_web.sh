#!/bin/bash

# 答题考试系统（AI版）启动脚本

echo "========================================================"
echo "答题考试系统（AI版）"
echo "========================================================"
echo ""

# 检查依赖
echo "📦 检查依赖..."
if ! python -c "import flask" 2>/dev/null; then
    echo "❌ Flask 未安装，正在安装..."
    pip install -r requirements-web.txt
fi

echo "✅ 依赖检查完成"
echo ""

# 创建必要的目录
mkdir -p uploads data AI_cf

# 启动服务器
echo "🚀 启动 Web 服务器..."
echo "访问地址: http://localhost:5001"
echo "按 Ctrl+C 停止服务器"
echo ""

python web_server.py
