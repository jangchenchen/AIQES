from __future__ import annotations

import json
import pathlib
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .question_models import Question, QuestionType


_QTYPE_ALIAS = {
    "single": QuestionType.SINGLE_CHOICE,
    "single_choice": QuestionType.SINGLE_CHOICE,
    "single-choice": QuestionType.SINGLE_CHOICE,
    "sc": QuestionType.SINGLE_CHOICE,
    "multi": QuestionType.MULTI_CHOICE,
    "multi_choice": QuestionType.MULTI_CHOICE,
    "multi-choice": QuestionType.MULTI_CHOICE,
    "mc": QuestionType.MULTI_CHOICE,
    "cloze": QuestionType.CLOZE,
    "fill": QuestionType.CLOZE,
    "fill_blank": QuestionType.CLOZE,
    "qa": QuestionType.QA,
    "open": QuestionType.QA,
    "open_ended": QuestionType.QA,
}


@dataclass
class AIConfig:
    key: str
    url: str
    model: str
    dev_document: Optional[str] = None
    timeout: float = 45.0


class AITransportError(RuntimeError):
    """Raised when the HTTP transport fails."""


class AIResponseFormatError(RuntimeError):
    """Raised when the AI response cannot be parsed into questions."""


class AIClient:
    """Client for requesting additional questions from an external AI model."""

    def __init__(self, config: AIConfig) -> None:
        self.config = config

    def describe(self) -> str:
        summary = f"model={self.config.model} url={self.config.url}"
        if self.config.dev_document:
            summary += f" (docs: {self.config.dev_document})"
        return summary

    def generate_additional_questions(
        self,
        entries: Sequence["KnowledgeEntry"],
        *,
        count: int,
        question_types: Iterable[QuestionType],
        temperature: float = 0.7,
    ) -> List[Question]:
        if count <= 0:
            return []
        type_labels = sorted({self._question_type_to_label(qt) for qt in question_types})
        if not type_labels:
            type_labels = ["single", "multi", "cloze", "qa"]

        knowledge_summary = self._build_knowledge_summary(entries)
        prompt = self._build_prompt(knowledge_summary, count, type_labels)

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一名安全培训出题专家。只使用提供的知识点内容，生成题目。"
                        "结果必须是 JSON 字符串。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }

        response = self._post_json(self._sanitize_url(self.config.url), payload)
        message = self._extract_message_text(response)
        raw_questions = self._parse_questions(message)
        built_questions: List[Question] = []
        for idx, raw in enumerate(raw_questions, start=1):
            question = self._build_question(raw, fallback_index=idx)
            if question is None:
                continue
            if question.question_type not in question_types:
                continue
            built_questions.append(question)
            if len(built_questions) >= count:
                break
        return built_questions

    def _question_type_to_label(self, question_type: QuestionType) -> str:
        if question_type == QuestionType.SINGLE_CHOICE:
            return "single"
        if question_type == QuestionType.MULTI_CHOICE:
            return "multi"
        if question_type == QuestionType.CLOZE:
            return "cloze"
        return "qa"

    def _build_knowledge_summary(self, entries: Sequence["KnowledgeEntry"]) -> str:
        chunks = []
        for entry in entries:
            chunks.append(f"- {entry.component}：{entry.raw_text}")
        return "\n".join(chunks)

    def _build_prompt(self, summary: str, count: int, type_labels: Sequence[str]) -> str:
        types_str = ", ".join(type_labels)
        template = (
            "以下是电梯安全维护的知识点：\n"
            f"{summary}\n\n"
            "请基于这些知识点生成 {count} 道题。题型限定为：{types}。\n"
            "输出 JSON 数组，每个元素包含字段：\n"
            "- id: 字符串，题目唯一标识（如果无可填临时 ID）\n"
            "- component: 题目涉及的部件名称\n"
            "- type: 题型（single/multi/cloze/qa）\n"
            "- prompt: 题干\n"
            "- options: 单选/多选题的选项数组，其他题型可省略\n"
            "- answer: 单选题用整数索引，多选题用整数索引数组，填空/问答题用字符串\n"
            "- explanation: 参考答案解析或出处\n"
            "- keywords: 可选，问答题可提供关键词数组\n"
            "务必严格输出合法 JSON，不要包含额外说明。"
        )
        return template.format(count=count, types=types_str)

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.key}",
        }
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - network path
            detail = exc.read().decode("utf-8", errors="ignore")
            raise AITransportError(f"AI 接口 HTTP {exc.code}: {detail}") from exc
        except OSError as exc:  # pragma: no cover - network path
            raise AITransportError(f"无法连接 AI 接口: {exc}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AIResponseFormatError("AI 接口返回的不是合法 JSON") from exc

    def _extract_message_text(self, response: Dict[str, Any]) -> str:
        choices = response.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                message = choice.get("message") if isinstance(choice, dict) else None
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                    if isinstance(content, list):
                        parts = [part.get("text", "") for part in content if isinstance(part, dict)]
                        merged = "".join(parts).strip()
                        if merged:
                            return merged
                content = choice.get("text") if isinstance(choice, dict) else None
                if isinstance(content, str) and content.strip():
                    return content
        for key in ("result", "content", "data"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raise AIResponseFormatError("无法在 AI 响应中找到文本内容")

    def _parse_questions(self, message: str) -> List[Dict[str, Any]]:
        message = message.strip()
        try:
            data = json.loads(message)
        except json.JSONDecodeError as exc:
            json_candidate = self._extract_json_block(message)
            if json_candidate is None:
                raise AIResponseFormatError("AI 返回内容中不包含 JSON 数据") from exc
            data = json.loads(json_candidate)
        if isinstance(data, dict) and "questions" in data:
            data = data["questions"]
        if not isinstance(data, list):
            raise AIResponseFormatError("AI 返回的 JSON 不是题目数组")
        normalized: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                normalized.append(item)
        if not normalized:
            raise AIResponseFormatError("AI 返回的题目数组为空")
        return normalized

    def _extract_json_block(self, text: str) -> Optional[str]:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        return None

    def _build_question(self, raw: Dict[str, Any], fallback_index: int) -> Optional[Question]:
        raw_type = str(raw.get("type", "")).strip().lower()
        question_type = _QTYPE_ALIAS.get(raw_type)
        if question_type is None:
            return None
        prompt = str(raw.get("prompt", "")).strip()
        if not prompt:
            return None
        component = str(raw.get("component", "")).strip() or "AI"
        identifier = str(raw.get("id") or f"AI-{component}-{fallback_index}")
        explanation = str(raw.get("explanation", "")).strip() or None

        if question_type in {QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE}:
            options = self._normalize_options(raw.get("options"))
            if not options:
                return None
            correct = self._normalize_option_answers(raw.get("answer"), question_type, options)
            if correct is None:
                return None
            answer_text = "；".join(options[idx] for idx in correct)
            return Question(
                identifier=identifier,
                question_type=question_type,
                prompt=prompt,
                options=options,
                correct_options=correct,
                answer_text=answer_text,
                explanation=explanation,
            )

        answer_text = self._normalize_text_answer(raw.get("answer"))
        if question_type == QuestionType.CLOZE and not answer_text:
            return None
        keywords_raw = raw.get("keywords")
        keywords = self._normalize_keywords(keywords_raw, fallback=answer_text)
        return Question(
            identifier=identifier,
            question_type=question_type,
            prompt=prompt,
            answer_text=answer_text,
            explanation=explanation,
            keywords=keywords,
        )

    def _normalize_options(self, options: Any) -> Optional[List[str]]:
        if not isinstance(options, (list, tuple)):
            return None
        normalized: List[str] = []
        for item in options:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized if normalized else None

    def _normalize_option_answers(
        self,
        answer: Any,
        question_type: QuestionType,
        options: Sequence[str],
    ) -> Optional[List[int]]:
        if question_type == QuestionType.SINGLE_CHOICE:
            candidates = self._coerce_answer_list(answer)
            if not candidates:
                return None
            idx = candidates[0]
            return [idx] if 0 <= idx < len(options) else None

        indices = sorted(set(self._coerce_answer_list(answer)))
        valid = [idx for idx in indices if 0 <= idx < len(options)]
        return valid if valid else None

    def _coerce_answer_list(self, answer: Any) -> List[int]:
        if isinstance(answer, int):
            return [answer]
        if isinstance(answer, str) and answer.strip():
            if answer.isdigit():
                return [int(answer)]
            # 尝试按字母匹配
            answer = answer.strip().upper()
            letters = [ch for ch in answer if "A" <= ch <= "Z"]
            if letters:
                return [ord(ch) - ord("A") for ch in letters]
        if isinstance(answer, (list, tuple)):
            result: List[int] = []
            for item in answer:
                result.extend(self._coerce_answer_list(item))
            return result
        return []

    def _normalize_text_answer(self, answer: Any) -> Optional[str]:
        if answer is None:
            return None
        if isinstance(answer, (list, tuple)):
            answer = "；".join(str(part) for part in answer if str(part).strip())
        text = str(answer).strip()
        return text or None

    def _normalize_keywords(self, keywords: Any, fallback: Optional[str]) -> List[str]:
        if isinstance(keywords, (list, tuple)):
            normalized = [str(item).strip() for item in keywords if str(item).strip()]
            if normalized:
                return normalized[:8]
        if isinstance(keywords, str) and keywords.strip():
            return [segment.strip() for segment in keywords.split("，") if segment.strip()][:8]
        if fallback:
            extracted = list({token for token in self._extract_tokens(fallback)})
            return extracted[:8]
        return []

    def _extract_tokens(self, text: str) -> Iterable[str]:
        numbers = re.findall(r"\d+(?:\.\d+)?%?|\d+m/s|\d+年|\d+次", text)
        words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)
        for token in numbers + words:
            yield token

    def _sanitize_url(self, url: str) -> str:
        return url.split("#", 1)[0]


def load_ai_config(path: pathlib.Path) -> AIConfig:
    payload: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    try:
        key = payload["key"]
        url = payload["url"]
        model = payload["model"]
    except KeyError as exc:  # pragma: no cover - defensive branch
        raise ValueError(f"配置文件缺少必要字段: {exc}") from exc
    return AIConfig(
        key=key,
        url=url,
        model=model,
        dev_document=payload.get("dev_document"),
        timeout=float(payload.get("timeout", 45.0)),
    )


__all__ = [
    "AIClient",
    "AIConfig",
    "AIResponseFormatError",
    "AITransportError",
    "load_ai_config",
]
