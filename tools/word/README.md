# 纯标准库 Word (.docx) 报告生成器

用于中文工程研究报告的 `.docx` 生成器，**只用 Python 标准库**（`zipfile` + 字符串/XML 模板 + `xml.sax.saxutils`），
不依赖 `python-docx` 或任何第三方包。输出的 OOXML 手工拼装，可直接用 Word 2016+ 打开，**不出现"修复"提示**。

```
tools/word/
├── omml.py          LaTeX 子集 -> OMML（Office Math Markup Language）转换器
├── report_docx.py   class Report  +  演示（python report_docx.py）
├── selftest.py      自检：生成 selftest.docx / selftest_edge.docx 并做全部校验
└── README.md        本文档
```

环境：Windows；Python 3.8 及以上，命令行以 `python` 调用即可（本工程在 Python 3.14 下验证通过）。

---

## 1. 快速开始

```python
from report_docx import Report

r = Report(title="报告标题", subtitle="副标题", author="作者", date="2026年9月",
           ascii_font="Times New Roman", east_font="宋体", heading_east_font="黑体",
           accent="1F4E79")

r.cover()                       # 封面：标题/副标题/作者/日期，末尾自动分页
r.toc()                         # 真正的 TOC 域（TOC \o "1-3" \h \z \u），打开时自动更新

r.h1("1 引言")                   # 标题层级由调用方自行编号
r.h2("1.1 背景")
r.h3("1.1.1 细节")

r.p("正文段落，行内公式写作 $\\alpha + \\beta$，自动转 OMML。", first_indent=True)
r.p("不需要首行缩进的段落", first_indent=False, align="left")

r.bullet("要点一")
r.bullet("子要点", level=1)
r.num("第一条")

r.eq(r"\dot{V} = \frac{T\cos\alpha - D}{m} - g\sin\gamma", number="(1)")

r.table(headers=["列1", "列2"], rows=[["a", "b"], ["c", "d"]],
        caption="表 1-1 参数表", widths=[6.0, 6.0], font_size=10.5,
        aligns=["center", "center"])

r.figure("path/to/fig.png", caption="图 1-1 仿真结果", width_cm=14.0)
r.caption("图 1-2 xxxx")        # 独立题注
r.note("小字注释")
r.pagebreak()
r.save("out.docx")
```

运行演示：`python report_docx.py` → 生成 `report_demo.docx`（及 `report_demo_fig.png`）。

---

## 2. API

### 2.1 `class Report`

```python
Report(title="", subtitle="", author="", date="",
       ascii_font="Times New Roman", east_font="宋体",
       heading_east_font="黑体", accent="1F4E79",
       body_size_pt=12.0, line_spacing=1.5, math_font="Cambria Math")
```

| 成员 | 说明 |
|---|---|
| `accent` | h1/h2 与封面标题的颜色，接受 `"1F4E79"` 或 `"#1F4E79"` |
| `body_size_pt` | 正文字号，默认 12 pt（小四） |
| `line_spacing` | 行距倍数，默认 1.5 → `w:line="360"` |
| `math_font` | 写入 `settings.xml` 的 `m:mathFont`，默认 `Cambria Math` |
| `text_width_cm` | 可用正文宽度 = 15.397 cm（8730 twips），只读 |
| `warnings` | `list[str]`，记录表格超宽被缩放、图片超宽被裁剪等 |
| `parts()` | 返回全部 OPC 部件 `(part_name, bytes\|str)` 列表 |
| `save(path)` | 写出 `.docx`，返回绝对路径；父目录不存在时自动创建 |

内容方法（按文档顺序调用即可）：

| 方法 | 说明 |
|---|---|
| `cover()` | 封面（4 空行 / 标题 26 pt 加粗 accent 色 / 副标题 16 pt 灰 / 6 空行 / 作者 14 pt / 日期 14 pt），末尾插入分页 |
| `toc(title="目录", *, page_break_after=False)` | `目 录` 标题 + TOC 域。`title=None` 可去掉标题行 |
| `h1(text, page_break_before=False)` | 一级标题，`w:pStyle="Heading1"`，16 pt，`outlineLvl=0` |
| `h2(...)` / `h3(...)` | 14 pt / 12.5 pt，`outlineLvl` 1 / 2 |
| `p(text, first_indent=True, align=None, *, size_pt=None, bold=False)` | 正文段落；`$...$` 转行内 `<m:oMath>`；`align` 默认 `"both"`（两端对齐） |
| `bullet(text, level=0)` | 项目符号列表（`numId=1`，0–3 级） |
| `num(text, level=0)` | 编号列表；**连续调用为一组**，组内自动编号，其他块打断后重新从 1 开始 |
| `eq(latex, number=None, *, layout="table")` | 显示公式；`number` 给出时用无边框 1×2 表格（左格居中公式、右格右对齐编号）；`layout="tabs"` 改用制表位方案 |
| `table(headers, rows, caption=None, widths=None, font_size=10.5, aligns=None, header_shade="D9E2F3", header_bold=True, first_col_align=None)` | 三线全框表格；**题注在表格上方**；`headers=None` 表示无表头 |
| `figure(path, caption=None, width_cm=14.0, *, keep_next=True)` | 居中插图，**题注在图下方**；像素尺寸由文件头解析，高度按宽高比推算 |
| `caption(text, *, keep_next=False, size_pt=None)` | 独立题注（居中、10.5 pt、不加粗、`Caption` 样式） |
| `note(text, *, align="left", size_pt=None)` | 小字注释，默认 9 pt |
| `pagebreak()` | 插入分页符 |

`table()` 细节：

* `widths` 单位为 **cm**；`None` 时按可用宽度均分。若总和超过正文宽度，按比例缩小并写入 `r.warnings`。
* `aligns` 为每列的 `"left" | "center" | "right"`，同时作用于表头行与数据行；`first_col_align` 可单独覆盖第 0 列。
* 行数/列数任意；`rows` 中每行长度不足自动补空，超出自动截断。
* 表头行加粗 + `D9E2F3` 底纹 + `<w:tblHeader/>`（跨页重复）；全表 `single` 细边框；所有单元格垂直居中；文字 10.5 pt。

### 2.2 `omml` 模块

```python
latex_to_omml(latex: str) -> str           # <m:oMath> 的“内层 XML”（子元素，无外层包裹）
inline_omml(latex) -> str                  # <m:oMath>...</m:oMath>
display_omml(latex, jc="center") -> str    # <m:oMathPara>...</m:oMathPara>
omml_paragraph(latex, number=None, ...) -> str    # 完整 <w:p>（number 非空时用制表位）
equation_table(latex, number, ...) -> str         # 无边框 1×2 <w:tbl>
UNKNOWN_MACROS: list[str]                  # 未能识别的宏（含重复、按出现顺序）
```

`latex_to_omml` 返回的内容**只含 `m:` 命名空间的元素**，不发射任何 `w:` 元素，因此可以单独用
`<root xmlns:m="...">` 包裹后做 XML 良构校验。

---

## 3. 版式与单位

| 项目 | 取值 |
|---|---|
| 纸张 | A4，`w:pgSz w:w="11906" w:h="16838"` |
| 上下页边距 | **1440 twips = 2.540 cm**（2.5 cm 的近似值，即 1 英寸） |
| 左右页边距 | **1588 twips = 2.8006 cm**（2.8 cm 的近似值） |
| 可用正文宽度 | 8730 twips = 15.397 cm |
| 页脚距边界 | 851 twips（1.5 cm） |
| 换算 | 1 cm = 567 twips = 360000 EMU；1 twip = 635 EMU |

> Word 的 twips 无法精确表示 2.5 cm / 2.8 cm，这里采用任务允许的 1440 / 1588 近似值，并在代码中以
> `MARGIN_TB_TW` / `MARGIN_LR_TW` 常量显式命名。

正文：Times New Roman（ascii/hAnsi/cs）+ 宋体（eastAsia），12 pt，行距 1.5 倍（`w:line="360" w:lineRule="auto"`），
首行缩进 2 字符（`w:ind w:firstLineChars="200" w:firstLine="480"`），两端对齐（`w:jc val="both"`）。

标题：黑体（eastAsia）+ 加粗，16 / 14 / 12.5 pt，h1/h2 用 accent 色；样式 `Heading1/2/3` 内含
`<w:outlineLvl w:val="0|1|2"/>` 与 `<w:keepNext/>`，因此 `TOC \o "1-3"` 能正确收录。
标题 run 上同时写入显式 `rPr`，即使样式解析异常外观也不会退化。

---

## 4. 支持的 LaTeX 宏（完整列表）

未列出的宏**不会抛异常**：会退化为字面的 `\macroname` 文本（已 XML 转义），并追加进 `omml.UNKNOWN_MACROS`。

### 4.1 结构类

`\frac{}{}` `\dfrac{}{}` `\tfrac{}{}` `\cfrac{}{}` · `\binom{}{}` `\dbinom{}{}` `\tbinom{}{}` ·
`\sqrt{}` `\sqrt[n]{}` · `\text{}` `\textrm{}` `\textnormal{}` `\mbox{}` `\operatorname{}` `\textbf{}` ·
`{}` 分组 · `^` `_`（含同时上下标 → `<m:sSubSup>`）· `\left…\right` `\middle` `\bigl` `\bigr` `\Big` `\bigg` `\Bigg`（及 `l/r/m` 变体）
· `\,` `\;` `\:` `\!` `\ `（反斜杠+空格）· `\quad` `\qquad` `\enspace` `\thinspace` ·
`\displaystyle` `\textstyle` `\limits` `\nolimits`（空操作）

数学字母表：`\mathrm` `\mathbf` `\boldsymbol` `\mathit` `\mathsf` `\mathtt` `\mathcal` `\mathfrak` `\mathbb` `\mathnormal`
（`\mathbb{R N Z Q C P H F E}` 替换为 ℝ ℕ ℤ ℚ ℂ ℙ ℍ 𝔽 𝔼）

重音/上划线：`\dot` `\ddot` `\hat` `\widehat` `\tilde` `\widetilde` `\vec` `\acute` `\grave` `\check` `\breve` `\mathring`
→ `<m:acc>`；`\bar` `\overline` `\underline` → `<m:bar>`

环境（`\begin{…}…\end{…}`，单元格用 `&` 分隔、`\\` 换行）：
`matrix` `smallmatrix` `pmatrix` `bmatrix` `Bmatrix` `vmatrix` `Vmatrix` `cases` `array` `aligned` `alignedat` `split` `gathered` `subarray`

### 4.2 大运算符（`<m:nary>`，含 `m:chr` 与 `m:limLoc`）

`\sum` `\prod` `\coprod` `\bigcup` `\bigcap` `\bigoplus` `\bigotimes` `\bigodot` `\bigvee` `\bigwedge`
（`limLoc = undOvr`）；`\int` `\iint` `\iiint` `\oint` `\oiint` `\smallint`（`limLoc = subSup`）

无上下限时自动写入 `<m:subHide m:val="1"/>` / `<m:supHide m:val="1"/>`，避免出现空的占位框。

### 4.3 函数名（直立 `<m:sty m:val="p"/>`）

`\sin` `\cos` `\tan` `\cot` `\sec` `\csc` `\arcsin` `\arccos` `\arctan` `\arccot`
`\sinh` `\cosh` `\tanh` `\coth` `\exp` `\ln` `\log` `\lg` `\lb`
`\max` `\min` `\sup` `\inf` `\lim` `\det` `\dim` `\deg` `\gcd` `\hom` `\ker` `\arg` `\sgn` `\sat`
`\tr` `\diag` `\erf` `\prob`

其中 `\lim \max \min \sup \inf \det \dim \gcd` 带下标时生成 `<m:limLow>`（下标在下方）；
不带下标时退化为普通直立 run，不会留下空的 `<m:lim/>` 占位框。

### 4.4 小写希腊字母（斜体）

`\alpha` `\beta` `\gamma` `\delta` `\epsilon`(ϵ) `\varepsilon`(ε) `\zeta` `\eta` `\theta` `\vartheta` `\iota` `\kappa`
`\lambda` `\mu` `\nu` `\xi` `\omicron` `\pi` `\varpi` `\rho` `\varrho` `\sigma` `\varsigma` `\tau` `\upsilon`
`\phi`(ϕ) `\varphi`(φ) `\chi` `\psi` `\omega`

### 4.5 大写希腊字母（直立）

`\Gamma` `\Delta` `\Theta` `\Lambda` `\Xi` `\Pi` `\Sigma` `\Upsilon` `\Phi` `\Psi` `\Omega`

### 4.6 运算符 / 关系 / 其他符号（直立）

```
\times \cdot \pm \mp \div \ast \star \circ \bullet \oplus \otimes \odot \cup \cap \setminus \wedge \vee \land \lor
\leq \le \geq \ge \neq \ne \approx \equiv \sim \simeq \cong \propto \ll \gg \lll \ggg \prec \succ \asymp \doteq
\to \rightarrow \longrightarrow \leftarrow \longleftarrow \leftrightarrow \Leftrightarrow \Rightarrow \Leftarrow
\mapsto \uparrow \downarrow \updownarrow \nearrow \searrow
\in \notin \ni \subset \subseteq \supset \supseteq \emptyset \varnothing
\forall \exists \nexists \neg \lnot \therefore \because
\infty \partial \nabla \angle \perp \parallel \square \triangle \prime \degree \hbar \ell \Re \Im \aleph \wp
\ldots \dots \cdots \vdots \ddots
\langle \rangle \lceil \rceil \lfloor \rfloor \vert \Vert \lvert \rvert \lVert \rVert \lbrace \rbrace
```

### 4.7 单字符转义

`\{ \} \| \% \$ \& \# \_ \( \) \[ \] \/ \- \' \.` 以及 `\,`→U+2009、`\;`→U+2005、`\:`→U+2004、`\!`→（空，见限制）

**合计 302 个可识别宏 / 环境名**（含上表结构类宏与 `\begin{}` 环境名）。

---

## 5. 已知限制（内容作者必读）

1. **`\!` 负细空格**无法在 OMML 中表达，被近似为"无输出"。`\,` `\;` `\:` 用 Unicode 空格字符实现。
2. **`\dfrac` / `\tfrac` 与 `\frac` 外观相同**：OMML 的 `<m:f>` 没有"文本样式分数"概念，三者都生成显示尺寸的 `<m:f>`。
3. **不会自动加运算符间距**：`m:t` 内容是字面文本，`a+b` 的排版间距完全交给 Word 的数学引擎（与 pandoc 的行为一致）。需要额外间距时请显式写 `\,`、`\quad`。
4. **`%` 不是注释符**：LaTeX 的 `%` 注释、`\newcommand`、`\def`、`\label`、`\tag`、`\begin{align}` 等均不支持。
5. **`\begin{align}` / `\begin{equation}` 不支持**：请直接用 `eq()` 为每个公式建一行；多行对齐用 `\begin{aligned}`（环境名支持，但列对齐由 OMML 矩阵的默认对齐控制）。
6. **`\over`、`\atop`、`\substack`、`\stackrel`、`\overset`、`\underset`、`\phantom`、`\boxed`、`\color`、`\cancel`、`\xrightarrow` 等未实现**，会走未知宏回退。
7. **`{}` 空组**会产生空的 `<m:sup>` 等，建议避免 `x^{}`。
8. **行内 `$...$` 只在 `p()` / `bullet()` / `num()` 中解析**；`h1/h2/h3`、`table` 单元格、`caption`、`note` **不解析**公式（会按字面文本输出 `$...$`）。`\$` 可转义美元符。`$$...$$` 不表示显示公式（`$$` 会被解析成一个空的行内公式，随后继续按普通 `$` 配对）。
9. **`r.eq` 编号行为**：`number` 是**纯文本**（如 `"(1)"`），生成器不自动编号、不生成 REF 域、不维护计数器。章节重排后需要调用方自己更新编号字符串。不带 `number` 时公式是一个居中段落，不进入任何表格。
10. **公式编号表格是"隐形表格"**：占 `Tables.Count`，如果后续用 Word COM 统计表格数量需要留意。宽度固定为正文宽度（8730 twips），公式列 7596 twips、编号列 1134 twips。
11. **字体假定**：中文标题假定系统有 **黑体（SimHei）**、正文假定有 **宋体（SimSun）**，公式假定有 **Cambria Math**。缺字体时 Word 会替换，版式可能变化。生成的 `w:rFonts` 同时写 ascii/hAnsi/eastAsia/cs 与 `w:hint="eastAsia"`。
12. **页脚统一应用于所有页面**（含封面），未使用 `w:titlePg` 做首页差异化。
13. **页码总是从 1 开始**，未生成 `w:pgNumType w:start`，也未对目录使用罗马数字分节。
14. **图片**只支持 PNG / JPEG；`width_cm` 超过正文宽度（15.40 cm）会被裁剪到正文宽度并写入 `warnings`。高度始终由宽高比推算，**无法单独指定高度**。同一份图片字节会被去重（共用一个 media 部件与一个关系 id）。
15. **表格**：不支持合并单元格（`gridSpan`/`vMerge`）、不支持单元格内换行/多段、不支持嵌套表格、不支持自动列宽（始终 `w:tblLayout="fixed"`）。单元格文本按**纯文本**处理（不解析 `$...$`）。
16. **列表**：`num()` 的连续组各自持有独立 `w:numId`（同一 `abstractNum`），因此插入正文后重新从 1 开始；`bullet()` 全部共用 `numId=1`。最多 4 级（0–3）。
17. **`layout="tabs"` 的公式编号方案未被渲染验证**，默认且推荐的方案是 `layout="table"`（无边框表格）。
18. **封面/目录不参与自动分页优化**：`cover()` 末尾有分页符，`toc()` 默认不分页（需要时传 `page_break_after=True` 或手动 `page_break()`）。
19. **目录域需要在 Word 中更新**：`settings.xml` 写了 `<w:updateFields w:val="true"/>`、域字符带 `w:dirty="true"`，Word 打开时会提示"是否更新域"。若选择否，目录处显示的是占位提示文字。
20. **不生成** `word/fontTable.xml`、`word/theme/theme1.xml`、`word/webSettings.xml`、批注、修订、书签、超链接。

---

## 6. 生成/校验的 OOXML 部件

```
[Content_Types].xml
_rels/.rels
docProps/core.xml
docProps/app.xml
word/document.xml
word/_rels/document.xml.rels          rId1 styles, rId2 settings, rId3 numbering,
                                      rId4 footer1, rId5+ media
word/styles.xml                       docDefaults, Normal, Heading1/2/3, TOC1/2/3, Caption
word/settings.xml                     <w:updateFields w:val="true"/> + m:mathPr
word/numbering.xml                    abstractNum 0 = 项目符号, 1 = 编号
word/footer1.xml                      居中 PAGE 域，格式“第 X 页”
word/_rels/footer1.xml.rels           空（无关系）
word/media/imageN.png|jpeg
```

---

## 7. 自检

```powershell
cd <仓库根>/tools/word
python selftest.py            # 完整自检（含 Word COM 尝试）
python selftest.py --no-com   # 只做静态校验
```

自检做四件事：

1. **纯 Python 生成图片**：`selftest_fig.png` 400×260 RGB（渐变 + 红色正弦曲线），只用 `zlib` + `struct`，无外部依赖；
   另生成 120×90 的 `selftest_fig2.png` 用于多图/去重测试。
2. **生成两份文档**：`selftest.docx`（封面、目录、h1/h2/h3、含行内公式的正文、6 个编号显示公式、
   5×4 带题注表格、嵌入插图）与 `selftest_edge.docx`（无表头表格、图片去重 + 第二张不同图片、
   `& < >` 转义、空行内公式、未知宏回退、列表重启、制表位公式方案）。
3. **静态校验 100 项**：
   * `zipfile.ZipFile(...).testzip() is None`
   * 每个 `*.xml` / `*.rels` 都用 `xml.etree.ElementTree` 解析成功
   * **严格的 OOXML 子元素顺序与必需子元素校验**（`w:pPr` / `w:rPr` / `w:tblPr` / `w:trPr` / `w:tcPr` /
     `w:sectPr` / `w:settings` / `m:f` / `m:rad` / `m:nary` / `m:d` / `w:inline` / `pic:pic` 等），
     这是"Word 需要修复"的最常见成因
   * 所有关系目标部件存在于 zip 中；`document.xml` 中每个 `r:id` / `r:embed` 都能解析；
     被引用的 `w:pStyle` / `w:numId` / `w:abstractNumId` 都有定义
   * `[Content_Types].xml` 覆盖实际用到的每个扩展名与部件
   * media 部件与源 PNG **逐字节相同**
   * OMML 是真数学而非文本（`m:oMath` / `m:oMathPara` / `m:f` / `m:nary` / `m:rad` / `m:m` / `m:sSubSup` / `m:d` / `m:acc` / `m:bar` / `m:limLow` 计数与属性）
   * `&` 转义、`w:updateFields`、A4 尺寸与页边距、TOC 域指令、页脚 PAGE 域、标题样式与字号
   * 图片 `wp:extent` / `wp:docPr` 唯一 id / `a:blip r:embed` / `a:prstGeom prst="rect"` / 宽高比 / `width_cm` 换算
   * `jpeg_size()` 对合成 SOF0 头（64×48、1920×1080）解析正确，且对非 JPEG 输入抛 `ValueError`
4. **Word COM 渲染校验**（`--no-com` 可跳过）：见下节。

成功时退出码 0 并打印 `SELFTEST PASS`（两份文档合计 100 项 PASS）。

### Word COM 渲染校验说明

`selftest.py` 会先跑一个**对照组**（对空白文档执行 `Documents.Add()`），再打开 `selftest.docx`、
`Fields.Update()` 更新目录、导出 `selftest.pdf`（`ExportAsFixedFormat(..., 17)`）并打印
`PAGES` / `OMATHS` / `TABLES` / `SHAPES` / `TOC_HITS` 等。

* 对照组通过 → 正常报告页数与 PDF 体积。
* 对照组不通过 → 打印 **`BLOCKED BY THE SANDBOX`** 及完整错误信息，**不判为文档缺陷**，自检仍以静态校验为准。
* 超时 → 杀掉本次新起的 `WINWORD.EXE` 并报告 INCONCLUSIVE。

**在 workspace-write 沙箱下的实测结果：COM 被沙箱阻断。**

```
Documents.Add()   -> Word 出现问题。       HResult 0x800A13E9
Documents.Open()  -> Word 未能引发事件。   HResult 0x800A1772
（有时表现为 Word 挂起在不可见的模态对话框上）
```

原因：Word 必须写自己的用户配置目录，而沙箱拒绝写入
（`System.UnauthorizedAccessException`）：

```
%APPDATA%\Microsoft\Word
%APPDATA%\Microsoft\Templates
%LOCALAPPDATA%\Microsoft\Office
```

由于连**空白文档**都无法创建，该失败与生成的 `.docx` 无关。若要在沙箱外获得真实页数与 PDF，
请在可写 `%APPDATA%` 的环境下重跑 `python selftest.py`（Word 16.0 已在本机注册可用）。

---

## 8. 实现要点

* **`omml.py`** 采用真正的分词器 + 递归下降解析器：`_tokenize()` 把 LaTeX 切成
  `CMD / LBRACE / LBRACKET / CARET / UNDER / AMP / ROWSEP / CHAR` 记号（空白不丢弃，而是记录在下一个记号的
  `space` 字段上，供 `\text{}` 还原），`_Parser.parse_seq()` 逐个人造 `_Atom` 并处理上下标绑定。
* 大运算符采用"开放槽位"模型：遇到 `\sum` 后先接收 `_`/`^`，再把**紧随其后的一个操作数**吞进
  `<m:e>`，从而既避免空参数占位框，又保证 `\sum_{i=1}^n x_i^2` 的 `_i^2` 绑在 `x` 上而不是 `∑` 上。
* 变量（拉丁/希腊字母）默认斜体，数字、运算符、函数名显式 `<m:rPr><m:sty m:val="p"/></m:rPr>`，
  `\text{}` 用 `<m:nor/>` 走正文文本字体。
* **`report_docx.py`** 中所有文本都经 `xml.sax.saxutils.escape`；属性值额外转义 `"`。
* 段落属性严格按 `CT_PPrBase` 顺序拼装（`pStyle → keepNext → numPr → tabs → spacing → ind → jc → outlineLvl → rPr`），
  表格同理（`tblW → jc → tblBorders → tblLayout → tblCellMar → tblLook`），
  这一点由自检的严格顺序校验兜底。
