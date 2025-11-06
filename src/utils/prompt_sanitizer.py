"""AI 提示注入过滤工具"""
from __future__ import annotations

import re
from typing import List


# 危险关键词列表（提示注入攻击常用词）
DANGEROUS_PATTERNS = [
    # 系统指令覆盖
    r"ignore\s+(previous|all|above|your)\s+(instructions?|prompts?|rules?)",
    r"forget\s+(everything|all|previous)",
    r"disregard\s+(previous|above)",
    r"override\s+instructions?",

    # 角色伪装
    r"you\s+are\s+(now|a)\s+(admin|developer|system|god|root)",
    r"you\s+are\s+now\s+an?\s+\w+\s+with\s+(full|admin|root)",  # "you are now an admin with full"
    r"now\s+you\s+are\s+",
    r"new\s+instructions?",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"act\s+as\s+(admin|root|system)",

    # 越狱尝试
    r"jailbreak",
    r"do\s+anything\s+now",
    r"DAN\s+mode",
    r"developer\s+mode",
    r"escape\s+(sandbox|restrictions?)",

    # 恶意命令
    r"execute\s+code",
    r"run\s+command",
    r"eval\s*\(",
    r"exec\s*\(",

    # 敏感操作
    r"delete\s+(all|everything|database)",
    r"drop\s+table",
    r"rm\s+-rf",
    r"grant\s+(me|access|admin)",
]

# 编译正则表达式
COMPILED_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS]


def contains_prompt_injection(text: str) -> bool:
    """
    检测文本是否包含提示注入攻击

    Args:
        text: 要检测的文本

    Returns:
        True 如果检测到注入攻击，否则 False
    """
    if not text:
        return False

    # 检查每个危险模式
    for pattern in COMPILED_PATTERNS:
        if pattern.search(text):
            return True

    return False


def get_matched_patterns(text: str) -> List[str]:
    """
    获取匹配的危险模式列表

    Args:
        text: 要检测的文本

    Returns:
        匹配的模式列表
    """
    if not text:
        return []

    matched = []
    for i, pattern in enumerate(COMPILED_PATTERNS):
        if pattern.search(text):
            matched.append(DANGEROUS_PATTERNS[i])

    return matched


def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """
    清理用户输入，移除潜在的危险字符

    Args:
        text: 原始输入
        max_length: 最大长度

    Returns:
        清理后的文本
    """
    if not text:
        return ""

    # 1. 限制长度
    sanitized = text[:max_length]

    # 2. 移除控制字符（保留换行和制表符）
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)

    # 3. 规范化空白字符
    sanitized = re.sub(r'\s+', ' ', sanitized)

    return sanitized.strip()


def is_safe_for_ai_prompt(text: str, strict: bool = False) -> tuple[bool, str]:
    """
    检查文本是否安全，可以用于 AI 提示

    Args:
        text: 要检查的文本
        strict: 是否启用严格模式

    Returns:
        (is_safe, reason) - (是否安全, 不安全的原因)
    """
    if not text:
        return True, ""

    # 检查长度
    if len(text) > 10000:
        return False, "输入过长"

    # 检查提示注入
    matched_patterns = get_matched_patterns(text)
    if matched_patterns:
        return False, f"检测到可疑指令: {matched_patterns[0]}"

    # 严格模式：额外检查
    if strict:
        # 检查是否包含过多重复字符（可能是攻击）
        if re.search(r'(.)\1{50,}', text):
            return False, "包含过多重复字符"

        # 检查是否包含过多特殊符号
        special_chars = len(re.findall(r'[^a-zA-Z0-9\u4e00-\u9fa5\s\.\,\!\?\-]', text))
        if special_chars > len(text) * 0.3:
            return False, "包含过多特殊符号"

    return True, ""


def create_safe_prompt(user_input: str, template: str, placeholder: str = "{input}") -> str:
    """
    创建安全的 AI 提示（在模板中安全地插入用户输入）

    Args:
        user_input: 用户输入
        template: 提示模板
        placeholder: 占位符

    Returns:
        安全的提示文本
    """
    # 清理用户输入
    sanitized = sanitize_user_input(user_input)

    # 检查是否安全
    is_safe, reason = is_safe_for_ai_prompt(sanitized, strict=True)
    if not is_safe:
        raise ValueError(f"用户输入不安全: {reason}")

    # 转义特殊字符以防止注入
    # 用引号包裹用户输入
    escaped = sanitized.replace('"', '\\"')

    # 替换占位符
    return template.replace(placeholder, f'"{escaped}"')
