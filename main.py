from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from src.ai_client import (
    AIClient,
    AIResponseFormatError,
    AITransportError,
    load_ai_config,
)
from src.knowledge_loader import MAX_KNOWLEDGE_FILE_SIZE, load_knowledge_entries
from src.question_generator import QuestionGenerator
from src.question_models import Question, QuestionType
from src.record_manager import RecordManager


DEFAULT_KNOWLEDGE_PATH = Path("docs/Knowledge/电梯安全装置维护程序.md")
AI_CONFIG_PATH = Path("AI_cf/cf.json")


_TYPE_ALIAS: Dict[str, QuestionType] = {
    "single": QuestionType.SINGLE_CHOICE,
    "multi": QuestionType.MULTI_CHOICE,
    "cloze": QuestionType.CLOZE,
    "qa": QuestionType.QA,
}


@dataclass
class GradeOutcome:
    is_correct: bool
    plain_explanation: str
    extra: Optional[Dict[str, Any]] = None


class QuizSession:
    def __init__(
        self,
        questions: Sequence[Question],
        mode: str = "sequential",
        count: int | None = None,
        seed: int | None = None,
        record_manager: RecordManager | None = None,
        session_id: str | None = None,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        questions = list(questions)
        if mode == "random":
            rng = random.Random(seed)
            rng.shuffle(questions)
        elif mode != "sequential":  # pragma: no cover - defensive branch
            raise ValueError(f"未知的出题模式: {mode}")
        if count is not None:
            questions = questions[:count]
        self.questions = questions
        self.correct_auto = 0
        self.total_auto = 0
        self.record_manager = record_manager
        self.session_id = session_id
        self.session_context = session_context or {}

    def run(self) -> None:
        total = len(self.questions)
        print(f"本次题目数量：{total}\n")
        for idx, question in enumerate(self.questions, start=1):
            print(f"—— 第{idx}题/{total} ——")
            self._ask(question)
            print()
        if self.total_auto:
            score = 100 * self.correct_auto / self.total_auto
            print(f"自动判分题得分：{score:.1f}（{self.correct_auto}/{self.total_auto}）")
        else:  # pragma: no cover - safeguard
            print("无自动判分题目。")

    def _ask(self, question: Question) -> None:
        print(question.prompt)
        if question.options:
            for idx, option in enumerate(question.options):
                label = chr(ord("A") + idx)
                print(f"  {label}. {option.strip()}")

        user_answer = input("你的答案：").strip()
        if question.question_type == QuestionType.SINGLE_CHOICE:
            outcome = self._grade_single_choice(question, user_answer)
        elif question.question_type == QuestionType.MULTI_CHOICE:
            outcome = self._grade_multi_choice(question, user_answer)
        elif question.question_type == QuestionType.CLOZE:
            outcome = self._grade_cloze(question, user_answer)
        elif question.question_type == QuestionType.QA:
            outcome = self._grade_open(question, user_answer)
        else:  # pragma: no cover - safety
            print("暂不支持的题型。")
            outcome = GradeOutcome(is_correct=False, plain_explanation="该题型尚未实现自动判分。")

        if self.record_manager and self.session_id:
            self.record_manager.log_attempt(
                session_id=self.session_id,
                question=question,
                user_answer=user_answer,
                is_correct=outcome.is_correct,
                plain_explanation=outcome.plain_explanation,
                session_context=self.session_context,
                extra=outcome.extra,
            )
            if outcome.is_correct:
                self.record_manager.remove_wrong_question(question.identifier)
            else:
                self.record_manager.upsert_wrong_question(
                    question,
                    last_plain_explanation=outcome.plain_explanation,
                )

    def _grade_single_choice(self, question: Question, user_answer: str) -> GradeOutcome:
        self.total_auto += 1
        correct_indices = question.correct_options or []
        correct_idx = correct_indices[0] if correct_indices else None
        correct_label = _option_label(correct_idx)
        is_correct = False

        if not user_answer:
            print("未作答。正确答案：", correct_label)
        else:
            idx = _letter_to_index(user_answer)
            if idx is None or idx >= len(question.options or []):
                print("答案格式不正确。正确答案：", correct_label)
            elif idx in correct_indices:
                self.correct_auto += 1
                is_correct = True
                print("✅ 回答正确！")
            else:
                print("❌ 回答不正确。正确答案：", correct_label)

        key_sentence = (question.answer_text or "").strip() or (question.explanation or "").strip()
        summary_text = question.answer_text or key_sentence
        print("要点：", summary_text)
        plain_explanation = _plain_explanation_single(
            question,
            correct_label=correct_label,
            key_sentence=key_sentence,
            is_correct=is_correct,
            user_answer=user_answer,
        )
        print("解析：", plain_explanation)
        return GradeOutcome(is_correct=is_correct, plain_explanation=plain_explanation)

    def _grade_multi_choice(self, question: Question, user_answer: str) -> GradeOutcome:
        self.total_auto += 1
        correct_indices = question.correct_options or []
        correct_set = set(correct_indices)
        correct_labels = _format_indices(correct_indices)
        parsed_indices: Optional[List[int]] = None
        is_correct = False

        if not user_answer:
            print("未作答。正确答案：", correct_labels)
        else:
            parsed_indices = _parse_multi_answer(user_answer, len(question.options or []))
            if parsed_indices is None:
                print("答案格式不正确。正确答案：", correct_labels)
            else:
                if set(parsed_indices) == correct_set:
                    self.correct_auto += 1
                    is_correct = True
                    print("✅ 回答正确！")
                else:
                    self._print_multi_feedback(parsed_indices, correct_set, question)

        correct_texts: List[str] = []
        if question.options:
            option_count = len(question.options)
            for idx in correct_indices:
                if 0 <= idx < option_count:
                    correct_texts.append(question.options[idx].strip())
        summary_text = question.answer_text or "；".join(correct_texts)
        print("要点：", summary_text)
        plain_explanation = _plain_explanation_multi(
            question,
            correct_labels=correct_labels,
            summary_text=summary_text,
            is_correct=is_correct,
        )
        print("解析：", plain_explanation)
        extra = {"selected_indices": parsed_indices} if parsed_indices is not None else None
        return GradeOutcome(is_correct=is_correct, plain_explanation=plain_explanation, extra=extra)

    def _print_multi_feedback(self, indices: Iterable[int], correct_set: set[int], question: Question) -> None:
        wrong = set(indices) - correct_set
        missing = correct_set - set(indices)
        print("❌ 回答不完全正确。")
        if wrong:
            detail = "；".join(question.options[i] for i in sorted(wrong))
            print("误选：", detail)
        if missing:
            detail = "；".join(question.options[i] for i in sorted(missing))
            print("漏选：", detail)
        print("正确选项：", _format_indices(question.correct_options))
        print("要点：", question.answer_text)

    def _grade_cloze(self, question: Question, user_answer: str) -> GradeOutcome:
        self.total_auto += 1
        normalized_user = _normalize_answer(user_answer)
        normalized_ref = _normalize_answer(question.answer_text or "")
        is_correct = False
        if normalized_user == normalized_ref and normalized_ref:
            self.correct_auto += 1
            is_correct = True
            print("✅ 回答正确！")
        else:
            print("❌ 回答不正确。")
            print("正确答案：", question.answer_text)
        print("参考原句：", question.explanation)
        plain_explanation = _plain_explanation_cloze(
            question,
            is_correct=is_correct,
        )
        print("解析：", plain_explanation)
        return GradeOutcome(is_correct=is_correct, plain_explanation=plain_explanation)

    def _grade_open(self, question: Question, user_answer: str) -> GradeOutcome:
        keywords = list(question.keywords or [])
        matched: List[str] = []
        ratio = 0.0
        is_correct = False
        if not user_answer:
            if keywords:
                print("未作答。建议包含以下关键词：", "、".join(keywords[:6]))
            else:
                print("未作答。请结合参考答案复习要点。")
        else:
            matched = [kw for kw in keywords if kw and kw in user_answer]
            ratio = len(matched) / max(1, len(keywords))
            if matched:
                print(f"匹配到关键词（{len(matched)}）：", "、".join(matched))
            else:
                print("未匹配到关键词，请对照参考答案自查。")
            print(f"关键词覆盖率约为：{ratio:.0%}")
            if keywords:
                is_correct = ratio >= 0.6
            else:
                is_correct = bool(user_answer.strip())
        print("参考答案：", question.answer_text)
        plain_explanation = _plain_explanation_qa(
            question,
            matched_keywords=matched,
            coverage_ratio=ratio,
            is_correct=is_correct,
        )
        print("解析：", plain_explanation)
        extra = {
            "matched_keywords": matched,
            "coverage_ratio": ratio,
        }
        return GradeOutcome(is_correct=is_correct, plain_explanation=plain_explanation, extra=extra)


def _option_label(idx: int | None) -> str:
    if idx is None:
        return "—"
    return chr(ord("A") + idx)


def _format_indices(indices: Sequence[int] | None) -> str:
    if not indices:
        return "—"
    return ", ".join(_option_label(i) for i in indices)


def _letter_to_index(user_answer: str) -> int | None:
    answer = user_answer.strip().upper()
    if not answer:
        return None
    letter = answer[0]
    if not ("A" <= letter <= "Z"):
        return None
    return ord(letter) - ord("A")


def _parse_multi_answer(user_answer: str, option_count: int) -> List[int] | None:
    cleaned = user_answer.replace(" ", "").replace("，", ",").upper()
    if not cleaned:
        return []
    tokens: List[str] = []
    for token in cleaned.split(","):
        if not token:
            continue
        tokens.append(token)
    if len(tokens) == 1 and len(tokens[0]) > 1:
        tokens = list(tokens[0])
    indices: List[int] = []
    for token in tokens:
        if not token:
            continue
        letter = token[0]
        if not ("A" <= letter <= "Z"):
            return None
        idx = ord(letter) - ord("A")
        if idx >= option_count:
            return None
        indices.append(idx)
    return sorted(set(indices))


def _normalize_answer(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace(" ", "").replace("，", ",").strip()


def _plain_explanation_single(
    question: Question,
    *,
    correct_label: str,
    key_sentence: str,
    is_correct: bool,
    user_answer: str,
) -> str:
    key_sentence = key_sentence or (question.explanation or "请按知识点要求执行。")
    if is_correct:
        return f"这题你选得很准，记住{correct_label}选项讲的是：{key_sentence}。"
    user_reply = user_answer or "未作答"
    return (
        f"正确答案是{correct_label}选项，你刚才填的是“{user_reply}”。简单来说，这条要求强调："
        f"{key_sentence}，以后留意不要选错。"
    )


def _plain_explanation_multi(
    question: Question,
    *,
    correct_labels: str,
    summary_text: str,
    is_correct: bool,
) -> str:
    summary_text = summary_text or (question.explanation or "按原文把所有条件都做到。")
    if is_correct:
        return f"多选题全部命中，{correct_labels} 选项共同强调：{summary_text}。记得逐条检查。"
    return (
        f"正确选项是 {correct_labels}，这些内容的意思是：{summary_text}。把所有要点一次记牢，"
        "别再漏选或多选。"
    )


def _plain_explanation_cloze(question: Question, *, is_correct: bool) -> str:
    answer_text = (question.answer_text or "").strip()
    reference = (question.explanation or "").strip()
    if is_correct:
        return f"空格填写“{answer_text}”就对了，原文提示就是：{reference}。"
    return (
        f"空格应填写“{answer_text}”，原文意思是：{reference}。记住这个关键词，下次不要再漏。"
    )


def _plain_explanation_qa(
    question: Question,
    *,
    matched_keywords: Iterable[str],
    coverage_ratio: float,
    is_correct: bool,
) -> str:
    matched_list = [kw for kw in matched_keywords]
    keyword_hint = "、".join(question.keywords[:6]) if question.keywords else ""
    reference = (question.answer_text or "").strip() or (question.explanation or "").strip()
    ratio_percent = int(round(coverage_ratio * 100))
    if is_correct:
        return (
            f"答案覆盖了主要关键词（{ '、'.join(matched_list) if matched_list else '关键点' }），"
            f"大约 {ratio_percent}% 的要求已提及。核心记忆点：{reference}。"
        )
    miss_part = (
        f"建议把关键字补齐：{keyword_hint}。" if keyword_hint else "请结合原文补充要点。"
    )
    return (
        f"目前覆盖率只有 {ratio_percent}% ，需要再补充。参考答案浓缩要点：{reference}。"
        f"{miss_part}"
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="基于知识点的问答训练系统")
    parser.add_argument("--mode", choices=["sequential", "random"], default="sequential", help="出题顺序：顺序或随机")
    parser.add_argument("--count", type=int, default=None, help="题目数量限制")
    parser.add_argument("--types", nargs="*", choices=list(_TYPE_ALIAS.keys()), help="筛选题型")
    parser.add_argument("--seed", type=int, default=None, help="随机数种子")
    parser.add_argument("--enable-ai", action="store_true", help="加载AI配置，预留AI题库扩展能力")
    parser.add_argument("--ai-questions", type=int, default=0, help="额外生成的 AI 题目数量")
    parser.add_argument("--ai-temperature", type=float, default=0.7, help="AI 生成题目的 temperature 参数")
    parser.add_argument(
        "--knowledge-file",
        type=str,
        help=(
            f"知识文件路径，支持 .md/.txt/.pdf 形式（<= {MAX_KNOWLEDGE_FILE_SIZE // 1024}KB）。"
        ),
    )
    parser.add_argument("--review-wrong", action="store_true", help="仅练习历史错题")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.count is not None and args.count <= 0:
        print("题目数量必须为正数。")
        return 1
    if args.ai_questions < 0:
        print("AI 题目数量不能为负数。")
        return 1

    record_manager = RecordManager()
    session_id = record_manager.new_session_id()

    knowledge_path = (
        Path(args.knowledge_file).expanduser()
        if args.knowledge_file
        else DEFAULT_KNOWLEDGE_PATH
    )
    try:
        entries = load_knowledge_entries(knowledge_path)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        print(f"加载知识文件失败：{exc}")
        return 1
    generator = QuestionGenerator(entries, seed=args.seed)
    question_bank = generator.build_question_bank()

    type_filters: Set[QuestionType]
    if args.types:
        type_filters = { _TYPE_ALIAS[t] for t in args.types }
        question_bank = [q for q in question_bank if q.question_type in type_filters]
        if not question_bank and args.ai_questions == 0 and not args.review_wrong:
            print("筛选后的题库为空，请调整题型筛选条件。")
            return 1
    else:
        type_filters = set(_TYPE_ALIAS.values())

    ai_client: AIClient | None = None
    ai_questions: List[Question] = []

    if args.review_wrong:
        wrong_questions = record_manager.load_wrong_questions()
        wrong_questions = [q for q in wrong_questions if q.question_type in type_filters]
        if not wrong_questions:
            print("暂无错题可复习，先完成一次练习再来试试吧。")
            return 0
        print(f"进入错题练习模式，共载入 {len(wrong_questions)} 道题。")
        question_bank = wrong_questions
        if args.enable_ai and args.ai_questions:
            print("提示：错题练习模式下忽略 AI 出题参数。")
    else:
        if args.enable_ai and AI_CONFIG_PATH.exists():
            config = load_ai_config(AI_CONFIG_PATH)
            ai_client = AIClient(config)
            print("已加载AI配置：", ai_client.describe())
            if args.ai_questions:
                print(
                    "尝试生成 {count} 道 AI 题目（type: {types}）。".format(
                        count=args.ai_questions,
                        types=", ".join(t.name for t in sorted(type_filters, key=lambda t: t.value)),
                    )
                )
        elif args.enable_ai:
            print("未找到AI配置文件，跳过AI加载。\n")

        if ai_client and args.ai_questions:
            try:
                ai_questions = ai_client.generate_additional_questions(
                    entries,
                    count=args.ai_questions,
                    question_types=type_filters,
                    temperature=args.ai_temperature,
                )
            except (AITransportError, AIResponseFormatError) as exc:
                print(f"⚠️ AI 出题失败：{exc}")
            else:
                if ai_questions:
                    print(f"AI 生成题目 {len(ai_questions)} 道，将并入题库。\n")
                else:
                    print("⚠️ AI 未返回有效题目。\n")

    all_questions = question_bank + ai_questions
    if not all_questions:
        print("题库为空，无法开始测验。")
        return 1

    session_context = {
        "mode": args.mode,
        "requested_count": args.count,
        "type_filters": [t.name for t in sorted(type_filters, key=lambda t: t.value)],
        "review_wrong": args.review_wrong,
        "ai_requested": args.ai_questions if not args.review_wrong else 0,
        "knowledge_file": str(knowledge_path),
    }
    if args.enable_ai:
        session_context["ai_temperature"] = args.ai_temperature

    session = QuizSession(
        all_questions,
        mode=args.mode,
        count=args.count,
        seed=args.seed,
        record_manager=record_manager,
        session_id=session_id,
        session_context=session_context,
    )
    session.run()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n已中断测验。")
        raise
