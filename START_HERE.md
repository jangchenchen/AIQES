# 🚀 答题考试系统（AI版）- 快速开始

## 5秒启动

```bash
python web_server.py
```

然后在浏览器打开：**http://localhost:5001**

---

## 完整的功能

✅ **上传知识文件** - 支持 txt/md/pdf，拖拽上传
✅ **配置题目参数** - 选择题型、数量、顺序
✅ **开始答题** - 4种题型实时判分
✅ **查看结果** - 得分统计、答题历史
✅ **AI 智能出题** - 可选功能（点击侧边栏"⚙️ AI 配置"）

---

## 使用流程

1. **上传知识文件**
   点击上传区域或拖拽文件（txt/md/pdf，≤700KB）

2. **配置参数**
   - 选择题型：单选、多选、填空、问答
   - 设置题目数量：1-100 题
   - 选择顺序：顺序或随机

3. **开始答题**
   - 单选/多选：点击选项
   - 填空/问答：输入文本
   - 提交后立即显示正确答案和解析

4. **查看结果**
   - 最终得分（百分比）
   - 正确题数/总题数
   - 可重新开始

---

## AI 配置（可选）

1. 点击侧边栏 **"⚙️ AI 配置"** 按钮（新标签页打开）
2. 或直接访问: http://localhost:5001/web/ai-config/index.html
3. 填写 API 信息：
   - **URL**: `https://api.openai.com/v1/chat/completions`
   - **Key**: `sk-your-api-key`
   - **Model**: `gpt-4o-mini`
4. 测试连通性并保存
5. 在"题目配置"中设置"AI 生成题目数量"

> **提示**: 所有 AI 配置 API 现已集成到 Flask 服务器 (端口 5001)，无需单独启动 FastAPI 服务器。

---

## 文件结构

```
.
├── web_server.py              # Web 服务器（启动这个！）
├── frontend/
│   ├── app.html              # 前端页面
│   └── assets/
│       ├── app.js            # 前端逻辑
│       └── styles.css        # 样式
├── data/
│   ├── answer_history.jsonl  # 答题历史
│   └── wrong_questions.json   # 错题本
└── uploads/                   # 上传的知识文件
```

---

## 端口被占用？

修改 `web_server.py` 最后一行：
```python
app.run(debug=True, host='0.0.0.0', port=5002)  # 改成其他端口
```

同时修改 `frontend/assets/app.js` 第 5 行：
```javascript
const API_BASE = 'http://localhost:5002/api';
```

---

## 详细文档

- **DEPLOYMENT_GUIDE.md** - 完整的部署和使用指南
- **WEB_README.md** - API 接口文档

---

## 特色功能

- ✅ 无需用户系统 - 开箱即用
- ✅ 文件拖拽上传 - 用户体验好
- ✅ 实时判分反馈 - 即时显示结果
- ✅ 答题历史追踪 - 数据持久化
- ✅ 错题自动管理 - 智能学习
- ✅ AI 智能出题 - 可选功能

---

**🎉 祝您使用愉快！**
