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

    def _write_wrong_payloads(self, entries: Iterable[Dict[str, Any]]) -> None:
        payload = list(entries)
        if payload:
            self.wrong_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        elif self.wrong_path.exists():
            self.wrong_path.unlink()


__all__ = ["RecordManager"]
