# Repository Guidelines

## Project Structure & Module Organization
- `main.py` 是 CLI 入口，负责题目出题、判分、日志写入和错题复练调度。
- `src/` 下的核心模块：`knowledge_loader.py`（知识解析，支持 .md/.txt/.pdf，≤700KB）、`question_generator.py`（题生成）、`question_models.py`（题目数据结构）、`ai_client.py`（大模型接口）以及 `record_manager.py`（作答历史与错题本持久化）。
- `docs/Knowledge/` 存放 Markdown 知识源，保留表格结构以便解析。
- `data/` 会自动生成，包含 `answer_history.jsonl`（JSON Lines 的答题记录）与 `wrong_questions.json`（错题题面与解析缓存）。
- `AI_cf/cf.json` 为大模型配置文件（Bearer token、endpoint、model、timeout）。
- 临时测试脚本统一放在仓库根目录，命名为 `test_*.py` 方便批量运行。

## Build, Test, and Development Commands
- `python main.py --count 5` runs a five-question sequential quiz using local knowledge.
- `python main.py --mode random --seed 42` shuffles questions deterministically; use during manual QA.
- `python main.py --enable-ai --ai-questions 3` pulls three additional questions from the configured AI service.
- `python main.py --review-wrong` drills the stored wrong-question bank; correct answers automatically drop from the list.
- `python main.py --knowledge-file path/to/file.md` 加载上传的知识文件（建议控制在 700KB 以内，PDF 需 PyPDF2）。
- `python manage_ai_config.py wizard` 运行交互式向导以录入/测试/保存 AI 配置。
- Offline validation: `python -m compileall src main.py` ensures the codebase is syntax-clean.

## Coding Style & Naming Conventions
- Use Python 3.10+ and standard-library typing (`from __future__ import annotations`).
- Prefer descriptive snake_case for functions/variables and PascalCase for classes (`QuestionGenerator`).
- Keep modules ASCII-only unless the knowledge source demands Unicode.
- Inline comments should explain intent, not restate code; limit to non-obvious logic blocks.
- Format imports in two groups: standard library first, then project-relative modules.

## Testing Guidelines
- Unit or integration checks should live in `test_*.py` files and rely on `pytest`-style assertions or direct `assert` statements.
- When adding AI integrations, provide mock transports (see `AIClient._post_json` shims) to keep tests offline.
- Validate quiz flows via scripted stdin, e.g. `python main.py --count 1 <<<'A'`.
- 对涉及错题或日志的改动，额外检查 `data/answer_history.jsonl`（合法 JSON Lines）和 `data/wrong_questions.json`（合法 JSON）是否保持可读。

## Commit & Pull Request Guidelines
- Follow concise, imperative commit subjects (`Add AI transport with error handling`).
- Ensure each PR description covers scope, testing evidence (`python main.py ...`), and any config changes.
- Link relevant issue IDs in the first line (`Refs #123`) and attach screenshots for user-facing changes when applicable.

## Security & Configuration Tips
- Never commit real API keys; store secrets as environment variables and reference them when composing `AI_cf/cf.json` locally.
- Avoid checking in real answer logs; scrub or delete files under `data/` before pushing shared branches.
- Scrub AI prompts and responses before logging to avoid leaking confidential knowledge base content.
