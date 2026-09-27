# -*- coding: utf-8 -*-
"""把 Markdown 源里"微软雅黑没有字形"的字符替换成等价的可显示写法。

发现的 18 类缺字（U+0302 等组合变音符、U+2080 系列下标数字、U+1D40 上标 T 等）
在 PDF 里会被静默丢弃，导致文字残缺（例如 "W̃₁ᵀ" 变成 "W"）。

用法：
    python fix_glyphs_src.py            # 就地替换全部 docs/tutorial_src/*.md
    python fix_glyphs_src.py --dry      # 只报告不写
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(ROOT, 'docs', 'tutorial_src')

SUB = {chr(0x2080 + i): str(i) for i in range(10)}          # ₀..₉ -> 0..9
SUP = {chr(0x2070 + i): str(i) for i in range(10)}          # ⁰..⁹ -> 0..9

# 顺序很重要：组合音符先按"基字符 + 音符"整体替换
# 注意：Python 的 re 替换串不支持 \uXXXX 转义，这里必须写实际字符
DOT2 = '\u0308'      # 组合分音符（双点）
DOT1 = '\u0307'      # 组合上点
TILDE = '\u0303'     # 组合波浪
MACRON = '\u0304'    # 组合长音
HAT = '\u0302'       # 组合尖帽
SUP2 = '\u00b2'      # ²
DELTA = '\u0394'     # Δ
INFTY = '\u221e'     # ∞

REGEX_RULES = [
    (re.compile('(.)' + DOT2), 'd' + SUP2 + r'\1/dt' + SUP2),   # q̈ -> d²q/dt²
    (re.compile('(.)' + DOT1), r'd\1/dt'),                      # q̇ -> dq/dt
    (re.compile('(.)' + TILDE), DELTA + r'\1'),                 # x̃ -> Δx
    (re.compile('q' + MACRON), 'q' + INFTY),                    # q̄ -> q∞
    (re.compile('(.)' + MACRON), r'\1'),                        # 其余长音符去掉
    (re.compile('(.)' + HAT), r'\1_hat'),                       # x̂ -> x_hat
]

CHAR_RULES = {
    '\u1d40': '^T',      # ᵀ 转置
    '\u1d62': 'i',       # ᵢ
    '\u2c7c': 'j',       # ⱼ
    '\u1e23': 'dh/dt',   # ḣ
    '\u207b': '^-',      # ⁻
    '\u226a': '<<',      # ≪
    '\u226b': '>>',      # ≫
    '\u2713': '\u221a',  # ✓ -> √
    '\u2717': '\u00d7',  # ✗ -> ×
    '\u2714': '\u221a',
    '\u2718': '\u00d7',
}
CHAR_RULES.update(SUB)
CHAR_RULES.update(SUP)


def fix(text):
    n = 0
    for pat, rep in REGEX_RULES:
        text, k = pat.subn(rep, text)
        n += k
    out = []
    for ch in text:
        if ch in CHAR_RULES:
            out.append(CHAR_RULES[ch])
            n += 1
        else:
            out.append(ch)
    return ''.join(out), n


def main():
    dry = '--dry' in sys.argv
    total = 0
    report = []
    for p in sorted(glob.glob(os.path.join(SRC, '*.md'))):
        raw = open(p, encoding='utf-8').read()
        new, n = fix(raw)
        total += n
        if n:
            report.append('%-28s 替换 %d 处' % (os.path.basename(p), n))
            if not dry:
                open(p, 'w', encoding='utf-8').write(new)
    report.append('合计替换 %d 处%s' % (total, '（dry-run，未写盘）' if dry else ''))
    txt = '\n'.join(report) + '\n'
    with open(os.path.join(HERE, '_fix_glyphs.txt'), 'w', encoding='utf-8') as fh:
        fh.write(txt)
    sys.stdout.buffer.write(txt.encode('utf-8', 'replace'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
