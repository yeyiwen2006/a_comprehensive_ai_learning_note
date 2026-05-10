# A Comprehensive AI Learning Note LaTeX Project

这是从仓库 Markdown 文档整理得到的 LaTeX 项目。正文入口为 `main.tex`，正文索引由 `body.tex` 承载，具体内容拆分在 `content/` 下，`images/` 保存为了稳定编译而生成的图片引用副本。

本项目只做排版转换，不改写原文档内容。

## Build

```powershell
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
```
