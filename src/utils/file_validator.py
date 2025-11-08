"""文件上传验证工具"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional, Tuple

try:
    import magic

    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

try:
    from pypdf import PdfReader

    HAS_PYPDF = True
except ImportError:
    try:
        # 向后兼容 PyPDF2
        from PyPDF2 import PdfReader

        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False


# MIME 类型白名单
ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "text/x-markdown",
}

# 扩展名到 MIME 类型的映射
EXT_TO_MIME = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}

# 文件大小限制（字节）
MAX_FILE_SIZE = 700 * 1024  # 700KB
MAX_PDF_DECODED_SIZE = 10 * 1024 * 1024  # 10MB


class FileValidationError(Exception):
    """文件验证失败"""

    pass


def verify_mime_type(file_content: bytes, filename: str) -> Tuple[bool, str]:
    """
    验证文件的 MIME 类型

    返回: (is_valid, mime_type)
    """
    ext = Path(filename).suffix.lower()

    # 方法1: 使用 python-magic (推荐)
    if HAS_MAGIC:
        try:
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_buffer(file_content)

            # 验证 MIME 类型是否在白名单中
            if detected_mime not in ALLOWED_MIME_TYPES:
                return False, detected_mime

            # 额外验证：MIME 类型应该与扩展名匹配
            expected_mime = EXT_TO_MIME.get(ext)
            if expected_mime and not detected_mime.startswith(
                expected_mime.split("/")[0]
            ):
                return False, detected_mime

            return True, detected_mime
        except Exception as e:
            print(f"⚠️  MIME 检测失败: {e}")

    # 方法2: 简单的 magic bytes 检查（降级方案）
    if file_content.startswith(b"%PDF"):
        if ext != ".pdf":
            return False, "application/pdf"
        return True, "application/pdf"

    # 对于文本文件，检查是否为有效的 UTF-8
    if ext in {".txt", ".md"}:
        try:
            file_content.decode("utf-8")
            return True, EXT_TO_MIME.get(ext, "text/plain")
        except UnicodeDecodeError:
            return False, "application/octet-stream"

    # 如果没有 magic 库，仅根据扩展名判断
    expected_mime = EXT_TO_MIME.get(ext)
    if expected_mime:
        return True, expected_mime

    return False, "application/octet-stream"


def validate_pdf_size(file_content: bytes) -> Tuple[bool, int]:
    """
    验证 PDF 解码后的大小

    返回: (is_valid, decoded_size)
    """
    if not HAS_PYPDF:
        print("⚠️  pypdf 未安装，跳过 PDF 大小验证")
        return True, 0

    try:
        pdf = PdfReader(io.BytesIO(file_content))
        total_size = 0

        # 估算解码后的大小（提取所有文本）
        for page in pdf.pages:
            try:
                text = page.extract_text()
                total_size += len(text.encode("utf-8"))
            except Exception:
                # 某些页面可能无法提取文本
                continue

        # 如果解码后超过限制，拒绝
        if total_size > MAX_PDF_DECODED_SIZE:
            return False, total_size

        return True, total_size
    except Exception as e:
        print(f"⚠️  PDF 验证失败: {e}")
        return False, 0


def validate_upload_file(
    file_content: bytes, filename: str, max_size: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """
    验证上传的文件

    返回: (is_valid, error_message)
    """
    max_size = max_size or MAX_FILE_SIZE

    # 1. 检查文件大小
    if len(file_content) > max_size:
        return (
            False,
            f"文件过大（{len(file_content) // 1024}KB），最大支持 {max_size // 1024}KB",
        )

    # 2. 检查扩展名
    ext = Path(filename).suffix.lower()
    if ext not in EXT_TO_MIME:
        return False, f"不支持的文件类型: {ext}"

    # 3. 验证 MIME 类型
    is_valid, mime_type = verify_mime_type(file_content, filename)
    if not is_valid:
        return False, f"文件类型验证失败（检测到 {mime_type}，但扩展名为 {ext}）"

    # 4. 对于 PDF，验证解码后大小
    if ext == ".pdf":
        is_valid, decoded_size = validate_pdf_size(file_content)
        if not is_valid:
            return (
                False,
                f"PDF 解码后过大（{decoded_size // 1024 // 1024}MB），最大支持 {MAX_PDF_DECODED_SIZE // 1024 // 1024}MB",
            )

    return True, None


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除路径遍历字符"""
    import re

    # 移除路径分隔符和特殊字符
    cleaned = re.sub(r'[\/\\:*?"<>|]', "", filename)

    # 限制长度
    if len(cleaned) > 255:
        ext = Path(cleaned).suffix
        cleaned = cleaned[:250] + ext

    return cleaned or "untitled"
