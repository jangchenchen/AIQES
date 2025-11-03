# 电梯安全知识点问答系统

一个基于自定义知识文档的轻量化问答训练脚本，涵盖单选、多选、完形填空与问答题型，可顺序或随机出题，并支持接入大模型补充题库。

## 功能概览
- 自动解析 `docs/Knowledge/电梯安全装置维护程序.md` 中的表格，提取关键句生成题干与答案。
- 支持题型筛选：`single`（单选）、`multi`（多选）、`cloze`（完形填空）、`qa`（问答）。
- 支持顺序或随机出题，限制题目数量，保留关键要点讲解。
- 每题自动输出大白话解析，帮助快速理解考点。
- 自动记录答题历史到 `data/answer_history.jsonl`，并维护错题本 `data/wrong_questions.json`。
- 支持自定义知识文件上传（`.md` / `.txt` / `.pdf`，≤700KB），解析后可直接用于生题或 AI 生成。
- 通过 `AI_cf/cf.json` 加载大模型配置，可向外部接口请求额外题目，并提供错题复练（`--review-wrong`）。

## 环境要求
- Python 3.10 及以上版本。
- 当前实现仅依赖标准库；若需网络访问，请确认终端具备外网权限。

## 快速开始
```bash
python main.py --count 5                 # 顺序答题，限制 5 题
python main.py --mode random             # 随机出题
python main.py --types single multi      # 仅针对客观题训练
python main.py --enable-ai               # 加载 AI 配置
python main.py --enable-ai --ai-questions 3  # 向大模型请求 3 道新增题
python main.py --review-wrong            # 练习历史错题
python main.py --knowledge-file data/sample.md  # 使用自定义知识文件练习
python manage_ai_config.py wizard        # 交互式配置/测试 AI 接口
uvicorn server.app:app --reload          # 启动 AI 配置 API 服务
```

- 单选题输入 `A`、`B` 等字母。
- 多选题可输入 `AC`、`A,C` 或 `A, C`。
- 填空题直接输入文本，问答题可输入完整语句以便关键词匹配。
- 每题都会追加“解析”行，总结正确做法和记忆要点。

### 答题记录与错题复练
- 所有作答会追加到 `data/answer_history.jsonl`（JSON 行格式），方便后续统计或导入 BI 工具。
- 错题自动进入 `data/wrong_questions.json`。使用 `python main.py --review-wrong` 按原题再次练习，答对会自动移除。

### 知识文件上传说明
- 支持 `.md`、`.txt` 与 `.pdf`（PDF 需 `PyPDF2`）格式，限制 700KB 以内以保障 AI 请求性能。
- Markdown 优先解析表格结构；若无表格，则按段落拆分为知识点。
- 文本/PDF 会按段落自动切分成知识点，首行默认视为知识点标题。
- 通过 `--knowledge-file` 传入自定义文件，可结合 `--enable-ai` 让大模型基于新知识点出题。

### AI 配置工具
- CLI：`manage_ai_config.py` 支持 `wizard`、`set`、`show`、`test`、`delete` 等子命令，可保存配置并测试连通性（若当前环境无外网则会提示失败原因）。
- 前端样板：桌面端弹窗、移动端底部抽屉均提供 URL、Key、模型输入与“测试/保存/删除”按钮，便于后续接入真实服务。
- API 服务：运行 `uvicorn server.app:app --reload` 启动 FastAPI 接口，前端页面 `web/ai-config/index.html` 通过 `/api/ai-config` 系列端点读取/保存配置、模拟连通性测试。
- URL 将自动补全为 `/v1/chat/completions`，无需手动填写完整路径。

## AI 扩展说明
- `src/ai_client.py` 实现了基于 HTTP 的通用调用逻辑：读取 `AI_cf/cf.json`，使用 Bearer Token 将请求 POST 到配置的 `url`。
- 默认请求体遵循类 OpenAI Chat Completion 的格式，系统提示会要求模型输出严格的 JSON 数组，字段包括 `id`、`type`、`prompt`、`options`、`answer` 等。
- CLI 参数：
  - `--enable-ai`：读取配置并初始化客户端。
  - `--ai-questions N`：请求 N 道额外题，生成成功后并入题库。
  - `--ai-temperature`：自定义外部模型的 temperature 参数（默认 0.7）。
- 若网络不可用或模型不返回合法 JSON，会提示错误并继续使用本地题库，确保系统可用。

## 目录结构
```
├── AI_cf/cf.json             # AI 模型配置（key、url、model、timeout）
├── data/                     # 答题历史与错题本数据目录
│   ├── answer_history.jsonl  # 逐题作答记录（JSON Lines）
│   └── wrong_questions.json  # 错题题面及解析缓存
├── docs/Knowledge/           # 默认示例知识文档，可替换为自定义文件
├── src/
│   ├── knowledge_loader.py   # 知识文件解析（.md/.txt/.pdf）
│   ├── question_models.py    # 题目数据结构
│   ├── question_generator.py # 各类题型生成逻辑
│   ├── ai_client.py          # AI 问题生成与配置加载
│   └── record_manager.py     # 作答日志与错题管理
├── server/app.py             # FastAPI 服务，承载 AI 配置 REST 接口
└── web/ai-config/            # AI 配置前端页面（HTML/CSS/JS）
```

## 后续可拓展点
1. 按需调整大模型提示词或响应解析逻辑，适配企业内部 API 协议。
2. 在错题模式基础上扩展错因标签、计划化复练策略。
3. 结合前端（如 Streamlit、Vue）封装图形化界面，便于非技术人员使用。
4. 引入更智能的关键词提取或文本相似度算法，提高问答题自动评分准确度。
