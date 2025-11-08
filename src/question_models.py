from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


class QuestionType(Enum):
    SINGLE_CHOICE = auto()
    MULTI_CHOICE = auto()
    CLOZE = auto()
    QA = auto()


@dataclass
class Question:
    identifier: str
    question_type: QuestionType
    prompt: str
    options: Optional[List[str]] = None
    correct_options: Optional[List[int]] = None
    answer_text: Optional[str] = None
    explanation: Optional[str] = None
    keywords: List[str] = field(default_factory=list)

    def is_multiple_choice(self) -> bool:
        return self.question_type in {
            QuestionType.SINGLE_CHOICE,
            QuestionType.MULTI_CHOICE,
        }


__all__ = ["Question", "QuestionType"]
