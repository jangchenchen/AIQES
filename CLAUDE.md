# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a quiz/exam system (答题考试系统 AI版) designed for knowledge-based training and assessment. It supports multiple question types (single-choice, multi-choice, fill-in-blank, Q&A), automated question generation from knowledge documents, and optional AI integration for enhanced question generation.

The system operates in two modes:
1. **CLI Mode** (`main.py`) - Terminal-based quiz interface with session management
2. **Web Mode** (`web_server.py`) - REST API server with modern web interface

## Development Commands

### Running the Application

```bash
# Web Server Mode (Primary interface)
python web_server.py
# Access at: http://localhost:5001

# CLI Mode (Terminal interface)
python main.py                              # Use default knowledge file
python main.py --count 5 --mode random      # 5 random questions
python main.py --types single multi         # Objective questions only
python main.py --review-wrong               # Practice wrong questions
python main.py --knowledge-file path.md     # Use custom knowledge file

# AI Configuration Management
python manage_ai_config.py wizard           # Interactive AI setup
python manage_ai_config.py show             # Show current config
python manage_ai_config.py test             # Test connectivity
python manage_ai_config.py delete           # Remove config

# Alternative FastAPI server (deprecated, now integrated into Flask)
uvicorn server.app:app --reload             # Port 8000
```

### Dependency Management

```bash
pip install -r requirements-web.txt         # Web server dependencies (Flask)
pip install -r requirements.txt             # CLI dependencies (optional)
```

### File Size Limits

- Knowledge files: ≤ 700KB (enforced in `knowledge_loader.py`)
- Supported formats: `.txt`, `.md`, `.pdf`
- Uploads stored in: `uploads/` with UUID filenames

## Architecture Overview

### Two-Tier Architecture

The system has evolved to a **unified Flask server** architecture:

```
┌─────────────────────────────────────────────────────────┐
│           Flask Web Server (web_server.py)              │
│                   Port 5001                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Quiz API Routes          AI Config Routes              │
│  ├── /api/upload-knowledge   ├── GET /api/ai-config     │
│  ├── /api/generate-questions ├── PUT /api/ai-config     │
│  ├── /api/get-question       ├── POST /api/ai-config/test│
│  ├── /api/submit-answer      └── DELETE /api/ai-config  │
│  └── /api/session-status                                │
│                                                          │
│  Static File Serving                                    │
│  ├── /            → frontend/app.html (main UI)         │
│  └── /web/        → web/ (AI config UI)                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
         ↓                         ↓
┌────────────────┐        ┌──────────────────┐
│  Core Modules  │        │  Data Storage    │
│  src/          │        │  ├── uploads/    │
│                │        │  ├── data/       │
│                │        │  └── AI_cf/      │
└────────────────┘        └──────────────────┘
```

**Important**: The FastAPI server (`server/app.py`) routes have been integrated into `web_server.py`. Do not run both servers simultaneously.

### Core Module Responsibilities

#### `src/knowledge_loader.py`
- Parses knowledge files (`.txt`, `.md`, `.pdf`)
- Extracts knowledge entries from tables or paragraphs
- Returns `KnowledgeEntry` objects with `component`, `process`, `raw_text`
- Markdown: prioritizes table parsing; fallback to paragraph splitting
- Text/PDF: splits by double newlines into knowledge entries

#### `src/question_generator.py`
- Generates questions from knowledge entries
- Creates 4 question types: SINGLE_CHOICE, MULTI_CHOICE, CLOZE, QA
- Uses heuristics to determine appropriate question type per entry
- Returns `Question` objects with prompts, options, answers, explanations

#### `src/question_models.py`
- Defines core data structures: `QuestionType` enum, `Question` dataclass
- Question contains: identifier, type, prompt, options, correct_options, answer_text, keywords, explanation

#### `src/ai_client.py`
- Handles AI integration for additional question generation
- Loads config from `AI_cf/cf.json`
- Makes HTTP requests to OpenAI-compatible endpoints
- Parses AI responses into `Question` objects
- Gracefully handles failures without breaking main flow

#### `src/record_manager.py`
- Manages answer history and wrong question tracking
- Writes to `data/answer_history.jsonl` (JSONL format, one record per line)
- Maintains `data/wrong_questions.json` (automatically adds/removes based on performance)
- Thread-safe file operations using Path.write_text()

#### `manage_ai_config.py`
- CLI and library for AI configuration management
- Normalizes URLs (auto-appends `/v1/chat/completions` if needed)
- Tests connectivity using Bearer token authentication
- Stores config at `AI_cf/cf.json`

### Session Management (Web Mode)

Sessions are stored in-memory in `web_server.py`:

```python
sessions[session_id] = {
    "questions": [...],          # List of Question objects
    "current_index": 0,          # Current question index
    "answers": [],               # User answers history
    "correct_count": 0,          # Number correct so far
    "total_count": len(questions),
    "filepath": "...",           # Source knowledge file
}
```

**Limitation**: Sessions are lost on server restart. For production, migrate to Redis or database.

### Question Type Grading Logic

Each question type has specific grading rules in `web_server.py`:

- **Single Choice**: Letter (A/B/C/D) → index comparison
- **Multi Choice**: Multiple letters (ACD) → sorted set comparison
- **Fill-in-Blank**: Keyword matching (case-insensitive substring search)
- **Q&A**: Keyword matching with partial credit

### Frontend Architecture

Two frontend implementations exist:

1. **Main Web UI** (`frontend/app.html` + `frontend/assets/app.js`)
   - Modern SPA-style interface
   - Drag-and-drop file upload
   - Real-time question rendering
   - Progress tracking sidebar
   - AI configuration button linking to `/web/ai-config/index.html`

2. **AI Config UI** (`web/ai-config/index.html` + `script.js`)
   - Standalone configuration page
   - API URL, Key, Model input
   - Connectivity testing before save
   - Opened via button or direct URL access

Both use `fetch()` API to communicate with Flask backend on port 5001.

## Important Patterns and Conventions

### Question Type Aliases

Use string aliases in API calls, converted to enums internally:

```python
_TYPE_ALIAS = {
    "single": QuestionType.SINGLE_CHOICE,
    "multi": QuestionType.MULTI_CHOICE,
    "cloze": QuestionType.CLOZE,
    "qa": QuestionType.QA,
}
```

### Error Handling Strategy

- **AI failures**: Non-blocking; log error and continue with local questions
- **File parsing failures**: Delete uploaded file and return 400 error
- **Invalid API requests**: Return JSON error with appropriate HTTP status
- **Session not found**: Return 404 with error message

### Data Persistence

1. **Answer History**: Append-only JSONL format
   - One JSON object per line
   - Fields: timestamp, session_id, question, user_answer, is_correct, explanation

2. **Wrong Questions**: Overwrite JSON file
   - Array of question objects with metadata
   - Auto-removed when answered correctly

3. **AI Config**: Single JSON file
   - Stores API credentials and model settings
   - Auto-creates parent directory if needed

### URL Normalization

AI config URLs are automatically normalized:

```python
# Input: "https://api.openai.com/v1"
# Output: "https://api.openai.com/v1/chat/completions"

# Input: "https://api.openai.com/v1/chat/completions"
# Output: unchanged (already has suffix)
```

This prevents common configuration errors.

## Key Integration Points

### Adding New Question Types

1. Add enum value to `QuestionType` in `src/question_models.py`
2. Implement generation logic in `src/question_generator.py`
3. Add grading function in `web_server.py` (e.g., `_grade_new_type()`)
4. Update `_grade_answer()` dispatcher function
5. Add frontend rendering logic in `frontend/assets/app.js`
6. Update type alias mapping if needed

### Adding New Knowledge File Formats

1. Extend `load_knowledge_entries()` in `src/knowledge_loader.py`
2. Add file extension to allowed list in `web_server.py` upload handler
3. Implement parser that returns list of `KnowledgeEntry` objects
4. Update MAX_KNOWLEDGE_FILE_SIZE constant if needed

### Modifying AI Integration

- AI client implementation: `src/ai_client.py`
- Prompt engineering: See system message in `generate_additional_questions()`
- Response parsing: Expects JSON array with specific schema
- Configuration schema: Defined in `manage_ai_config.py` AIConfig dataclass

## Testing and Debugging

### Verify Question Generation

```bash
# Test with small sample
python main.py --count 3 --types single

# Test AI integration (requires config)
python manage_ai_config.py test
python main.py --enable-ai --ai-questions 2
```

### Check Data Files

```bash
# View recent answer history
tail -5 data/answer_history.jsonl | python -m json.tool

# Check wrong questions
cat data/wrong_questions.json | python -m json.tool

# Verify AI config
python manage_ai_config.py show
```

### Web Server Debugging

```bash
# Start server with debug output
python web_server.py
# Flask debug mode is enabled by default (debug=True)

# Test API endpoints
curl http://localhost:5001/api/ai-config
curl -X POST http://localhost:5001/api/session-status \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test-uuid"}'
```

### Port Conflicts

If port 5001 is in use:

1. Change port in `web_server.py` (last line): `app.run(..., port=5002)`
2. Update API_BASE in `frontend/assets/app.js`: `const API_BASE = 'http://localhost:5002/api'`
3. Update API_BASE in `web/ai-config/script.js`: same change

## Migration Notes

### From FastAPI to Flask

The AI configuration API was originally implemented as a separate FastAPI server (`server/app.py`) but has been integrated into the Flask server for simplicity. The original FastAPI routes are preserved in `server/app.py` for reference but should not be used in production.

### Session Storage Migration

Current implementation uses in-memory dictionary. For production deployment:

1. Replace `sessions` dict with Redis or database
2. Serialize Question objects to JSON before storage
3. Add session timeout/cleanup logic
4. Implement session recovery on server restart

## Documentation Structure

- `START_HERE.md` - Quick start guide for end users
- `DEPLOYMENT_GUIDE.md` - Comprehensive deployment documentation
- `WEB_README.md` - Web API reference
- `SYSTEM_FLOW.md` - System flow diagrams
- `PROJECT_SUMMARY.txt` - Project completion summary
- `AI_CONFIG_FIX.md` - Details on AI config integration fix
- `README.md` - Project overview and CLI usage

Refer to these files for specific implementation details and troubleshooting.
