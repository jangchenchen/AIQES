from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import List

MAX_KNOWLEDGE_FILE_SIZE = 700_000  # bytes, ~700KB to keep AI 请求高效


@dataclass
class KnowledgeEntry:
    component: str
    raw_text: str
    sentences: List[str] = field(default_factory=list)


def load_knowledge_entries(path: pathlib.Path) -> List[KnowledgeEntry]:
    """Load knowledge entries from markdown/txt/pdf.

    The parser prioritises structured markdown tables, otherwise it falls back
    to plain-text segmentation. PDF 支持依赖 PyPDF2，可选安装。
    """

    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"知识文件不存在：{path}")
    if path.stat().st_size > MAX_KNOWLEDGE_FILE_SIZE:
        raise ValueError(
            f"知识文件过大（>{MAX_KNOWLEDGE_FILE_SIZE // 1024}KB），请精简内容后再上传。"
        )

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_text_from_pdf(path)
        return _entries_from_plain_text(text)

    encoding = "utf-8"
    try:
        text = path.read_text(encoding=encoding)
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".md":
        entries = _parse_markdown_table(text)
        if entries:
            return entries
    return _entries_from_plain_text(text)


# ---------------------------------------------------------------------------
# Markdown parsing utilities


def _parse_markdown_table(text: str) -> List[KnowledgeEntry]:
    lines = text.splitlines()
    table_lines: List[str] = []
    for line in lines:
        if not line.startswith("|"):
            continue
        if line.strip().startswith("| :"):
            continue
        table_lines.append(line)
    entries: List[KnowledgeEntry] = []
    for raw_line in table_lines:
        parts = [part.strip() for part in raw_line.strip().strip("|").split("|")]
        if len(parts) < 2:
            continue
        component = _clean_markdown(parts[0])
        if component in {"部件", "知识点", "章节"}:
            continue
        description = _clean_markdown(" ".join(parts[1:]))
        if not description:
            continue
        sentences = _split_sentences(description)
        entries.append(
            KnowledgeEntry(
                component=component or "知识点",
                raw_text=description,
                sentences=sentences,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Plain-text fallback


def _entries_from_plain_text(text: str) -> List[KnowledgeEntry]:
    blocks = [block.strip() for block in re.split(r"\n{2,}", text) if block.strip()]
    entries: List[KnowledgeEntry] = []
    for index, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        component = lines[0]
        content_lines = lines[1:] if len(lines) > 1 else lines
        raw_text = " ".join(content_lines)
        if not raw_text:
            raw_text = component
            component = f"知识点{index}"
        sentences = _split_sentences(raw_text)
        entries.append(
            KnowledgeEntry(
                component=component,
                raw_text=raw_text,
                sentences=sentences,
            )
        )
    if entries:
        return entries
    # 兜底：整个文件作为一个知识点
    cleaned = text.strip()
    sentences = _split_sentences(cleaned)
    return [
        KnowledgeEntry(
            component="知识点1",
            raw_text=cleaned,
            sentences=sentences,
        )
    ]


# ---------------------------------------------------------------------------
# Helpers


def _clean_markdown(text: str) -> str:
    cleaned = text.replace("**", "")
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    cleaned = re.sub(r"`+", "", cleaned)
    cleaned = re.sub(r"\\n", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _split_sentences(text: str) -> List[str]:
    pattern = re.compile(r"[^。！？；;\n]+[。！？；;]?")
    sentences: List[str] = []
    for match in pattern.findall(text):
        sentence = match.strip()
        if sentence:
            sentences.append(sentence)
    return sentences or [text.strip()] if text.strip() else []


def _extract_text_from_pdf(path: pathlib.Path) -> str:
    try:
        import PyPDF2  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ImportError("读取 PDF 需要安装 PyPDF2：pip install PyPDF2") from exc

    text_chunks: List[str] = []
    with path.open("rb") as handle:
        reader = PyPDF2.PdfReader(handle)
        for page in reader.pages:
            try:
                text_chunks.append(page.extract_text() or "")
            except Exception:  # pragma: no cover - PyPDF2 内部异常
                continue
    return "\n\n".join(chunk.strip() for chunk in text_chunks if chunk.strip())


__all__ = ["KnowledgeEntry", "load_knowledge_entries", "MAX_KNOWLEDGE_FILE_SIZE"]
