#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
上传前验证脚本。

目标不是证明内容完全正确，而是阻止明显错误：
1. Word 原稿、OCR 临时文件和未经筛选的本地图片素材不能进入上传仓库。
2. Markdown 文件不能为空，不能出现明显乱码。
3. 目录中的链接应指向存在的文件。
4. Markdown 数学公式应使用 GitHub 可渲染分隔符。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote


PUBLIC_IMAGE_ROOT = Path("assets") / "images"

IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
}

BANNED_SUFFIXES = {
    ".docx",
    ".doc",
    ".emf",
    ".wmf",
}


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate generated Markdown repository.")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    return parser.parse_args()


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"[FAIL] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def validate_github_math_blocks(path: Path, repo_root: Path, text: str, failures: list[str]) -> None:
    """检查 $$ 块级公式是否按 GitHub 能稳定渲染的方式独立成段。"""

    lines = text.splitlines()
    in_math_block = False
    for index, line in enumerate(lines):
        if line.strip() != "$$":
            continue

        line_no = index + 1
        previous_blank = index == 0 or not lines[index - 1].strip()
        next_blank = index == len(lines) - 1 or not lines[index + 1].strip()

        if not in_math_block:
            if not previous_blank:
                fail(
                    f"块级数学公式开始标记 $$ 前需要空行，避免 GitHub 解析失败: {path.relative_to(repo_root)}:{line_no}",
                    failures,
                )
            in_math_block = True
        else:
            if not next_blank:
                fail(
                    f"块级数学公式结束标记 $$ 后需要空行，避免 GitHub 解析失败: {path.relative_to(repo_root)}:{line_no}",
                    failures,
                )
            in_math_block = False

    if in_math_block:
        fail(f"块级数学公式 $$ 标记未闭合: {path.relative_to(repo_root)}", failures)


def validate_no_banned_files(repo_root: Path, failures: list[str]) -> None:
    local_only_warned = False
    for path in repo_root.rglob("*"):
        relative = path.relative_to(repo_root)
        if ".git" in relative.parts:
            continue
        if "local-only" in relative.parts:
            if not local_only_warned:
                warn("检测到本地-only目录，必须保持 gitignore 不上传: local-only")
                local_only_warned = True
            continue
        if not path.is_file():
            if path.is_dir() and path.name in {"_ocr_tmp", "_tmp"}:
                fail(f"禁止上传的临时或本地目录: {path.relative_to(repo_root)}", failures)
            continue

        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES and not str(relative).replace("\\", "/").startswith("assets/images/"):
            fail(f"图片只能放在公开资源目录 assets/images 下: {path.relative_to(repo_root)}", failures)
        if suffix in BANNED_SUFFIXES:
            fail(f"禁止上传的文件类型: {path.relative_to(repo_root)}", failures)


def validate_markdown_files(repo_root: Path, failures: list[str]) -> None:
    markdown_files = list(repo_root.rglob("*.md"))
    if not markdown_files:
        fail("仓库中没有 Markdown 文件。", failures)
        return

    for path in markdown_files:
        relative_posix = str(path.relative_to(repo_root)).replace("\\", "/")
        if relative_posix.startswith("local-only/"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            fail(f"Markdown 空文件: {path.relative_to(repo_root)}", failures)
        if "\ufffd" in text or "????" in text:
            fail(f"疑似编码乱码: {path.relative_to(repo_root)}", failures)
        if any(marker in text for marker in ("\\[", "\\]", "\\(", "\\)")):
            fail(
                f"检测到 GitHub 不兼容的数学公式分隔符，请使用 $...$ 或 $$...$$: {path.relative_to(repo_root)}",
                failures,
            )
        validate_github_math_blocks(path, repo_root, text, failures)


def validate_required_files(repo_root: Path, failures: list[str]) -> None:
    required = [
        "README.md",
        "LICENSE",
        ".gitignore",
        "CONTRIBUTING.md",
        "DISCLAIMER.md",
        "CITATION.cff",
        "CHANGELOG.md",
        "目录.md",
        "学习路径.md",
        "TODO.md",
        "OCR质量报告.md",
        "引用与版权清理报告.md",
    ]
    for relative in required:
        if not (repo_root / relative).exists():
            fail(f"缺少必需文件: {relative}", failures)


def validate_directory_links(repo_root: Path, failures: list[str]) -> None:
    directory = repo_root / "目录.md"
    if not directory.exists():
        return
    text = directory.read_text(encoding="utf-8", errors="replace")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    for link in links:
        if link.startswith("http://") or link.startswith("https://"):
            continue
        target = repo_root / unquote(link)
        if not target.exists():
            fail(f"目录链接指向不存在的文件: {link}", failures)


def validate_license(repo_root: Path, failures: list[str]) -> None:
    license_path = repo_root / "LICENSE"
    if not license_path.exists():
        return
    text = license_path.read_text(encoding="utf-8", errors="replace")
    if "Attribution-NonCommercial-ShareAlike 4.0" not in text:
        fail("LICENSE 中未检测到 CC BY-NC-SA 4.0 关键字。", failures)


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    failures: list[str] = []

    validate_required_files(repo_root, failures)
    validate_no_banned_files(repo_root, failures)
    validate_markdown_files(repo_root, failures)
    validate_directory_links(repo_root, failures)
    validate_license(repo_root, failures)

    docs_count = len(list((repo_root / "docs").rglob("*.md"))) if (repo_root / "docs").exists() else 0
    if docs_count == 0:
        fail("docs 目录中没有上传版 Markdown。", failures)
    else:
        print(f"[OK] docs Markdown files: {docs_count}")

    if failures:
        print(f"[SUMMARY] validation failed: {len(failures)} issue(s)")
        return 1
    print("[SUMMARY] validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
