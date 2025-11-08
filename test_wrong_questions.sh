#!/bin/bash
# 错题本功能测试脚本

echo "======================================"
echo "错题本功能测试"
echo "======================================"

# 确保服务器运行在 5001 端口
SERVER="http://localhost:5001"

echo ""
echo "1. 测试错题统计 API"
curl -s "$SERVER/api/wrong-questions/stats" | python -m json.tool

echo ""
echo "2. 测试错题列表 API（第1页，每页10条）"
curl -s "$SERVER/api/wrong-questions?page=1&page_size=10" | python -m json.tool

echo ""
echo "3. 测试创建错题复练会话"
curl -s -X POST "$SERVER/api/wrong-questions/practice" \
  -H "Content-Type: application/json" \
  -d '{"count": 2, "mode": "random"}' | python -m json.tool

echo ""
echo "======================================"
echo "测试完成！"
echo "访问 http://localhost:5001/web/wrong-questions/index.html 查看前端页面"
echo "======================================"
