#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把本地 Word 笔记转换为可上传 GitHub 的 Markdown 资料库。

设计目标：
1. 不修改任何原始 .docx 文件。
2. 不把 .docx、Word 内嵌图片或 OCR 临时图片放进 Git 仓库。
3. 尽量保留 Word 正文顺序，并在图片位置插入稳定的重建占位。
4. 自动检索正文中的引用线索，把确定不了的引用风险写入报告。
5. 按用户要求：第40章“世界模型与科学发现”只生成本地 Markdown，不上传 GitHub。
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from urllib.parse import quote

try:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
except Exception:  # pragma: no cover - 仅在 Pillow 缺失时触发
    Image = None


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
V_NS = "urn:schemas-microsoft-com:vml"

NS = {
    "w": W_NS,
    "r": R_NS,
    "a": A_NS,
    "rel": REL_NS,
    "v": V_NS,
}


TOP_DIR_SLUGS = {
    "第1部分 深度学习": "01-deep-learning",
    "第2部分 强化学习": "02-reinforcement-learning",
    "第3部分 大语言模型": "03-large-language-model",
    "第4部分 大模型智能体与持续学习": "04-agents-and-continual-learning",
    "第5部分 世界模型、多模态生成与具身智能": "05-world-models-multimodal-embodied-ai",
}


REFERENCE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"https?://",
        r"arxiv",
        r"doi[:：]",
        r"参考",
        r"引用",
        r"来源",
        r"图源",
        r"原论文",
        r"paper",
        r"technical report",
        r"AAAI",
        r"ICML",
        r"ICLR",
        r"NeurIPS",
        r"CVPR",
        r"ACL",
        r"EMNLP",
        r"《[^》]+》",
    ]
]


@dataclass
class Segment:
    """表示 Word 段落中的一个顺序片段：普通文字或图片。"""

    kind: str
    value: str


@dataclass
class ConvertedDoc:
    """记录单个 Word 文档转换后的统计信息和输出位置。"""

    source_path: Path
    source_rel: str
    title: str
    output_path: Path | None
    output_rel: str | None
    local_only: bool
    text_chars: int = 0
    paragraph_count: int = 0
    image_count: int = 0
    ocr_success: int = 0
    ocr_failed: int = 0
    ocr_chars: int = 0
    formula_risk_count: int = 0
    reference_lines: list[str] = field(default_factory=list)
    missing_reference_notes: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert local DOCX notes to Markdown.")
    repo_root = Path(__file__).resolve().parents[1]
    default_source = repo_root.parent.parent
    parser.add_argument("--source-root", type=Path, default=default_source)
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--local-only-root", type=Path, default=repo_root / "local-only")
    parser.add_argument("--ocr-script", type=Path, default=repo_root / "tools" / "winrt_ocr.ps1")
    parser.add_argument(
        "--run-ocr",
        action="store_true",
        help="调试旧流程时才调用 Windows OCR；开源版默认不写入自动 OCR。",
    )
    parser.add_argument("--clean", action="store_true", help="清理旧的生成目录后重新生成。")
    parser.add_argument("--max-docs", type=int, default=None, help="只处理前 N 个文档，用于小样本验证。")
    parser.add_argument("--only-sample", action="store_true", help="只处理一组覆盖不同部分的样本文档。")
    return parser.parse_args()


def read_docx_xml(docx_path: Path, member: str) -> ET.Element | None:
    """从 docx 压缩包中读取指定 XML；不存在时返回 None。"""

    try:
        with zipfile.ZipFile(docx_path) as zf:
            if member not in zf.namelist():
                return None
            return ET.fromstring(zf.read(member))
    except Exception:
        return None


def parse_relationships(docx_path: Path) -> dict[str, str]:
    """读取 document.xml.rels，建立 rId 到 word/media 路径的映射。"""

    root = read_docx_xml(docx_path, "word/_rels/document.xml.rels")
    if root is None:
        return {}

    relationships: dict[str, str] = {}
    for rel in root.findall(f"{{{REL_NS}}}Relationship"):
        r_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        mode = rel.attrib.get("TargetMode")
        if not r_id or not target or mode == "External":
            continue
        relationships[r_id] = posixpath.normpath(posixpath.join("word", target))
    return relationships


def collect_run_text(run: ET.Element) -> str:
    """抽取一个 w:r run 内的文字、制表符和换行。"""

    pieces: list[str] = []
    for node in run.iter():
        if node.tag == f"{{{W_NS}}}t" and node.text:
            pieces.append(node.text)
        elif node.tag == f"{{{W_NS}}}tab":
            pieces.append("\t")
        elif node.tag == f"{{{W_NS}}}br":
            pieces.append("\n")
    return "".join(pieces)


def collect_image_rids(node: ET.Element) -> list[str]:
    """从一个 XML 节点里抽取 DrawingML/VML 图片关系 ID。"""

    rids: list[str] = []
    for blip in node.findall(".//a:blip", NS):
        r_id = blip.attrib.get(f"{{{R_NS}}}embed") or blip.attrib.get(f"{{{R_NS}}}link")
        if r_id:
            rids.append(r_id)
    for image_data in node.findall(".//v:imagedata", NS):
        r_id = image_data.attrib.get(f"{{{R_NS}}}id")
        if r_id:
            rids.append(r_id)
    return rids


def paragraph_segments(paragraph: ET.Element) -> list[Segment]:
    """按 Word 段落内部顺序生成文字和图片片段。

    Word 的图片通常挂在 run 内部。这里按 run 的顺序处理，尽量让 OCR
    文字出现在原图片所在位置附近。
    """

    segments: list[Segment] = []
    for child in paragraph:
        if child.tag == f"{{{W_NS}}}r":
            text = collect_run_text(child)
            if text:
                segments.append(Segment("text", text))
            for r_id in collect_image_rids(child):
                segments.append(Segment("image", r_id))
        elif child.tag == f"{{{W_NS}}}hyperlink":
            for run in child.findall(".//w:r", NS):
                text = collect_run_text(run)
                if text:
                    segments.append(Segment("text", text))
                for r_id in collect_image_rids(run):
                    segments.append(Segment("image", r_id))
        else:
            for r_id in collect_image_rids(child):
                segments.append(Segment("image", r_id))
    return segments


def iter_paragraphs(docx_path: Path) -> Iterable[ET.Element]:
    """按 document.xml 顺序遍历所有段落，包括表格中的段落。"""

    root = read_docx_xml(docx_path, "word/document.xml")
    if root is None:
        return []
    return root.findall(".//w:p", NS)


def sanitize_filename(name: str) -> str:
    """把 Word 文件名转成相对稳定、不会明显超长的 Markdown 文件名。"""

    name = Path(name).stem
    name = name.replace("（", "-").replace("）", "")
    name = name.replace("(", "-").replace(")", "")
    name = name.replace("：", "-").replace(":", "-")
    name = name.replace("、", "-")
    name = name.replace(" ", "-")
    name = re.sub(r"-+", "-", name).strip("-")

    match = re.match(r"^(\d+)\.(\d+)\s*(.*)$", name)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        title = match.group(3).strip("- ")
        return f"{major:02d}-{minor:02d}-{title}.md"

    match = re.match(r"^(\d+)\s*(.*)$", name)
    if match:
        major = int(match.group(1))
        title = match.group(2).strip("- ")
        return f"{major:02d}-{title}.md"

    return f"{name}.md"


def sanitize_dirname(name: str) -> str:
    """把章节目录名转成较短但仍可读的目录名。"""

    name = name.replace(" ", "-")
    match = re.match(r"^(\d+)\.(.*)$", name)
    if match:
        return f"{int(match.group(1)):02d}-{match.group(2).strip('-')}"
    return name


def rel_to_posix(path: Path) -> str:
    return path.as_posix()


def markdown_link(path: str) -> str:
    return quote(path.replace("\\", "/"), safe="/")


def is_root_usage_doc(source_root: Path, path: Path) -> bool:
    return path.parent == source_root and path.name == "使用说明.docx"


def is_chapter40(path: Path, source_root: Path) -> bool:
    try:
        rel = path.relative_to(source_root)
    except ValueError:
        return False
    return len(rel.parts) >= 2 and rel.parts[1].startswith("40.")


def is_note_doc(source_root: Path, path: Path) -> bool:
    """判断一个 docx 是否属于笔记正文，而不是说明文件或导出目录内容。"""

    try:
        rel = path.relative_to(source_root)
    except ValueError:
        return False

    if "github-export" in rel.parts:
        return False
    if path.name.startswith("~$"):
        return False
    if is_root_usage_doc(source_root, path):
        return False
    return path.suffix.lower() == ".docx"


def discover_docx(source_root: Path, only_sample: bool, max_docs: int | None) -> list[Path]:
    docs = sorted(p for p in source_root.rglob("*.docx") if is_note_doc(source_root, p))
    if only_sample:
        prefixes = ["1.2 ", "13.3 ", "15.3 ", "25.1 ", "34.1 ", "40.1 "]
        sample: list[Path] = []
        for prefix in prefixes:
            found = next((p for p in docs if p.name.startswith(prefix)), None)
            if found is not None:
                sample.append(found)
        docs = sample
    if max_docs is not None:
        docs = docs[:max_docs]
    return docs


def output_path_for_doc(source_root: Path, repo_root: Path, local_only_root: Path, docx_path: Path) -> tuple[Path, bool]:
    """计算 Markdown 输出位置。

    第40章按用户要求输出到 repo 外的 local-only/chapter40_markdown，不进入上传仓库。
    """

    rel = docx_path.relative_to(source_root)
    top = rel.parts[0]
    top_slug = TOP_DIR_SLUGS.get(top, sanitize_dirname(top))
    subdirs = [sanitize_dirname(part) for part in rel.parts[1:-1]]
    filename = sanitize_filename(rel.name)

    if is_chapter40(docx_path, source_root):
        return local_only_root / "chapter40_markdown" / top_slug / Path(*subdirs) / filename, True

    return repo_root / "docs" / top_slug / Path(*subdirs) / filename, False


def extract_usage_text(source_root: Path) -> str:
    usage = source_root / "使用说明.docx"
    if not usage.exists():
        return ""
    paragraphs = []
    for paragraph in iter_paragraphs(usage):
        text = "".join(seg.value for seg in paragraph_segments(paragraph) if seg.kind == "text").strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def clean_ocr_text(text: str) -> str:
    """清理 Windows OCR 常见的中文间隔空格，但不过度修正内容。"""

    text = normalize_text(text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\s+([，。！？；：、）】])", r"\1", text)
    text = re.sub(r"([（【])\s+", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def has_formula_risk(text: str) -> bool:
    """判断 OCR 文本是否疑似包含数学公式。

    OCR 对公式、上下标、希腊字母和分式最容易出错。这里宁可多标一些
    “需要公式校对”，也不能把自动识别结果伪装成可靠公式。
    """

    if not text.strip():
        return False

    math_symbol_pattern = re.compile(
        r"[=≈≠≤≥∑∫∂√∞∈∀∃∇±×÷⊙⊗αβγδθλμσπφϕωΔΠΣ]|"
        r"(?:\^|_)\{?[A-Za-z0-9]+|"
        r"\\(?:frac|sum|int|theta|lambda|alpha|beta|gamma|delta|mu|sigma|pi)|"
        r"\b(?:softmax|argmax|argmin|log|exp|loss|KL|MSE|CE)\b|"
        r"\b(?:p|q|P|Q|L|J|V|A|E)\s*[\(\[]"
    )
    if math_symbol_pattern.search(text):
        return True

    # 如果一段 OCR 里数字、括号和运算符密度很高，也按公式风险处理。
    compact = re.sub(r"\s+", "", text)
    if len(compact) >= 12:
        math_like = sum(1 for ch in compact if ch.isdigit() or ch in "+-*/=()[]{}.,;:|<>")
        if math_like / max(len(compact), 1) > 0.28:
            return True
    return False


def paragraph_to_markdown(text: str) -> str:
    """把普通段落转换成轻量 Markdown。

    这里只做非常保守的标题提升，不重排原文，避免破坏学习笔记内容。
    """

    text = normalize_text(text)
    if not text:
        return ""
    if re.match(r"^[一二三四五六七八九十]+、", text):
        return f"## {text}"
    if re.match(r"^（[一二三四五六七八九十]+）", text):
        return f"### {text}"
    return text


def prepare_image_for_ocr(image_bytes: bytes, media_name: str, target_dir: Path, index: int) -> Path:
    """把 Word 内嵌图片写入 OCR 临时目录，必要时用 Pillow 缩放。

    Windows OCR 对超大图片不稳定。这里把最长边限制在 2500 像素左右，
    兼顾识别速度和文字清晰度。
    """

    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(media_name).suffix.lower() or ".png"
    raw_target = target_dir / f"image_{index:04d}{suffix}"

    if Image is None:
        raw_target.write_bytes(image_bytes)
        return raw_target

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            max_side = max(img.size)
            if max_side > 2500:
                scale = 2500 / max_side
                new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
                img = img.resize(new_size)
            target = target_dir / f"image_{index:04d}.png"
            img.save(target, "PNG")
            return target
    except Exception:
        raw_target.write_bytes(image_bytes)
        return raw_target


def run_windows_ocr(ocr_script: Path, image_paths: dict[str, Path], work_dir: Path) -> dict[str, tuple[str, str]]:
    """调用 PowerShell WinRT OCR 脚本，返回 id -> (text, error)。"""

    if not image_paths:
        return {}

    input_json = work_dir / "ocr_input.json"
    output_json = work_dir / "ocr_output.json"
    payload = {
        "items": [
            {"id": image_id, "path": str(path.resolve())}
            for image_id, path in sorted(image_paths.items())
        ]
    }
    # PowerShell 5.1 对无 BOM UTF-8 和中文路径都比较脆弱。
    # 这里使用 ASCII JSON（中文写成 \uXXXX），由 ConvertFrom-Json 解码回真实路径。
    input_json.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ocr_script.resolve()),
        "-InputJson",
        str(input_json.resolve()),
        "-OutputJson",
        str(output_json.resolve()),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return {
            image_id: ("", f"PowerShell OCR failed: {result.stderr.strip() or result.stdout.strip()}")
            for image_id in image_paths
        }

    try:
        data = json.loads(output_json.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {image_id: ("", f"Cannot parse OCR output: {exc}") for image_id in image_paths}

    outputs: dict[str, tuple[str, str]] = {}
    for item in data.get("results", []):
        outputs[str(item.get("id", ""))] = (
            clean_ocr_text(str(item.get("text", "") or "")),
            str(item.get("error", "") or ""),
        )
    return outputs


def load_media_bytes(docx_path: Path, media_paths: list[str]) -> dict[str, bytes]:
    """一次性从 docx 中读取需要 OCR 的媒体文件。"""

    unique_paths = sorted(set(media_paths))
    outputs: dict[str, bytes] = {}
    with zipfile.ZipFile(docx_path) as zf:
        names = set(zf.namelist())
        for media_path in unique_paths:
            if media_path in names:
                outputs[media_path] = zf.read(media_path)
    return outputs


def extract_reference_lines(lines: list[str]) -> list[str]:
    """从正文和 OCR 文本里抽取疑似引用线索。"""

    references: list[str] = []
    seen: set[str] = set()
    for line in lines:
        compact = re.sub(r"\s+", " ", line).strip()
        if not compact:
            continue
        if any(pattern.search(compact) for pattern in REFERENCE_PATTERNS):
            clipped = compact[:240] + ("..." if len(compact) > 240 else "")
            if clipped not in seen:
                seen.add(clipped)
                references.append(clipped)
    return references[:30]


def missing_reference_notes(title: str, lines: list[str], reference_lines: list[str], image_count: int) -> list[str]:
    """根据文件名和正文特征生成待补引用提示。

    这里不猜测具体论文来源，只标出需要人工确认的位置，避免把错误来源写进开源资料。
    """

    joined = "\n".join(lines)
    notes: list[str] = []
    if "论文" in title and not any(re.search(r"https?://|arxiv|doi|原论文|参考", line, re.I) for line in reference_lines):
        notes.append("本文标题标记为论文笔记，但未自动发现原论文链接、arXiv/DOI、作者或年份，建议人工补充。")
    if image_count > 0:
        notes.append("本文含 Word 内嵌图片；开源版未上传图片。若图片来自教材、论文或技术报告，建议人工确认授权、补充来源或重画。")
    if re.search(r"图源|截图|教材|《动手学", joined) and not reference_lines:
        notes.append("正文疑似提到图源、截图或教材来源，但未抽取到完整引用，建议人工检查。")
    if not reference_lines and ("论文" in title or image_count > 0):
        notes.append("未自动检索到明确参考文献线索，建议人工补充可追溯来源。")
    return notes


def convert_single_doc(
    source_root: Path,
    repo_root: Path,
    local_only_root: Path,
    ocr_script: Path,
    docx_path: Path,
    skip_ocr: bool,
    temp_root: Path,
) -> ConvertedDoc:
    """转换单个 docx，返回统计记录。"""

    output_path, local_only = output_path_for_doc(source_root, repo_root, local_only_root, docx_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_rel = rel_to_posix(docx_path.relative_to(source_root))
    output_rel = None if local_only else rel_to_posix(output_path.relative_to(repo_root))
    title = docx_path.stem
    record = ConvertedDoc(
        source_path=docx_path,
        source_rel=source_rel,
        title=title,
        output_path=output_path,
        output_rel=output_rel,
        local_only=local_only,
    )

    relationships = parse_relationships(docx_path)
    paragraphs = list(iter_paragraphs(docx_path))
    record.paragraph_count = len(paragraphs)

    blocks: list[Segment] = []
    media_in_order: list[str] = []

    for paragraph in paragraphs:
        buffer: list[str] = []
        for segment in paragraph_segments(paragraph):
            if segment.kind == "text":
                buffer.append(segment.value)
            elif segment.kind == "image":
                text = "".join(buffer).strip()
                if text:
                    blocks.append(Segment("text", text))
                    buffer = []
                media_path = relationships.get(segment.value)
                if media_path:
                    blocks.append(Segment("image", media_path))
                    media_in_order.append(media_path)
        text = "".join(buffer).strip()
        if text:
            blocks.append(Segment("text", text))

    record.image_count = len(media_in_order)
    record.text_chars = sum(len(block.value) for block in blocks if block.kind == "text")

    ocr_by_media: dict[str, tuple[str, str]] = {}
    if media_in_order and not skip_ocr:
        # OCR 临时目录只用 ASCII 哈希名，避免 Windows PowerShell 5.1
        # 读取 JSON 后在中文路径上出现编码和反斜杠转义问题。
        doc_work_dir = temp_root / f"run_{os.getpid()}" / f"doc_{hashlib.sha1(source_rel.encode('utf-8')).hexdigest()[:16]}"
        doc_work_dir.mkdir(parents=True, exist_ok=True)

        media_bytes = load_media_bytes(docx_path, media_in_order)
        image_paths: dict[str, Path] = {}
        media_to_id: dict[str, str] = {}
        for index, media_path in enumerate(sorted(set(media_in_order)), start=1):
            image_id = f"img_{index:04d}"
            media_to_id[media_path] = image_id
            if media_path not in media_bytes:
                ocr_by_media[media_path] = ("", "Media file is missing in docx package.")
                continue
            image_paths[image_id] = prepare_image_for_ocr(
                media_bytes[media_path],
                media_path,
                doc_work_dir,
                index,
            )

        ocr_outputs = run_windows_ocr(ocr_script, image_paths, doc_work_dir)
        for media_path, image_id in media_to_id.items():
            ocr_by_media[media_path] = ocr_outputs.get(image_id, ("", "OCR did not return a result."))

    markdown_lines: list[str] = [
        "---",
        f'title: "{title}"',
        f'source_docx: "{source_rel}"',
        'status: "auto-converted"',
        'ocr: "disabled; image content awaits manual reconstruction"',
        'license: "CC BY-NC-SA 4.0"',
        f'local_only: {"true" if local_only else "false"}',
        "---",
        "",
        f"# {title}",
        "",
        "> 本文由本地 Word 原稿自动转换而来。图片内容暂不使用自动 OCR；含公式、图示或表格的图片会在后续人工重建为 Markdown/LaTeX。",
        "",
    ]

    if "论文" in title:
        markdown_lines.extend(
            [
                "> 本文是论文阅读笔记，内容代表对应论文方法或作者理解，不应直接视为领域共识或工程最佳实践。",
                "",
            ]
        )

    content_lines_for_reference: list[str] = []
    image_index = 0
    output_rel_for_id = output_path.relative_to(local_only_root if local_only else repo_root).as_posix()
    output_id = hashlib.sha1(output_rel_for_id.encode("utf-8")).hexdigest()[:12]
    for block in blocks:
        if block.kind == "text":
            md = paragraph_to_markdown(block.value)
            if md:
                markdown_lines.extend([md, ""])
                content_lines_for_reference.append(block.value)
        elif block.kind == "image":
            image_index += 1
            rebuild_id = f"img-{output_id}-{image_index:04d}"
            text, error = ocr_by_media.get(block.value, ("", "OCR skipped." if skip_ocr else "OCR result missing."))
            markdown_lines.append(
                f"> [图片内容待重建：{rebuild_id}] 原 Word 此处有图片。"
                "为避免版权风险，开源版暂不上传图片；自动 OCR 已弃用，后续将依据原稿人工重建为 Markdown/LaTeX。"
            )
            if text:
                record.ocr_success += 1
                record.ocr_chars += len(text)
                formula_risk = has_formula_risk(text)
                if formula_risk:
                    record.formula_risk_count += 1
                markdown_lines.extend(
                    [
                        "",
                        "**图片文字 OCR（自动识别，待校对；数学公式必须人工核对）：**",
                        "",
                    ]
                )
                if formula_risk:
                    markdown_lines.extend(
                        [
                            "> [公式校对警告] 这段 OCR 文本疑似包含数学公式、上下标、希腊字母或高密度符号。请不要直接把自动识别结果视为可靠公式。",
                            "",
                        ]
                    )
                markdown_lines.extend([text, ""])
                content_lines_for_reference.append(text)
            elif not skip_ocr:
                record.ocr_failed += 1
                message = error or "未识别出有效文字。"
                markdown_lines.extend(["", f"> [图片 {image_index} OCR 未识别出有效文字：{message}]", ""])

    record.reference_lines = extract_reference_lines(content_lines_for_reference)
    record.missing_reference_notes = missing_reference_notes(
        title=title,
        lines=content_lines_for_reference,
        reference_lines=record.reference_lines,
        image_count=record.image_count,
    )

    markdown_lines.extend(["## 参考文献与引用线索", ""])
    markdown_lines.append("> 本节由脚本自动检索正文中的引用线索，可能不完整；未能确定来源的位置会在下方标为待补引用。")
    markdown_lines.append("")
    if record.reference_lines:
        markdown_lines.append("### 自动检索到的引用线索")
        markdown_lines.append("")
        for ref in record.reference_lines:
            markdown_lines.append(f"- {ref}")
        markdown_lines.append("")
    if record.missing_reference_notes:
        markdown_lines.append("### 待补引用或版权检查")
        markdown_lines.append("")
        for note in record.missing_reference_notes:
            markdown_lines.append(f"- [待补引用] {note}")
        markdown_lines.append("")
    if not record.reference_lines and not record.missing_reference_notes:
        markdown_lines.append("- 暂未自动检索到明显引用线索。")
        markdown_lines.append("")

    output_path.write_text("\n".join(markdown_lines).rstrip() + "\n", encoding="utf-8")
    return record


def clean_outputs(repo_root: Path, local_only_root: Path) -> None:
    """清理脚本生成物。只删除导出目录内的生成内容，不接触 Word 原稿。"""

    safe_targets = [
        repo_root / "docs",
        repo_root / "OCR质量报告.md",
        repo_root / "引用与版权清理报告.md",
        repo_root / "目录.md",
        repo_root / "学习路径.md",
        repo_root / "TODO.md",
        repo_root / "README.md",
        repo_root / "LICENSE",
        repo_root / ".gitignore",
        repo_root / "CONTRIBUTING.md",
        repo_root / "DISCLAIMER.md",
        repo_root / "CITATION.cff",
        repo_root / "CHANGELOG.md",
        local_only_root / "chapter40_markdown",
    ]
    for target in safe_targets:
        resolved = target.resolve()
        if repo_root.resolve() not in resolved.parents and local_only_root.resolve() not in resolved.parents:
            raise RuntimeError(f"Refuse to clean outside export roots: {target}")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def build_directory_markdown(records: list[ConvertedDoc]) -> str:
    upload_records = [record for record in records if not record.local_only and record.output_rel]
    grouped: dict[str, list[ConvertedDoc]] = {}
    for record in upload_records:
        top = record.source_rel.split("/")[0]
        grouped.setdefault(top, []).append(record)

    lines = [
        "# 目录",
        "",
        "本目录由脚本根据本地 Word 原稿自动生成。第40章“世界模型与科学发现”按作者要求只在本地转换为 Markdown，不上传 GitHub。",
        "",
    ]
    for top in sorted(grouped):
        lines.extend([f"## {top}", ""])
        for record in sorted(grouped[top], key=lambda item: item.source_rel):
            assert record.output_rel is not None
            link = markdown_link(record.output_rel)
            flags = []
            if "论文" in record.title:
                flags.append("论文笔记")
            if record.ocr_failed:
                flags.append("OCR待校对")
            suffix = f"（{'，'.join(flags)}）" if flags else ""
            lines.append(f"- [{record.title}]({link}){suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_learning_path_markdown() -> str:
    return textwrap.dedent(
        """\
        # 学习路径

        本文件面向第一次进入仓库的学习者，给出几条可执行的阅读路线。笔记内容覆盖面很广，不建议从目录第一篇开始机械阅读。

        ## 路线 A：人工智能入门

        适合已有基础数学和编程能力，但还没有系统学习深度学习的读者。

        1. 第1部分：1.深度学习基础理论
        2. 第1部分：2.神经网络训练的常用方法
        3. 第1部分：3.1 卷积神经网络（CNN）
        4. 第1部分：3.4 残差网络（ResNet）
        5. 第3部分：15.注意力机制与Transformer
        6. 第3部分：16.大语言模型的基本原理

        ## 路线 B：强化学习

        适合希望理解经典 RL、RLHF、PPO、GRPO 等内容的读者。

        1. 第2部分：10.强化学习的基本知识
        2. 第2部分：11.基于价值的强化学习
        3. 第2部分：12.基于策略的强化学习
        4. 第2部分：13.综合价值与策略的算法
        5. 第3部分：17.强化微调

        ## 路线 C：大语言模型与智能体

        适合希望系统理解现代 LLM 架构、训练、推理、工具调用和 RAG 的读者。

        1. 第3部分：15.注意力机制与Transformer
        2. 第3部分：16.大语言模型的基本原理
        3. 第3部分：17.强化微调
        4. 第3部分：19.注意力机制的工程优化
        5. 第4部分：22.大模型智能体
        6. 第4部分：23.工具调用
        7. 第4部分：25.检索增强生成
        8. 第4部分：26.上下文与记忆

        ## 路线 D：世界模型、多模态生成与具身智能

        适合已经具备深度学习、Transformer 和生成模型基础，想了解前沿研究方向的读者。

        1. 第5部分：30.扩散模型与流匹配模型的原理和架构
        2. 第5部分：31.扩散模型与流匹配模型的强化学习
        3. 第5部分：32.具身智能的基本知识
        4. 第5部分：33.世界模型的基本知识
        5. 第5部分：34.多模态生成与生成式世界模型
        6. 第5部分：35-39 相关论文笔记

        ## 阅读提示

        - 标题含“论文”的文档通常是前沿论文阅读笔记，不代表领域共识或业界标准做法。
        - 图片内容暂不使用自动 OCR；公式、表格和图示会按批次人工重建。
        - 如果你发现概念错误、公式错误、引用缺失或图片重建问题，欢迎通过 Issue 反馈。
        """
    )


def build_readme(records: list[ConvertedDoc], usage_text: str) -> str:
    upload_count = sum(1 for record in records if not record.local_only)
    local_only_count = sum(1 for record in records if record.local_only)
    image_count = sum(record.image_count for record in records)
    usage_excerpt = usage_text[:2800].strip()
    return f"""# A Comprehensive AI Learning Note

这是一份面向人工智能学习者的中文学习笔记，内容覆盖深度学习、强化学习、大语言模型、大模型智能体、持续学习、世界模型、多模态生成与具身智能等方向。

本仓库由作者叶逸文的本地 Word 笔记自动转换而来。原始 Word 文件不上传 GitHub；本仓库只保存可搜索、可阅读、便于协作纠错的 Markdown 版本。

## 内容范围

- 第1部分：深度学习
- 第2部分：强化学习
- 第3部分：大语言模型
- 第4部分：大模型智能体与持续学习
- 第5部分：世界模型、多模态生成与具身智能

当前上传 Markdown 文档数：`{upload_count}`。

第40章“世界模型与科学发现”已按作者要求转换为本地 Markdown，但不上传 GitHub。本地转换数量：`{local_only_count}`。

## 推荐入口

- [学习路径](学习路径.md)
- [完整目录](目录.md)
- [图片重建与OCR处理报告](OCR质量报告.md)
- [引用与版权清理报告](引用与版权清理报告.md)
- [免责声明](DISCLAIMER.md)
- [贡献说明](CONTRIBUTING.md)

## 图片与OCR说明

Word 原稿中有部分内容是图片格式。早期转换曾尝试使用普通 OCR，但数学公式、上下标、矩阵、表格和复杂图示的识别质量不可接受，因此开源版已放弃自动 OCR 文本。

- 本次检测到 Word 内嵌图片数量：`{image_count}`
- 公开 Markdown 中保留的图片重建占位数量：`{image_count}`
- 自动 OCR 正文写入状态：`已弃用`

每个图片位置都有稳定的 `img-...` 重建 ID。后续会依据本地 Word 原稿和本地图片清单，按章节把图片内容人工重建为 Markdown/LaTeX；无法确认的内容会明确标注为待复核。

为避免教材截图、论文图、技术报告图等材料产生版权风险，开源仓库不上传 Word 内嵌图片，也不保留普通 OCR 生成的乱码公式。

## 资料来源与可靠性

这份资料本来是个人学习笔记，包含作者整理、教材学习笔记、论文阅读笔记、业界动态整理，以及 AI 辅助写作和修改。自动转换脚本会检索正文中的引用线索并标注，但仍可能存在当时漏标来源的情况。请以原论文、官方文档和权威教材为最终依据。

标题含“论文”的文档通常是对学界或业界探索性工作的阅读笔记，不代表领域共识或业界标准范式。

## 许可协议

本仓库采用 [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/) 协议。

简要来说，你可以在署名、非商用、相同方式共享的条件下复制、分享和改编本项目内容。完整法律文本以 `LICENSE` 和 Creative Commons 官方页面为准。

## 原始说明摘录

以下内容来自本地 `使用说明.docx` 的自动抽取文本，作为项目定位说明：

```text
{usage_excerpt}
```
"""


def build_disclaimer() -> str:
    return textwrap.dedent(
        """\
        # 免责声明

        本仓库是个人学习笔记的 Markdown 开源版本，不是正式教材、论文或官方文档。

        ## 内容准确性

        人工智能领域更新很快，笔记中的部分内容可能存在理解偏差、表达不严谨、信息过时或引用缺失。请以原论文、官方文档、权威教材和可复现实验为最终依据。

        ## AI 辅助写作说明

        本资料包含作者个人整理、教材和论文学习笔记，以及 AI 工具辅助生成、改写或校对的内容。作者已尽量进行整理和判断，但不能保证所有内容完全准确。

        ## 图片与OCR说明

        本仓库的 Markdown 文件由本地 Word 原稿转换而来。Word 中的图片内容不再使用普通 OCR 写入正文；数学公式、上下标、希腊字母、分式、矩阵、表格、代码截图、小字号图注和复杂论文图会按批次人工重建。重建完成前，图片占位不代表内容缺失已解决。

        ## 前沿研究说明

        标题含“论文”的文档通常是论文阅读笔记，代表对应论文方法或作者理解，不应直接视为领域共识、工程最佳实践或业界标准范式。
        """
    )


def build_contributing() -> str:
    return textwrap.dedent(
        """\
        # 贡献说明

        欢迎通过 Issue 或 Pull Request 帮助改进这份 AI 学习笔记。

        ## 推荐反馈类型

        - 概念错误
        - 公式错误
        - 图片内容重建错误或缺失
        - 引用缺失
        - 过时信息
        - 版权风险提示
        - 学习路径建议
        - 排版和链接问题

        ## 提交 Issue 时建议包含

        - 出错文档路径
        - 原文片段
        - 问题说明
        - 推荐修改
        - 参考来源链接或论文信息

        ## 提交 PR 时建议遵守

        - 保持中文表达准确、清晰、克制。
        - 重建图片内容时，尽量只补充图片对应的文字、公式、表格或图示说明。
        - 补引用时优先使用原论文、官方文档、教材页面或作者项目页。
        - 不上传未经确认可复用的教材截图、论文图或商业资料截图。
        - 不提交 Word 原稿、临时文件、缓存文件或本地图片重建素材。
        """
    )


def build_license() -> str:
    return textwrap.dedent(
        """\
        Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International

        This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

        You are free to:

        - Share: copy and redistribute the material in any medium or format.
        - Adapt: remix, transform, and build upon the material.

        Under the following terms:

        - Attribution: You must give appropriate credit, provide a link to the license, and indicate if changes were made.
        - NonCommercial: You may not use the material for commercial purposes.
        - ShareAlike: If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.
        - No additional restrictions: You may not apply legal terms or technological measures that legally restrict others from doing anything the license permits.

        Full license text:
        https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode
        """
    )


def build_gitignore() -> str:
    return textwrap.dedent(
        """\
        # Word 原稿和 Office 临时文件不得上传
        *.docx
        ~$*

        # OCR 和转换临时目录
        _ocr_tmp/
        _tmp/
        local-only/
        ../local-only/
        ../_tmp/

        # Python 缓存
        __pycache__/
        *.py[cod]
        .pytest_cache/

        # 系统和编辑器文件
        .DS_Store
        Thumbs.db
        desktop.ini

        # 本地环境和密钥
        .env
        .env.*
        *.pem
        *.key
        """
    )


def build_citation() -> str:
    return textwrap.dedent(
        """\
        cff-version: 1.2.0
        title: "A Comprehensive AI Learning Note"
        message: "If you use this learning note, please cite it as below."
        type: dataset
        authors:
          - family-names: "Ye"
            given-names: "Yiwen"
        repository-code: "https://github.com/yeyiwen2006/a_comprehensive_ai_learning_note"
        license: "CC-BY-NC-SA-4.0"
        abstract: "A Chinese AI learning note covering deep learning, reinforcement learning, large language models, agents, continual learning, world models, multimodal generation, and embodied AI."
        """
    )


def build_changelog() -> str:
    today = date.today().isoformat()
    return textwrap.dedent(
        f"""\
        # 更新记录

        ## {today}

        - 初始化 GitHub 开源版资料库。
        - 从本地 Word 原稿自动生成 Markdown。
        - 放弃普通 OCR 公式文本，图片位置改为稳定重建占位。
        - 按作者要求不上传 Word 原稿和图片。
        - 按作者要求第40章只在本地转换，不上传 GitHub。
        """
    )


def build_todo(records: list[ConvertedDoc]) -> str:
    lines = [
        "# TODO",
        "",
        "本文件记录开源后仍需人工处理的事项。图片内容已放弃普通 OCR，需要按章节人工重建为 Markdown/LaTeX。",
        "",
        "## 图片内容待重建",
        "",
        "- [ ] 按 `local-only/image-reconstruction/manifest.jsonl` 从第 1 章开始逐张重建图片内容。",
        "- [ ] 将可确认的公式写为 LaTeX，将表格写为 Markdown 表格或 HTML 表格。",
        "- [ ] 对无法确认的图片内容保留明确的待复核标记，不猜测公式。",
        "",
    ]
    lines.extend(["", "## 待补引用与版权检查", ""])
    ref_risky = [record for record in records if record.missing_reference_notes]
    for record in sorted(ref_risky, key=lambda item: (-len(item.missing_reference_notes), item.source_rel))[:120]:
        location = record.output_rel or f"local-only: {record.source_rel}"
        lines.append(f"- [ ] {location}")
        for note in record.missing_reference_notes[:3]:
            lines.append(f"  - {note}")
    if not ref_risky:
        lines.append("- 暂无。")

    lines.extend(
        [
            "",
            "## 后续建设",
            "",
            "- [ ] 人工重建核心学习路径中的图片公式、图示和表格。",
            "- [ ] 给论文笔记补充原论文标题、作者、年份、会议或 arXiv 链接。",
            "- [ ] 对疑似教材或论文截图的内容重画图或删除图片依赖。",
            "- [ ] 未来可考虑迁移到 MkDocs、VitePress 或 Docusaurus，提供站内搜索和侧边栏导航。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_ocr_report(records: list[ConvertedDoc]) -> str:
    lines = [
        "# 图片重建与OCR处理报告",
        "",
        "本报告由转换脚本自动生成，用于说明每个 Word 文档的正文抽取和图片重建状态。普通 OCR 已弃用，不再把 OCR 文本写入公开 Markdown。",
        "",
        "| 文档 | 上传状态 | 正文字数 | 图片数 | 图片重建状态 |",
        "|---|---:|---:|---:|---|",
    ]
    for record in sorted(records, key=lambda item: item.source_rel):
        status = "local-only" if record.local_only else "upload"
        doc_label = record.output_rel or record.source_rel
        rebuild_status = "待重建" if record.image_count else "无图片"
        lines.append(
            f"| {doc_label} | {status} | {record.text_chars} | {record.image_count} | {rebuild_status} |"
        )
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 普通 OCR 已确认不适合本资料中的公式、表格、代码截图和复杂论文图。",
            "- 公开 Markdown 只保留图片重建占位，不上传 Word 内嵌图片。",
            "- 第40章按作者要求只生成本地 Markdown，不上传 GitHub。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_reference_report(records: list[ConvertedDoc]) -> str:
    lines = [
        "# 引用与版权清理报告",
        "",
        "本报告自动检索正文中的参考文献线索，并列出需要人工补充来源或检查版权的位置。",
        "",
        "## 待补引用或版权检查",
        "",
    ]
    risky = [record for record in records if record.missing_reference_notes]
    if risky:
        for record in sorted(risky, key=lambda item: item.source_rel):
            location = record.output_rel or f"local-only: {record.source_rel}"
            lines.append(f"### {location}")
            lines.append("")
            for note in record.missing_reference_notes:
                lines.append(f"- {note}")
            if record.reference_lines:
                lines.append("")
                lines.append("自动检索到的线索：")
                for ref in record.reference_lines[:8]:
                    lines.append(f"- {ref}")
            lines.append("")
    else:
        lines.append("- 暂无。")
        lines.append("")

    lines.extend(["## 已检索到的引用线索摘要", ""])
    with_refs = [record for record in records if record.reference_lines]
    for record in sorted(with_refs, key=lambda item: item.source_rel):
        location = record.output_rel or f"local-only: {record.source_rel}"
        lines.append(f"### {location}")
        lines.append("")
        for ref in record.reference_lines[:12]:
            lines.append(f"- {ref}")
        lines.append("")
    if not with_refs:
        lines.append("- 暂无。")

    return "\n".join(lines).rstrip() + "\n"


def build_structure_doc() -> str:
    return textwrap.dedent(
        """\
        # 项目结构说明

        本文件说明 GitHub 开源版项目结构，以及转换脚本中每个函数的职责。

        ## 目录结构

        - `README.md`：项目首页，说明资料定位、内容范围、OCR 状态、许可协议和入口链接。
        - `LICENSE`：CC BY-NC-SA 4.0 许可说明。
        - `.gitignore`：防止 Word 原稿、Office 临时文件、OCR 临时图片、本地密钥和缓存进入仓库。
        - `CONTRIBUTING.md`：说明如何反馈错误、补充引用、提交 PR。
        - `DISCLAIMER.md`：说明个人笔记、AI 辅助写作、OCR 误差和前沿研究风险。
        - `CITATION.cff`：推荐引用格式。
        - `CHANGELOG.md`：开源版更新记录。
        - `目录.md`：自动生成的全量上传目录。
        - `学习路径.md`：面向不同学习目标的阅读路线。
        - `TODO.md`：OCR 校对、引用补充和版权检查待办。
        - `OCR质量报告.md`：每个文档的正文、图片和 OCR 统计。
        - `引用与版权清理报告.md`：自动检索到的引用线索和待补引用位置。
        - `docs/`：由 Word 原稿自动转换出的 Markdown 正文。第40章不在此目录内。
        - `tools/convert_docx_to_markdown.py`：批量转换脚本。
        - `tools/winrt_ocr.ps1`：调用 Windows 自带 OCR 的辅助脚本。
        - `tools/validate_generated_markdown.py`：上传前安全验证脚本。

        ## `convert_docx_to_markdown.py` 函数说明

        - `parse_args`：读取命令行参数，确定原稿目录、仓库目录、本地-only目录和 OCR 选项。
        - `read_docx_xml`：从 docx 压缩包中读取 XML 文件。
        - `parse_relationships`：读取 Word 关系文件，将图片 rId 映射到 `word/media` 内部路径。
        - `collect_run_text`：抽取 Word run 中的文字、制表符和换行。
        - `collect_image_rids`：抽取 DrawingML/VML 图片关系 ID。
        - `paragraph_segments`：把一个 Word 段落拆成顺序的文字片段和图片片段。
        - `iter_paragraphs`：按文档顺序遍历所有段落，包括表格中的段落。
        - `sanitize_filename`：把 Word 文件名转换成较短、稳定的 Markdown 文件名。
        - `sanitize_dirname`：把章节目录名转换成较短、稳定的目录名。
        - `markdown_link`：生成适合 Markdown 的 URL 编码链接。
        - `is_root_usage_doc`：判断是否为根目录使用说明。
        - `is_chapter40`：判断文档是否属于第40章。
        - `is_note_doc`：判断某个 docx 是否属于需要转换的笔记正文。
        - `discover_docx`：扫描本地 Word 原稿，得到待转换文档列表。
        - `output_path_for_doc`：根据上传规则计算 Markdown 输出路径，第40章输出到仓库外。
        - `extract_usage_text`：抽取 `使用说明.docx` 内容，用于生成 README。
        - `normalize_text`：统一换行和空白。
        - `clean_ocr_text`：清理 OCR 常见中文间隔空格。
        - `has_formula_risk`：判断 OCR 文本是否疑似包含数学公式、上下标、希腊字母或高密度符号，并触发人工公式校对标记。
        - `paragraph_to_markdown`：把 Word 段落保守转换为 Markdown 段落或标题。
        - `prepare_image_for_ocr`：把 Word 内嵌图片写入 OCR 临时目录，并对过大图片缩放。
        - `run_windows_ocr`：调用 PowerShell OCR 脚本并读取 OCR 结果。
        - `load_media_bytes`：从 docx 中读取待 OCR 的图片字节。
        - `extract_reference_lines`：自动检索正文中的引用线索。
        - `missing_reference_notes`：根据文件名、图片数量和引用线索生成待补引用提示。
        - `convert_single_doc`：转换单个 Word 文档，生成 Markdown 并返回统计记录。
        - `clean_outputs`：清理导出目录中的旧生成物，不接触 Word 原稿。
        - `build_directory_markdown`：生成完整上传目录。
        - `build_learning_path_markdown`：生成学习路径。
        - `build_readme`：生成 GitHub 首页。
        - `build_disclaimer`：生成免责声明。
        - `build_contributing`：生成贡献说明。
        - `build_license`：生成 CC BY-NC-SA 4.0 许可说明。
        - `build_gitignore`：生成上传安全忽略规则。
        - `build_citation`：生成 `CITATION.cff`。
        - `build_changelog`：生成初始更新记录。
        - `build_todo`：生成 OCR、引用和版权待办。
        - `build_ocr_report`：生成 OCR 质量报告。
        - `build_reference_report`：生成引用与版权清理报告。
        - `build_structure_doc`：生成本项目结构说明。
        - `write_project_files`：写入项目外壳和报告文件。
        - `main`：组织清理、扫描、转换、报告生成和进度输出。

        ## `winrt_ocr.ps1` 函数说明

        - `Await-WinRt`：把 WinRT 异步操作转换成可同步等待的 .NET Task。
        - `New-OcrEngine`：创建 Windows OCR 引擎，优先使用用户系统语言。
        - `Invoke-ImageOcr`：读取单张图片并返回 OCR 文字。

        ## `validate_generated_markdown.py` 函数说明

        - `main`：检查上传范围是否安全，包括是否误包含 Word、图片、中间文件、空 Markdown、乱码和断链。
        """
    )


def write_project_files(repo_root: Path, records: list[ConvertedDoc], usage_text: str) -> None:
    files = {
        "README.md": build_readme(records, usage_text),
        "LICENSE": build_license(),
        ".gitignore": build_gitignore(),
        "CONTRIBUTING.md": build_contributing(),
        "DISCLAIMER.md": build_disclaimer(),
        "CITATION.cff": build_citation(),
        "CHANGELOG.md": build_changelog(),
        "目录.md": build_directory_markdown(records),
        "学习路径.md": build_learning_path_markdown(),
        "TODO.md": build_todo(records),
        "OCR质量报告.md": build_ocr_report(records),
        "引用与版权清理报告.md": build_reference_report(records),
    }
    for relative, content in files.items():
        (repo_root / relative).write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_root = args.source_root.resolve()
    repo_root = args.repo_root.resolve()
    local_only_root = args.local_only_root.resolve()
    # OCR 临时图片放在仓库内部的 _ocr_tmp/，便于沙箱写入。
    # 该目录会被 .gitignore 忽略，并在转换成功后删除。
    temp_root = repo_root / "_ocr_tmp"

    if args.clean:
        clean_outputs(repo_root, local_only_root)
    temp_root.mkdir(parents=True, exist_ok=True)

    docs = discover_docx(source_root, args.only_sample, args.max_docs)
    if not docs:
        print("No DOCX note files found.", file=sys.stderr)
        return 1

    usage_text = extract_usage_text(source_root)
    records: list[ConvertedDoc] = []

    for index, docx_path in enumerate(docs, start=1):
        rel = docx_path.relative_to(source_root)
        print(f"[{index}/{len(docs)}] converting {rel}", flush=True)
        record = convert_single_doc(
            source_root=source_root,
            repo_root=repo_root,
            local_only_root=local_only_root,
            ocr_script=args.ocr_script,
            docx_path=docx_path,
            skip_ocr=not args.run_ocr,
            temp_root=temp_root,
        )
        records.append(record)

    write_project_files(repo_root, records, usage_text)
    if temp_root.exists():
        try:
            shutil.rmtree(temp_root)
        except PermissionError as exc:
            print(f"Warning: cannot remove OCR temp directory {temp_root}: {exc}", file=sys.stderr)
    print(f"Converted {len(records)} documents.", flush=True)
    print(f"Upload docs: {sum(1 for record in records if not record.local_only)}", flush=True)
    print(f"Local-only docs: {sum(1 for record in records if record.local_only)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
