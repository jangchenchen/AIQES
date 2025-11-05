from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .question_models import Question, QuestionType


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_iso(timestamp: str) -> datetime:
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    return datetime.fromisoformat(timestamp)


def _question_to_dict(question: Question) -> Dict[str, Any]:
    return {
        "identifier": question.identifier,
        "question_type": question.question_type.name,
        "prompt": question.prompt,
        "options": question.options,
        "correct_options": question.correct_options,
        "answer_text": question.answer_text,
        "explanation": question.explanation,
        "keywords": question.keywords,
    }


def _dict_to_question(payload: Dict[str, Any]) -> Question:
    question_type = QuestionType[payload["question_type"]]
    return Question(
        identifier=payload["identifier"],
        question_type=question_type,
        prompt=payload["prompt"],
        options=payload.get("options"),
        correct_options=payload.get("correct_options"),
        answer_text=payload.get("answer_text"),
        explanation=payload.get("explanation"),
        keywords=list(payload.get("keywords", []) or []),
    )


class RecordManager:
    """Manage answer history and wrong-question persistence."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path("data")
        _ensure_dir(self.data_dir)
        self.history_path = self.data_dir / "answer_history.jsonl"
        self.wrong_path = self.data_dir / "wrong_questions.json"

    def new_session_id(self) -> str:
        return uuid.uuid4().hex

    def log_attempt(
        self,
        *,
        session_id: str,
        question: Question,
        user_answer: str,
        is_correct: bool,
        plain_explanation: str,
        session_context: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry: Dict[str, Any] = {
            "timestamp": _now_iso(),
            "session_id": session_id,
            "question": _question_to_dict(question),
            "user_answer": user_answer,
            "is_correct": is_correct,
            "plain_explanation": plain_explanation,
        }
        if session_context:
            entry["session_context"] = session_context
        if extra:
            entry["extra"] = extra
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Answer history management ------------------------------------------------

    def query_answer_history(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        session_id: str | None = None,
        question_type: QuestionType | None = None,
        is_correct: bool | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Dict[str, Any]:
        """分页查询作答历史记录"""
        entries = list(self._iter_answer_history())
        entries.sort(key=lambda item: item.get("timestamp", ""), reverse=True)

        filtered: List[Dict[str, Any]] = []
        for item in entries:
            if session_id and item.get("session_id") != session_id:
                continue
            if question_type:
                q_type = item.get("question", {}).get("question_type")
                if q_type != question_type.name:
                    continue
            if is_correct is not None and item.get("is_correct") != is_correct:
                continue
            if (date_from or date_to) and (timestamp := item.get("timestamp")):
                try:
                    dt = _parse_iso(timestamp)
                except ValueError:
                    continue
                if date_from and dt < date_from:
                    continue
                if date_to and dt > date_to:
                    continue
            filtered.append(item)

        total = len(filtered)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        page_entries = filtered[start:end] if start < total else []

        return {
            "entries": page_entries,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        }

    def list_answer_history_sessions(self, *, limit: int = 20) -> List[Dict[str, Any]]:
        """汇总最近的作答会话"""
        entries = list(self._iter_answer_history())
        if not entries:
            return []

        summaries: Dict[str, Dict[str, Any]] = {}
        for item in entries:
            session_id = item.get("session_id")
            if not session_id:
                continue
            summary = summaries.get(session_id)
            timestamp = item.get("timestamp")
            if summary is None:
                summary = {
                    "session_id": session_id,
                    "latest_at": timestamp,
                    "started_at": timestamp,
                    "total_answers": 0,
                    "correct_answers": 0,
                    "knowledge_file": item.get("session_context", {}).get("knowledge_file"),
                    "mode": item.get("session_context", {}).get("mode"),
                }
                summaries[session_id] = summary
            summary["total_answers"] += 1
            if item.get("is_correct"):
                summary["correct_answers"] += 1
            if timestamp:
                if not summary.get("latest_at") or summary["latest_at"] < timestamp:
                    summary["latest_at"] = timestamp
                if not summary.get("started_at") or summary["started_at"] > timestamp:
                    summary["started_at"] = timestamp

        ordered = sorted(
            summaries.values(),
            key=lambda entry: entry.get("latest_at", ""),
            reverse=True,
        )
        for entry in ordered:
            total_answers = entry.get("total_answers", 0) or 0
            correct = entry.get("correct_answers", 0)
            entry["accuracy"] = (correct / total_answers) if total_answers else 0.0
        return ordered[:limit]

    # Wrong question management -------------------------------------------------

    def load_wrong_questions(self) -> List[Question]:
        entries = self._load_wrong_payloads()
        questions: List[Question] = []
        for item in entries:
            try:
                questions.append(_dict_to_question(item["question"]))
            except KeyError:
                continue
        return questions

    def upsert_wrong_question(self, question: Question, *, last_plain_explanation: str) -> None:
        entries = self._load_wrong_payloads(as_dict=True)
        record = {
            "question": _question_to_dict(question),
            "last_plain_explanation": last_plain_explanation,
            "last_wrong_at": _now_iso(),
        }
        entries[question.identifier] = record
        self._write_wrong_payloads(entries.values())

    def remove_wrong_question(self, identifier: str) -> None:
        entries = self._load_wrong_payloads(as_dict=True)
        if identifier in entries:
            entries.pop(identifier)
            self._write_wrong_payloads(entries.values())

    def get_wrong_questions_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        question_type: Optional[QuestionType] = None,
        sort_by: str = "last_wrong_at",
        order: str = "desc",
    ) -> Dict[str, Any]:
        """获取分页的错题列表"""
        entries = self._load_wrong_payloads()

        # 筛选题型
        if question_type:
            entries = [
                e for e in entries
                if e.get("question", {}).get("question_type") == question_type.name
            ]

        # 排序
        reverse = (order == "desc")
        if sort_by == "last_wrong_at":
            entries.sort(key=lambda x: x.get("last_wrong_at", ""), reverse=reverse)
        elif sort_by == "identifier":
            entries.sort(
                key=lambda x: x.get("question", {}).get("identifier", ""),
                reverse=reverse
            )

        # 分页
        total = len(entries)
        start = (page - 1) * page_size
        end = start + page_size
        page_entries = entries[start:end]

        return {
            "questions": page_entries,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        }

    def get_wrong_question_stats(self) -> Dict[str, Any]:
        """获取错题统计信息"""
        entries = self._load_wrong_payloads()

        by_type = {}
        for entry in entries:
            q_type = entry.get("question", {}).get("question_type")
            by_type[q_type] = by_type.get(q_type, 0) + 1

        # 提取知识点（从 identifier 中提取）
        topics = {}
        for entry in entries:
            identifier = entry.get("question", {}).get("identifier", "")
            topic = identifier.split("-")[0] if "-" in identifier else "未分类"
            topics[topic] = topics.get(topic, 0) + 1

        weakest_topics = [
            {"topic": k, "count": v}
            for k, v in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        return {
            "total_wrong": len(entries),
            "by_type": by_type,
            "weakest_topics": weakest_topics,
        }

    def get_wrong_question_detail(self, identifier: str) -> Optional[Dict[str, Any]]:
        """获取单个错题详情"""
        entries = self._load_wrong_payloads(as_dict=True)
        return entries.get(identifier)

    def clear_all_wrong_questions(self) -> int:
        """清空错题本，返回删除数量"""
        entries = self._load_wrong_payloads()
        count = len(entries)
        if self.wrong_path.exists():
            self.wrong_path.unlink()
        return count

    # Internal helpers ---------------------------------------------------------

    def _load_wrong_payloads(self, *, as_dict: bool = False) -> Any:
        if not self.wrong_path.exists():
            return {} if as_dict else []
        try:
            payload = json.loads(self.wrong_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {} if as_dict else []
        if as_dict:
            if isinstance(payload, list):
                return {
                    item.get("question", {}).get("identifier", str(index)): item
                    for index, item in enumerate(payload)
                    if isinstance(item, dict)
                }
            if isinstance(payload, dict):
                return payload
            return {}
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return list(payload.values())
        return []

    def _iter_answer_history(self) -> Iterable[Dict[str, Any]]:
        if not self.history_path.exists():
            return []
        def generator() -> Iterable[Dict[str, Any]]:
            with self.history_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        return generator()

    def _write_wrong_payloads(self, entries: Iterable[Dict[str, Any]]) -> None:
        payload = list(entries)
        if payload:
            self.wrong_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        elif self.wrong_path.exists():
            self.wrong_path.unlink()


__all__ = ["RecordManager"]
