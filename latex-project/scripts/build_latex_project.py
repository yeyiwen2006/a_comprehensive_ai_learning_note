from __future__ import annotations

import html
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "latex-project"
BUILD_DIR = PROJECT / "build"
COMBINED_MD = BUILD_DIR / "combined.md"
BODY_TEX = PROJECT / "body.tex"
MAIN_TEX = PROJECT / "main.tex"
IMAGE_DIR = PROJECT / "images"
CONTENT_TEX_DIR = PROJECT / "content"
MANIFEST = PROJECT / "RESOURCE_MANIFEST.md"
TYPO_REPORT = PROJECT / "TYPO_REPORT.md"

ROOT_MARKDOWN = [
    "README.md",
    "学习路径.md",
    "DISCLAIMER.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
]

ARCHIVED_ROOT_MARKDOWN = [
    "目录.md",
]

PART_TITLES = {
    "01-deep-learning": "第1部分 深度学习",
    "02-reinforcement-learning": "第2部分 强化学习",
    "03-large-language-model": "第3部分 大语言模型",
    "04-agents-and-continual-learning": "第4部分 大模型智能体与持续学习",
    "05-world-models-multimodal-embodied-ai": "第5部分 世界模型、多模态生成与具身智能",
}

TYPO_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("重复中文标点", re.compile(r"[，。！？；：、]{2,}")),
    ("重复英文标点", re.compile(r"(?<!\.)[!?;:]{2,}|,{2,}")),
    ("可能重复虚词", re.compile(r"(?:在在|的的|了了|是是|并并|和和|与与|将将|为为|对对|及及|或或|但但|而而|由由|把把|被被)")),
    ("可能重复术语", re.compile(r"(?:无法无法|可以可以|需要需要|如果如果|因此因此|因为因为|所以所以|进行进行|使用使用|通过通过|模型模型|数据数据|训练训练|生成生成|动作动作|状态状态)")),
    ("常见反向表达", re.compile(r"多数服从少数")),
    ("待办标记", re.compile(r"\b(?:TODO|FIXME|XXX)\b", re.IGNORECASE)),
    ("非普通空白", re.compile(r"[\t\u00a0]")),
]

MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HTML_IMAGE_RE = re.compile(
    r"<img\b(?=[^>]*\bsrc=[\"']([^\"']+)[\"'])(?=[^>]*\balt=[\"']([^\"']*)[\"'])[^>]*>",
    re.IGNORECASE,
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def remove_tree(path: Path) -> None:
    def on_error(function, item, _exc_info):
        os.chmod(item, 0o700)
        function(item)

    if path.exists():
        for item in path.rglob("*"):
            try:
                os.chmod(item, 0o700)
            except OSError:
                pass
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass
        shutil.rmtree(path, onerror=on_error)


def normalize_slashes(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def raw_latex(command: str) -> str:
    return f"```{{=latex}}\n{command}\n```"


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
    }
    return "".join(replacements.get(char, char) for char in text)


def part_heading(title: str) -> str:
    escaped = latex_escape(title)
    return raw_latex(rf"\part*{{{escaped}}}" + "\n" + rf"\addcontentsline{{toc}}{{part}}{{{escaped}}}")


def split_front_matter(text: str) -> tuple[list[str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], text

    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], "\n".join(lines[index + 1 :]).lstrip("\n")
    return [], text


def parse_front_matter(lines: list[str]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in lines:
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        rows.append((key.strip(), value))
    return rows


def metadata_table(front_matter: list[str]) -> str:
    rows = parse_front_matter(front_matter)
    if not rows:
        return ""

    table = ["", "| 原始元数据字段 | 原始值 |", "|---|---|"]
    for key, value in rows:
        safe_value = value.replace("|", r"\|")
        table.append(f"| `{key}` | {safe_value} |")
    table.append("")
    return "\n".join(table)


def strip_leading_number(title: str) -> str:
    title = title.strip()
    title = re.sub(r"^\d+(?:\.\d+)*\s+", "", title)
    title = re.sub(r"^\d+[-_]", "", title)
    return title.strip()


def front_matter_title(front_matter: list[str], fallback: str) -> str:
    for key, value in parse_front_matter(front_matter):
        if key == "title" and value.strip():
            return value.strip()
    return fallback


def first_heading_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def shift_markdown_headings(text: str, amount: int = 1) -> str:
    shifted: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            shifted.append(line)
            continue
        if not in_fence:
            match = re.match(r"^(#{1,6})(\s+.*)$", line)
            if match:
                level = min(6, len(match.group(1)) + amount)
                shifted.append("#" * level + match.group(2))
                continue
        shifted.append(line)
    return "\n".join(shifted)


def section_markdown(body: str, front_matter: list[str], fallback_title: str) -> str:
    lines = body.splitlines()
    h1_index = next((index for index, line in enumerate(lines) if line.startswith("# ")), None)
    title = front_matter_title(front_matter, fallback_title)
    if h1_index is not None:
        title = first_heading_title(body, title)
        remainder = "\n".join(lines[h1_index + 1 :]).lstrip("\n")
    else:
        remainder = body

    chunks = [f"## {strip_leading_number(title)}"]
    if remainder.strip():
        chunks.append(shift_markdown_headings(remainder.strip(), amount=1))
    return "\n\n".join(chunks)


def insert_metadata_after_h1(body: str, front_matter: list[str], fallback_title: str) -> str:
    meta = metadata_table(front_matter)
    if not meta:
        return body if body.strip() else f"# {fallback_title}\n"

    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# "):
            return "\n".join(lines[: index + 1] + [meta] + lines[index + 1 :])

    return f"# {fallback_title}\n{meta}\n{body}"


def resolve_resource(markdown_file: Path, target: str) -> Path | None:
    raw_target = target.strip()
    if raw_target.startswith(("http://", "https://", "mailto:")):
        return None
    if " " in raw_target and raw_target.count('"') >= 2:
        raw_target = raw_target.split(" ", 1)[0]
    raw_target = raw_target.strip("<>")
    decoded = urllib.parse.unquote(raw_target)
    candidate = (markdown_file.parent / decoded).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        return None
    return candidate if candidate.exists() else None


class ImageRegistry:
    def __init__(self) -> None:
        self.by_source: dict[Path, str] = {}
        self.rows: list[tuple[str, str]] = []

    def register(self, source: Path) -> str:
        source = source.resolve()
        if source in self.by_source:
            return self.by_source[source]

        image_number = len(self.by_source) + 1
        target_suffix = ".png" if source.suffix.lower() == ".webp" else source.suffix.lower()
        target_name = f"image-{image_number:04d}{target_suffix}"
        target = IMAGE_DIR / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".webp":
            from PIL import Image

            with Image.open(source) as image:
                image.save(target, "PNG")
        else:
            shutil.copy2(source, target)

        relative = normalize_slashes(Path("images") / target_name)
        self.by_source[source] = relative
        self.rows.append((normalize_slashes(source.relative_to(ROOT)), relative))
        return relative


def rewrite_images(text: str, markdown_file: Path, registry: ImageRegistry) -> str:
    def replace_markdown(match: re.Match[str]) -> str:
        alt, target = match.group(1), match.group(2)
        source = resolve_resource(markdown_file, target)
        if source is None:
            return match.group(0)
        return f"![{alt}]({registry.register(source)})"

    def replace_html(match: re.Match[str]) -> str:
        src, alt = match.group(1), html.unescape(match.group(2))
        source = resolve_resource(markdown_file, src)
        if source is None:
            return match.group(0)
        return f"![{alt}]({registry.register(source)})"

    text = HTML_IMAGE_RE.sub(replace_html, text)
    return MARKDOWN_IMAGE_RE.sub(replace_markdown, text)


def normalize_markdown_for_latex(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        line = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", line)
        if re.match(r"^\s*(`{3,}|~{3,})", line):
            in_fence = not in_fence
            lines.append(line)
            continue
        if in_fence:
            lines.append(line)
            continue

        line = re.sub(r"^(\s{0,3}[-*])(?=[A-Za-z\u4e00-\u9fff`$])", r"\1 ", line)
        line = re.sub(r"^(\s{0,3}\d+[.)])(?=[^\s\d)])", r"\1 ", line)
        lines.append(line)
    return "\n".join(lines)


def docs_markdown_files() -> list[Path]:
    return sorted((ROOT / "docs").rglob("*.md"), key=lambda p: normalize_slashes(p.relative_to(ROOT)))


def copy_source_markdown(files: list[Path]) -> None:
    for path in files:
        target = PROJECT / "source-markdown" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def copy_assets() -> None:
    shutil.copytree(ROOT / "assets", PROJECT / "assets", dirs_exist_ok=True)


def build_combined_markdown(registry: ImageRegistry) -> list[Path]:
    included: list[Path] = []
    chunks: list[str] = [
        raw_latex(
            r"\setcounter{secnumdepth}{-1}"
            + "\n"
            + r"\setcounter{tocdepth}{0}"
            + "\n"
            + r"\addtocontents{toc}{\protect\setcounter{tocdepth}{0}}"
        ),
        "",
    ]

    for name in ARCHIVED_ROOT_MARKDOWN:
        path = ROOT / name
        if path.exists():
            included.append(path)

    for name in ROOT_MARKDOWN:
        path = ROOT / name
        if not path.exists():
            continue
        included.append(path)
        text = rewrite_images(read_text(path), path, registry).strip()
        text = normalize_markdown_for_latex(text).strip()
        chunks.extend([text, "", raw_latex(r"\clearpage"), ""])

    chunks.extend(
        [
            raw_latex(
                r"\mainmatter"
                + "\n"
                + r"\setcounter{secnumdepth}{1}"
                + "\n"
                + r"\setcounter{tocdepth}{1}"
                + "\n"
                + r"\addtocontents{toc}{\protect\setcounter{tocdepth}{1}}"
            ),
            "",
        ]
    )

    current_part = ""
    current_chapter = ""
    for path in docs_markdown_files():
        included.append(path)
        relative = path.relative_to(ROOT)
        part_key = relative.parts[1]
        part_title = PART_TITLES.get(part_key, part_key)
        if part_title != current_part:
            current_part = part_title
            current_chapter = ""
            chunks.extend([part_heading(part_title), ""])

        chapter_key = relative.parts[2] if len(relative.parts) > 3 else path.parent.name
        chapter_title = strip_leading_number(chapter_key)
        if chapter_key != current_chapter:
            current_chapter = chapter_key
            chunks.extend([f"# {chapter_title}", ""])

        text = read_text(path)
        front_matter, body = split_front_matter(text)
        body = rewrite_images(body, path, registry).strip()
        body = section_markdown(body, front_matter, path.stem)
        body = normalize_markdown_for_latex(body).strip()
        chunks.extend([body, "", raw_latex(r"\clearpage"), ""])

    write_text(COMBINED_MD, "\n".join(chunks).rstrip() + "\n")
    return included


def write_manifest(included_files: list[Path], registry: ImageRegistry) -> None:
    lines = [
        "# LaTeX 项目资源清单",
        "",
        f"- 已纳入根目录 Markdown：{len([p for p in included_files if p.parent == ROOT])}",
        f"- 已纳入 docs Markdown：{len([p for p in included_files if 'docs' in p.relative_to(ROOT).parts])}",
        f"- 原始 assets 文件：{len(list((ROOT / 'assets').rglob('*.*')))}",
        f"- 已转换图片引用：{len(registry.rows)}",
        "",
        "## 图片引用映射",
        "",
        "| 原始资源 | LaTeX 编译引用 |",
        "|---|---|",
    ]
    for source, target in registry.rows:
        lines.append(f"| `{source}` | `{target}` |")
    write_text(MANIFEST, "\n".join(lines) + "\n")


def escape_markdown_cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", r"\|").replace("\n", " ")


def display_match(text: str) -> str:
    replacements = {
        "\t": "U+0009(TAB)",
        "\u00a0": "U+00A0(NBSP)",
    }
    return "".join(replacements.get(char, char) for char in text)


def compact_context(line: str, start: int, end: int, radius: int = 42) -> str:
    left = max(0, start - radius)
    right = min(len(line), end + radius)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(line) else ""
    return prefix + line[left:start] + "【" + line[start:end] + "】" + line[end:right] + suffix


def scan_typo_candidates(files: list[Path]) -> list[tuple[str, int, str, str, str]]:
    findings: list[tuple[str, int, str, str, str]] = []
    seen: set[tuple[str, int, str, str]] = set()

    for path in files:
        in_fence = False
        relative = normalize_slashes(path.relative_to(ROOT))
        for line_number, line in enumerate(read_text(path).splitlines(), start=1):
            if re.match(r"^\s*(```|~~~)", line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for rule_name, pattern in TYPO_PATTERNS:
                for match in pattern.finditer(line):
                    key = (relative, line_number, rule_name, match.group(0))
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(
                        (
                            relative,
                            line_number,
                            rule_name,
                            match.group(0),
                            compact_context(line, match.start(), match.end()),
                        )
                    )
    return findings


def write_typo_report(included_files: list[Path]) -> None:
    findings = scan_typo_candidates(included_files)
    rule_order = {name: index for index, (name, _pattern) in enumerate(TYPO_PATTERNS)}
    findings.sort(key=lambda item: (rule_order.get(item[2], 999), item[0], item[1], item[3]))

    counts: dict[str, int] = {}
    for _relative, _line_number, rule_name, _match_text, _context in findings:
        counts[rule_name] = counts.get(rule_name, 0) + 1

    lines = [
        "# 正则 typo 疑似项报告",
        "",
        "本报告只用正则规则标记疑似问题，不直接改动原文。请人工确认后再决定是否修订源 Markdown。",
        "",
        f"- 扫描 Markdown 文件：{len(included_files)}",
        f"- 疑似项数量：{len(findings)}",
        "",
    ]

    if not findings:
        lines.append("未发现当前规则覆盖的疑似 typo。")
        write_text(TYPO_REPORT, "\n".join(lines) + "\n")
        return

    lines.extend(["## 规则统计", ""])
    for rule_name, _pattern in TYPO_PATTERNS:
        if rule_name in counts:
            lines.append(f"- {rule_name}：{counts[rule_name]}")
    lines.extend(["", "## 明细", ""])

    lines.extend(["| 文件 | 行 | 规则 | 匹配 | 上下文 |", "|---|---:|---|---|---|"])
    for relative, line_number, rule_name, match_text, context in findings:
        lines.append(
            "| "
            + escape_markdown_cell(relative)
            + f" | {line_number} | "
            + escape_markdown_cell(rule_name)
            + " | `"
            + escape_markdown_cell(display_match(match_text))
            + "` | "
            + escape_markdown_cell(context)
            + " |"
        )
    write_text(TYPO_REPORT, "\n".join(lines) + "\n")


def write_project_readme() -> None:
    write_text(
        PROJECT / "README.md",
        """# A Comprehensive AI Learning Note LaTeX Project

这是从仓库 Markdown 文档整理得到的 LaTeX 项目。正文入口为 `main.tex`，正文索引由 `body.tex` 承载，具体内容拆分在 `content/` 下，`images/` 保存为了稳定编译而生成的图片引用副本。

本项目只做排版转换，不改写原文档内容。

## Build

```powershell
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
```
""",
    )


def write_main_tex() -> None:
    write_text(
        MAIN_TEX,
        r"""\documentclass[11pt,openany,oneside]{ctexbook}

\usepackage[a4paper,margin=2.4cm]{geometry}
\usepackage{amsmath,amssymb,mathtools,bm}
\usepackage{graphicx}
\usepackage[export]{adjustbox}
\usepackage{longtable,booktabs,array}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{xurl}
\usepackage{hyperref}
\usepackage{bookmark}
\usepackage{caption}
\usepackage{fancyhdr}
\usepackage{microtype}
\usepackage{fancyvrb}
\usepackage{fvextra}
\usepackage{upquote}
\usepackage{etoolbox}
\usepackage{newunicodechar}

\setmainfont{Times New Roman}
\setsansfont{Arial}
\setmonofont{Consolas}
\IfFontExistsTF{SimSun}{%
  \IfFontExistsTF{SimHei}{%
    \IfFontExistsTF{KaiTi}{%
      \setCJKmainfont[BoldFont=SimHei,ItalicFont=KaiTi]{SimSun}%
    }{%
      \setCJKmainfont[BoldFont=SimHei]{SimSun}%
    }%
  }{%
    \setCJKmainfont{SimSun}%
  }%
}{}
\IfFontExistsTF{Microsoft YaHei}{\setCJKsansfont{Microsoft YaHei}}{}
\newfontfamily\mathcjkfont{SimSun}

\graphicspath{{./}{images/}}
\setkeys{Gin}{max width=\linewidth,max height=0.46\textheight,keepaspectratio}
\makeatletter
\let\latexproject@origincludegraphics\includegraphics
\renewcommand{\includegraphics}[2][]{%
  \adjustbox{max width=\linewidth,max height=0.46\textheight,center}{%
    \latexproject@origincludegraphics[#1]{#2}%
  }%
}
\makeatother

\definecolor{latexprojectBlue}{HTML}{1F4E79}
\definecolor{latexprojectGray}{HTML}{555555}

\hypersetup{
  unicode=true,
  bookmarksnumbered=true,
  bookmarksopen=true,
  bookmarksopenlevel=1,
  colorlinks=true,
  linkcolor=latexprojectBlue,
  urlcolor=latexprojectBlue,
  citecolor=latexprojectBlue,
  pdftitle={A Comprehensive AI Learning Note},
  pdfauthor={叶逸文}
}

\linespread{1.16}
\raggedbottom
\setlength{\parindent}{2em}
\setlength{\parskip}{0.08em}
\setlength{\emergencystretch}{4em}
\setlength{\intextsep}{0.7em}
\setlength{\textfloatsep}{0.8em}
\setlength{\floatsep}{0.8em}
\setlength{\headheight}{14pt}
\setlength{\LTpre}{0.35em}
\setlength{\LTpost}{0.35em}
\setlength{\tabcolsep}{4.5pt}
\setlength{\abovedisplayskip}{0.65em}
\setlength{\belowdisplayskip}{0.65em}
\setlength{\abovedisplayshortskip}{0.45em}
\setlength{\belowdisplayshortskip}{0.45em}
\renewcommand{\arraystretch}{1.14}
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000
\allowdisplaybreaks[2]
\sloppy
\setcounter{tocdepth}{1}
\setcounter{secnumdepth}{1}
\setlist{leftmargin=2.2em, labelsep=0.5em, itemsep=0.12em, topsep=0.28em, parsep=0.04em}
\captionsetup{font=small,labelfont=bf,skip=0.35em}
\Urlmuskip=0mu plus 2mu\relax
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small\nouppercase{\leftmark}}
\fancyhead[R]{\small\thepage}
\renewcommand{\headrulewidth}{0.35pt}
\renewcommand{\chaptermark}[1]{\markboth{#1}{}}
\fancypagestyle{plain}{%
  \fancyhf{}%
  \fancyfoot[C]{\small\thepage}%
  \renewcommand{\headrulewidth}{0pt}%
}
\ctexset{
  part = {
    format = \centering\Huge\bfseries\color{latexprojectBlue},
    beforeskip = 0pt,
    afterskip = 2.2em
  },
  chapter = {
    format = \centering\LARGE\bfseries\color{latexprojectBlue},
    beforeskip = 1.05em,
    afterskip = 0.85em,
    name = {第,章},
    number = \arabic{chapter},
    aftername = \quad
  },
  section = {
    format = \Large\bfseries\color{latexprojectBlue!88!black},
    beforeskip = 0.9em,
    afterskip = 0.4em,
    aftername = \quad
  },
  subsection = {
    format = \normalsize\bfseries\color{latexprojectGray},
    beforeskip = 0.7em,
    afterskip = 0.25em,
    numbering = false
  },
  subsubsection = {
    format = \normalsize\bfseries,
    beforeskip = 0.5em,
    afterskip = 0.2em,
    numbering = false
  }
}

\AtBeginEnvironment{longtable}{\small}
\AtBeginEnvironment{quote}{\small\color{latexprojectGray}}
\RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines,breakanywhere,fontsize=\footnotesize,frame=leftline,framerule=0.8pt,framesep=2mm,rulecolor=\color{latexprojectBlue!45}}
\DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,breakanywhere,fontsize=\footnotesize,frame=leftline,framerule=0.8pt,framesep=2mm,rulecolor=\color{latexprojectBlue!45},commandchars=\\\{\}}
\newenvironment{Shaded}{}{}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\passthrough}[1]{#1}
\providecommand{\pandocbounded}[1]{#1}
\providecommand{\n}{\textbackslash n}
\providecommand{\lt}{<}
\providecommand{\gt}{>}
\newcommand{\mathcjk}[1]{\mbox{{\mathcjkfont #1}}}
\newunicodechar{∈}{\ensuremath{\in}}

\title{A Comprehensive AI Learning Note}
\author{叶逸文}
\date{2026年5月10日}

\begin{document}
\makeatletter
\begin{titlepage}
\centering
\vspace*{0.18\textheight}
{\Huge\bfseries\color{latexprojectBlue}\@title\par}
\vspace{2.2em}
{\Large\@author\par}
\vfill
{\large\@date\par}
\end{titlepage}
\makeatother
\frontmatter
\phantomsection
\pdfbookmark[0]{目录}{toc}
\tableofcontents
\input{body.tex}
\end{document}
""",
    )


def run_pandoc() -> None:
    command = [
        "pandoc",
        str(COMBINED_MD),
        "--from",
        "markdown+tex_math_dollars+raw_attribute+pipe_tables+fenced_code_blocks",
        "--to",
        "latex",
        "--top-level-division=chapter",
        "--wrap=preserve",
        "--no-highlight",
        "--resource-path",
        str(PROJECT),
        "-o",
        str(BODY_TEX),
    ]
    subprocess.run(command, cwd=PROJECT, check=True)
    patch_body_tex()


def patch_body_tex() -> None:
    text = read_text(BODY_TEX)
    cjk_text_pattern = re.compile(r"\\text\{([^{}]*[\u4e00-\u9fff][^{}]*)\}")
    text = cjk_text_pattern.sub(r"\\mathcjk{\1}", text)
    cjk_mbox_pattern = re.compile(r"\\mbox\{([^{}]*[\u4e00-\u9fff][^{}]*)\}")
    text = cjk_mbox_pattern.sub(r"\\mathcjk{\1}", text)
    text = wrap_cjk_inside_math(text)
    text = text.replace("\\begin{figure}\n", "\\begin{figure}[htbp]\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    write_text(BODY_TEX, text)
    split_body_tex()


def split_body_tex() -> None:
    text = read_text(BODY_TEX)
    remove_tree(CONTENT_TEX_DIR)

    boundary = re.compile(
        r"(?m)^(?=\\mainmatter$|\\part\*\{|\\hypertarget\{[^}]+\}\{%\n\\chapter\{)"
    )
    starts = [match.start() for match in boundary.finditer(text)]
    if 0 not in starts:
        starts.insert(0, 0)
    starts = sorted(set(starts))

    chunks = [text[starts[index] : starts[index + 1] if index + 1 < len(starts) else len(text)] for index in range(len(starts))]
    inputs: list[tuple[str, str]] = []
    front_index = 1
    chapter_index = 1
    part_index = 1
    in_mainmatter = False

    for chunk in chunks:
        if not chunk.strip():
            continue

        chapter_match = re.search(r"\\chapter\{([^{}]+)\}", chunk)
        part_match = re.search(r"\\part\*\{([^{}]+)\}", chunk)

        if chunk.lstrip().startswith(r"\mainmatter"):
            relative = Path("content") / "mainmatter" / "000-mainmatter-setup.tex"
            title = "mainmatter setup"
            in_mainmatter = True
        elif part_match:
            relative = Path("content") / "mainmatter" / f"part-{part_index:02d}.tex"
            title = part_match.group(1)
            part_index += 1
            in_mainmatter = True
        elif chapter_match and in_mainmatter:
            relative = Path("content") / "mainmatter" / f"chapter-{chapter_index:03d}.tex"
            title = chapter_match.group(1)
            chapter_index += 1
        elif chapter_match:
            relative = Path("content") / "frontmatter" / f"{front_index:03d}.tex"
            title = chapter_match.group(1)
            front_index += 1
        else:
            relative = Path("content") / "frontmatter" / "000-frontmatter-setup.tex"
            title = "frontmatter setup"

        target = PROJECT / relative
        write_text(target, chunk.strip() + "\n")
        inputs.append((normalize_slashes(relative), title))

    body_lines = [
        "% Auto-generated content index. Do not edit by hand.",
        "% Actual document content is split under latex-project/content/.",
        "",
    ]
    for relative, title in inputs:
        body_lines.append(f"% {title}")
        body_lines.append(rf"\input{{{relative}}}")
        body_lines.append("")
    write_text(BODY_TEX, "\n".join(body_lines).rstrip() + "\n")


def wrap_cjk_inside_math(text: str) -> str:
    cjk_run = re.compile(r"[\u4e00-\u9fff]+")

    def wrap_runs(content: str) -> str:
        result: list[str] = []
        last = 0
        for match in cjk_run.finditer(content):
            result.append(content[last : match.start()])
            previous = content[match.start() - 1] if match.start() > 0 else ""
            if previous == "{":
                result.append(match.group(0))
            else:
                result.append(rf"\mathcjk{{{match.group(0)}}}")
            last = match.end()
        result.append(content[last:])
        return "".join(result)

    text = re.sub(r"\\\((.*?)\\\)", lambda m: r"\(" + wrap_runs(m.group(1)) + r"\)", text)
    return re.sub(r"\\\[(.*?)\\\]", lambda m: r"\[" + wrap_runs(m.group(1)) + r"\]", text, flags=re.S)


def compact_context(line: str, start: int, end: int, radius: int = 42) -> str:
    left = max(0, start - radius)
    right = min(len(line), end + radius)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(line) else ""
    return prefix + line[left:start] + "【" + line[start:end] + "】" + line[end:right] + suffix


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def strip_inline_code(text: str) -> str:
    chars = list(text)
    for match in re.finditer(r"`+[^`]*?`+", text):
        for index in range(match.start(), match.end()):
            chars[index] = " "
    return "".join(chars)


def unescaped_positions(text: str, token: str) -> list[int]:
    positions: list[int] = []
    start = 0
    while True:
        index = text.find(token, start)
        if index < 0:
            return positions
        if not is_escaped(text, index):
            positions.append(index)
        start = index + len(token)


def find_closing(text: str, start: int, closing: str) -> int:
    index = start
    while index < len(text):
        if text[index] == closing and not is_escaped(text, index):
            return index
        index += 1
    return -1


def split_unescaped_pipes(line: str) -> list[str]:
    cells: list[str] = []
    start = 0
    for index, char in enumerate(line):
        if char == "|" and not is_escaped(line, index):
            cells.append(line[start:index])
            start = index + 1
    cells.append(line[start:])
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return cells


def markdown_syntax_findings(files: list[Path]) -> list[tuple[str, int, str, str, str]]:
    findings: list[tuple[str, int, str, str, str]] = []
    seen: set[tuple[str, int, str, str]] = set()

    def add(path: Path, line_number: int, rule: str, evidence: str, line: str, start: int = 0) -> None:
        relative = normalize_slashes(path.relative_to(ROOT))
        key = (relative, line_number, rule, evidence)
        if key in seen:
            return
        seen.add(key)
        end = min(len(line), start + max(1, len(evidence)))
        findings.append((relative, line_number, rule, evidence, compact_context(line, start, end)))

    table_separator = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")

    for path in files:
        lines = read_text(path).splitlines()
        yaml_line = [False] * len(lines)
        if lines and lines[0].strip() == "---":
            yaml_line[0] = True
            for yaml_index in range(1, len(lines)):
                yaml_line[yaml_index] = True
                if lines[yaml_index].strip() == "---":
                    break

        in_fence = False
        fence_marker = ""
        fence_start = 0
        display_math_start = 0
        in_display_math = False
        code_line = [False] * len(lines)

        for index, line in enumerate(lines, start=1):
            if yaml_line[index - 1]:
                continue

            fence_match = re.match(r"^\s*(`{3,}|~{3,})", line)
            if fence_match:
                marker = fence_match.group(1)
                if not in_fence:
                    in_fence = True
                    fence_marker = marker[0]
                    fence_start = index
                elif marker.startswith(fence_marker * 3):
                    in_fence = False
                    fence_marker = ""
                code_line[index - 1] = True
                continue

            if in_fence:
                code_line[index - 1] = True
                continue

            for control_match in re.finditer(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", line):
                add(path, index, "不可见控制字符", f"U+{ord(control_match.group(0)):04X}", line, control_match.start())

            visible = strip_inline_code(line)

            if re.match(r"^\s*#{1,6}(?!#)\S", visible):
                add(path, index, "标题缺少空格", "#", line, visible.find("#"))

            list_marker = re.match(r"^(\s*[-*])(?![-*])(?=[A-Za-z\u4e00-\u9fff])", visible)
            if list_marker:
                add(path, index, "列表标记后缺少空格", list_marker.group(1), line, list_marker.start(1))

            ordered_marker = re.match(r"^(\s*\d+[.)])\S", visible)
            if ordered_marker:
                add(path, index, "有序列表标记后缺少空格", ordered_marker.group(1), line, ordered_marker.start(1))

            code_runs: dict[int, int] = {}
            for match in re.finditer(r"(?<!\\)`+", line):
                code_runs[len(match.group(0))] = code_runs.get(len(match.group(0)), 0) + 1
            for run_length, count in code_runs.items():
                if count % 2 == 1:
                    evidence = "`" * run_length
                    add(path, index, "行内代码反引号未配对", evidence, line, line.find(evidence))
                    break

            double_dollars = unescaped_positions(visible, "$$")
            if len(double_dollars) % 2 == 1:
                if in_display_math:
                    in_display_math = False
                else:
                    in_display_math = True
                    display_math_start = index

            single_dollar_positions: list[int] = []
            cursor = 0
            while cursor < len(visible):
                if visible[cursor] == "$" and not is_escaped(visible, cursor):
                    previous_is_dollar = cursor > 0 and visible[cursor - 1] == "$"
                    next_is_dollar = cursor + 1 < len(visible) and visible[cursor + 1] == "$"
                    if not previous_is_dollar and not next_is_dollar:
                        single_dollar_positions.append(cursor)
                cursor += 1
            if len(single_dollar_positions) % 2 == 1:
                add(path, index, "行内数学美元符未配对", "$", line, single_dollar_positions[0])

            for match in re.finditer(r"!\[|\[", visible):
                start = match.start()
                if is_escaped(visible, start):
                    continue
                is_image = visible.startswith("![", start)
                close = find_closing(visible, start + 1, "]")
                if close < 0:
                    if is_image:
                        add(path, index, "图片方括号未闭合", "![", line, start)
                    continue
                if close + 1 < len(visible) and visible[close + 1] == "(":
                    target_close = find_closing(visible, close + 2, ")")
                    if target_close < 0:
                        add(path, index, "链接或图片圆括号未闭合", "](", line, close)

        if in_fence:
            add(path, fence_start, "代码块围栏未闭合", fence_marker * 3, lines[fence_start - 1], 0)
        if in_display_math:
            add(path, display_math_start, "展示数学块美元符未闭合", "$$", lines[display_math_start - 1], 0)

        for index, line in enumerate(lines, start=1):
            if yaml_line[index - 1] or code_line[index - 1] or not table_separator.match(line):
                continue
            if index <= 1:
                add(path, index, "表格分隔行缺少表头", line.strip(), line, 0)
                continue
            expected = len(split_unescaped_pipes(lines[index - 2]))
            actual = len(split_unescaped_pipes(line))
            if expected != actual:
                add(path, index, "表格分隔行列数不一致", f"{actual}/{expected}", line, 0)
            cursor = index + 1
            while cursor <= len(lines):
                row = lines[cursor - 1]
                if code_line[cursor - 1] or not row.strip() or "|" not in row:
                    break
                if table_separator.match(row):
                    cursor += 1
                    continue
                cells = len(split_unescaped_pipes(row))
                if cells != expected:
                    add(path, cursor, "表格正文列数不一致", f"{cells}/{expected}", row, 0)
                cursor += 1

    findings.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return findings


def write_typo_report(included_files: list[Path]) -> None:
    findings = markdown_syntax_findings(included_files)
    counts: dict[str, int] = {}
    for _relative, _line_number, rule_name, _match_text, _context in findings:
        counts[rule_name] = counts.get(rule_name, 0) + 1

    lines = [
        "# Markdown 语法体检报告",
        "",
        "本报告只检查 Markdown 结构和配对类问题，不改动源文档。条目为正则与轻量解析的疑似结果，建议人工确认后再修改源 Markdown。",
        "",
        f"- 扫描 Markdown 文件：{len(included_files)}",
        f"- 疑似语法问题：{len(findings)}",
        "",
    ]

    if not findings:
        lines.append("未发现当前规则覆盖的 Markdown 语法疑似问题。")
        write_text(TYPO_REPORT, "\n".join(lines) + "\n")
        return

    lines.extend(["## 规则统计", ""])
    for rule_name in sorted(counts):
        lines.append(f"- {rule_name}：{counts[rule_name]}")
    lines.extend(["", "## 明细", ""])

    lines.extend(["| 文件 | 行 | 规则 | 证据 | 上下文 |", "|---|---:|---|---|---|"])
    for relative, line_number, rule_name, match_text, context in findings:
        lines.append(
            "| "
            + escape_markdown_cell(relative)
            + f" | {line_number} | "
            + escape_markdown_cell(rule_name)
            + " | `"
            + escape_markdown_cell(display_match(match_text))
            + "` | "
            + escape_markdown_cell(context)
            + " |"
        )
    write_text(TYPO_REPORT, "\n".join(lines) + "\n")


def main() -> int:
    PROJECT.mkdir(parents=True, exist_ok=True)
    remove_tree(IMAGE_DIR)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    registry = ImageRegistry()

    included = build_combined_markdown(registry)
    write_manifest(included, registry)
    write_typo_report(included)
    write_project_readme()
    write_main_tex()
    run_pandoc()
    return 0


if __name__ == "__main__":
    sys.exit(main())
