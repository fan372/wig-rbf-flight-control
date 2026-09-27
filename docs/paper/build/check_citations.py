# -*- coding: utf-8 -*-
"""check_citations.py —— 检查参考文献是否有「列了但没引」。

IEEE 等主流会议都要求参考文献表中的每一条都在正文中被引用；
反过来，正文引用了不存在的编号同样是硬错误。本脚本把中英两版、
三个页数版本的正文引用编号全部抽出（支持 [3-5,18-21] 、[7]-[9] 等写法），
与 refs.py 的条目数对照，任一方向不匹配即报错。

用法：
    python check_citations.py        # 通过则退出码 0，否则 1
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_en          # noqa: E402
import content_zh          # noqa: E402
import refs as refs_mod    # noqa: E402

M = json.load(open(os.path.join(HERE, 'metrics.json'), encoding='utf-8'))


def cited_numbers(blocks):
    """从所有文本里抽出引用编号（支持 [3]、[4]-[6]、[22], [26]、$^{[1-2]}$ 等写法）。"""
    chunks = []
    for kind, payload in blocks:
        if isinstance(payload, str):
            chunks.append(payload)
        elif isinstance(payload, (list, tuple)):
            for x in payload:
                if isinstance(x, str):
                    chunks.append(x)
        elif isinstance(payload, dict):
            chunks.append(str(payload.get('caption', '')))
            for row in payload.get('rows', []):
                chunks.extend(str(c) for c in row)
    text = ' \n'.join(chunks)

    nums = set()

    def add_spec(spec: str):
        """把 "3-5" / "18" / "19-21" 这样的片段展开成编号。"""
        for part in re.split(r'[,\s]+', spec.strip()):
            part = part.strip()
            if not part:
                continue
            m = re.fullmatch(r'(\d+)\s*[-–]\s*(\d+)', part)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                if a <= b <= a + 30:
                    nums.update(range(a, b + 1))
            elif part.isdigit():
                nums.add(int(part))

    # 形如 [3-5,18-21,23-24] 的一组
    for m in re.finditer(r'\[(\d[\d,\s\-–]*\d|\d)\]', text):
        add_spec(m.group(1))
    # 形如 [4]-[6] 或 [18]–[20] 的跨组区间
    for m in re.finditer(r'\[(\d+)\]\s*[-–]\s*\[(\d+)\]', text):
        a, b = int(m.group(1)), int(m.group(2))
        if a <= b <= a + 30:
            nums.update(range(a, b + 1))
    return nums


out = []
for name, mod, refs in (('zh', content_zh, refs_mod.REFS_ZH),
                        ('en', content_en, refs_mod.REFS_EN)):
    allnums = set()
    for lv in (6, 8, 12):
        b = mod.build(lv, M, refs)
        n = cited_numbers(b)
        allnums |= n
        out.append(f'  {name} level {lv}: 引用编号 {sorted(n)}')
    missing = [i for i in range(1, len(refs) + 1) if i not in allnums]
    out.append(f'{name}: 参考文献 {len(refs)} 条；三版合计【从未被引用】的编号: {missing}')
    out.append('')

report = '\n'.join(out)
print(report)

# 判定：每个语言，三版合计必须覆盖全部条目，且不得出现越界编号
bad = 0
for name, mod, refs in (('zh', content_zh, refs_mod.REFS_ZH),
                        ('en', content_en, refs_mod.REFS_EN)):
    used = set()
    for lv in (6, 8, 12):
        used |= cited_numbers(mod.build(lv, M, refs))
    n = len(refs)
    never = sorted(i for i in range(1, n + 1) if i not in used)
    beyond = sorted(i for i in used if i > n)
    if never:
        bad += 1
        print(f'  [FAIL] {name}: 列了但从未引用 -> {never}')
    if beyond:
        bad += 1
        print(f'  [FAIL] {name}: 引用了不存在的编号 -> {beyond}')
    if not never and not beyond:
        print(f'  [OK]   {name}: {n} 条文献全部被引用，无越界编号')

print('\nCITATIONS ' + ('PASS' if bad == 0 else 'FAIL'))
sys.exit(1 if bad else 0)
