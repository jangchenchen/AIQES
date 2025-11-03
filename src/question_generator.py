from __future__ import annotations

import random
import re
from itertools import count
from typing import List, Sequence, Tuple

from .knowledge_loader import KnowledgeEntry
from .question_models import Question, QuestionType


_STOPWORDS = {
    "检查",
    "调整",
    "复位",
    "确认",
    "确保",
    "进行",
    "必须",
    "开关",
    "动作",
    "试验",
    "功能",
    "工作",
    "安全",
    "装置",
    "电梯",
    "设备",
    "确认",
    "确保",
}


class QuestionGenerator:
    def __init__(self, entries: Sequence[KnowledgeEntry], seed: int | None = None) -> None:
        self.entries = list(entries)
        self._rng = random.Random(seed)
        self._all_sentences: List[Tuple[str, str]] = []
        for entry in self.entries:
            for sentence in entry.sentences:
                normalized = sentence.strip()
                if len(normalized) < 8:
                    continue
                self._all_sentences.append((entry.component, normalized))

    def build_single_choice(self) -> List[Question]:
        questions: List[Question] = []
        unique_idx = count(1)

        other_sentences_by_component = {
            entry.component: [s for comp, s in self._all_sentences if comp != entry.component]
            for entry in self.entries
        }

        for entry in self.entries:
            candidates = [s for s in entry.sentences if len(s.strip()) >= 10]
            if not candidates:
                continue
            distractor_pool = other_sentences_by_component.get(entry.component, [])
            if len(distractor_pool) < 3:
                continue
            correct_sentence = self._rng.choice(candidates)
            distractors = self._rng.sample(distractor_pool, 3)
            options = distractors + [correct_sentence]
            self._rng.shuffle(options)
            correct_index = options.index(correct_sentence)
            questions.append(
                Question(
                    identifier=f"{entry.component}-SC-{next(unique_idx)}",
                    question_type=QuestionType.SINGLE_CHOICE,
                    prompt=f"关于{entry.component}，以下哪项描述是正确的？",
                    options=options,
                    correct_options=[correct_index],
                    answer_text=correct_sentence,
                    explanation=entry.raw_text,
                )
            )
        return questions

    def build_multi_choice(self) -> List[Question]:
        questions: List[Question] = []
        unique_idx = count(1)
        other_sentences = [sentence for _, sentence in self._all_sentences]

        for entry in self.entries:
            sentences = [s for s in entry.sentences if len(s.strip()) >= 10]
            if len(sentences) < 2:
                continue
            num_correct = min(3, len(sentences))
            correct_sentences = self._rng.sample(sentences, num_correct)
            distractor_candidates = [s for s in other_sentences if s not in correct_sentences]
            if len(distractor_candidates) < 2:
                continue
            num_distractors = max(2, 5 - num_correct)
            num_distractors = min(num_distractors, len(distractor_candidates))
            distractors = self._rng.sample(distractor_candidates, num_distractors)
            options = correct_sentences + distractors
            self._rng.shuffle(options)
            correct_indices = sorted([options.index(sentence) for sentence in correct_sentences])
            questions.append(
                Question(
                    identifier=f"{entry.component}-MC-{next(unique_idx)}",
                    question_type=QuestionType.MULTI_CHOICE,
                    prompt=f"关于{entry.component}，以下哪些描述是正确的？（多选）",
                    options=options,
                    correct_options=correct_indices,
                    answer_text="；".join(correct_sentences),
                    explanation=entry.raw_text,
                )
            )
        return questions

    def build_cloze(self) -> List[Question]:
        questions: List[Question] = []
        unique_idx = count(1)
        for entry in self.entries:
            for sentence in entry.sentences:
                cloze_sentence, answer = _make_cloze(sentence, entry.component)
                if cloze_sentence is None or answer is None:
                    continue
                questions.append(
                    Question(
                        identifier=f"{entry.component}-CZ-{next(unique_idx)}",
                        question_type=QuestionType.CLOZE,
                        prompt=f"填空题：{cloze_sentence}",
                        answer_text=answer,
                        explanation=sentence,
                    )
                )
                break
        return questions

    def build_open_ended(self) -> List[Question]:
        questions: List[Question] = []
        unique_idx = count(1)
        for entry in self.entries:
            reference = "；".join(entry.sentences[:3])
            keywords = _extract_keywords(entry)
            questions.append(
                Question(
                    identifier=f"{entry.component}-QA-{next(unique_idx)}",
                    question_type=QuestionType.QA,
                    prompt=f"问答题：请概述{entry.component}的关键检查或操作要求。",
                    answer_text=reference,
                    explanation=entry.raw_text,
                    keywords=keywords,
                )
            )
        return questions

    def build_question_bank(self) -> List[Question]:
        questions: List[Question] = []
        questions.extend(self.build_single_choice())
        questions.extend(self.build_multi_choice())
        questions.extend(self.build_cloze())
        questions.extend(self.build_open_ended())
        return questions


def _make_cloze(sentence: str, component: str) -> tuple[str | None, str | None]:
    sentence = sentence.strip()
    numeric_pattern = re.compile(r"(\d+(?:\.\d+)?%?|\d+m/s|\d+年|\d+次)")
    match = numeric_pattern.search(sentence)
    if match:
        answer = match.group(0)
        return sentence[:match.start()] + "____" + sentence[match.end():], answer

    if component in sentence:
        return sentence.replace(component, "____", 1), component

    word_candidates = re.findall(r"[\u4e00-\u9fa5]{2,4}", sentence)
    for word in word_candidates:
        if word in _STOPWORDS:
            continue
        return sentence.replace(word, "____", 1), word
    return None, None


def _extract_keywords(entry: KnowledgeEntry) -> List[str]:
    keywords: List[str] = []
    numeric_tokens = set(re.findall(r"\d+(?:\.\d+)?%?|\d+m/s|\d+年|\d+次", entry.raw_text))
    keywords.extend(list(numeric_tokens))
    word_candidates = re.findall(r"[\u4e00-\u9fa5]{2,4}", entry.raw_text)
    for word in word_candidates:
        if word in _STOPWORDS:
            continue
        if word == entry.component:
            continue
        if word in keywords:
            continue
        keywords.append(word)
        if len(keywords) >= 8:
            break
    if entry.component not in keywords:
        keywords.insert(0, entry.component)
    return keywords


__all__ = ["QuestionGenerator"]
