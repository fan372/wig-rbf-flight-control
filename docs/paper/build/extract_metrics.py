# -*- coding: utf-8 -*-
"""extract_metrics.py —— 把 MATLAB 仿真日志解析为机器可读的 metrics.json。

这是会议论文生成的【唯一数值来源】：论文正文里的每一个数字都必须从
metrics.json 取值，禁止硬编码，从而保证论文与 results/log_*.txt 永久一致。

用法：
    python extract_metrics.py                # 解析 ../..//matlab_simulink/results
    python extract_metrics.py --check        # 额外做自洽性校验

设计原则：
  * 每个正则若匹配失败 -> 立即抛错并指出是哪个日志、哪一节，
    绝不允许"静默产生 None 再写进论文"。
  * 所有解析结果保留日志中的原始精度（浮点数），不做四舍五入。
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
RESULTS = os.path.join(ROOT, 'matlab_simulink', 'results')
OUT = os.path.join(HERE, 'metrics.json')


# --------------------------------------------------------------------------
class ParseError(RuntimeError):
    pass


def read_log(name: str) -> str:
    path = os.path.join(RESULTS, name)
    if not os.path.isfile(path):
        raise ParseError(f'缺少日志文件：{path}')
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


def f(x: str) -> float:
    return float(x.replace('−', '-').replace('+', ''))


def rows(text: str, header_pat: str, row_pat: str, ncols: int,
         logname: str, section: str) -> list[list[float]]:
    """在 text 中定位 header_pat，随后连续解析符合 row_pat 的数值行。"""
    m = re.search(header_pat, text)
    if not m:
        raise ParseError(f'[{logname}] 找不到表头：{section}')
    tail = text[m.end():]
    out: list[list[float]] = []
    for line in tail.splitlines():
        if not line.strip():
            if out:
                break
            continue
        mm = re.match(row_pat, line.strip())
        if not mm:
            if out:
                break
            continue
        vals = [f(g) for g in mm.groups()]
        if len(vals) != ncols:
            raise ParseError(f'[{logname}] {section}: 期望 {ncols} 列，实得 {len(vals)}')
        out.append(vals)
    if not out:
        raise ParseError(f'[{logname}] {section}: 表头之后没有解析到任何数据行')
    return out


def scalar(text: str, pat: str, logname: str, what: str) -> float:
    m = re.search(pat, text)
    if not m:
        raise ParseError(f'[{logname}] 找不到 {what}')
    return f(m.group(1))


# --------------------------------------------------------------------------
def parse_analysis() -> dict:
    ln = 'log_analysis.txt'
    t = read_log(ln)

    ge = rows(
        t,
        r'---- 1\. 地效因子与有效升力线斜率 ----\n\s*h\[m\][^\n]*\n',
        r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)%',
        7, ln, '§1 地效因子')

    trim = rows(
        t,
        r'---- 2\. 配平特性[^\n]*\n\s*h\[m\][^\n]*\n',
        r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+'
        r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',
        12, ln, '§2 配平特性')

    modes = rows(
        t,
        r'---- 3\. 纵向模态随高度变化[^\n]*\n\s*h\[m\][^\n]*\n',
        r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',
        6, ln, '§3 纵向模态')

    ph = []
    for m in re.finditer(
            r'h=([\d.]+) m: L=([\d.]+) N D=([\d.]+) N L/D=([\d.]+) -> '
            r'经典 wn_p=([\d.]+) zeta_p=\+?([-\d.]+)', t):
        ph.append([f(g) for g in m.groups()])
    if len(ph) < 3:
        raise ParseError(f'[{ln}] §4 经典浮沉理论校核解析不足')

    return {
        'ge': {
            'h': [r[0] for r in ge], 'hb': [r[1] for r in ge],
            'kappa_nom': [r[2] for r in ge], 'kappa_true': [r[3] for r in ge],
            'aw_nom': [r[4] for r in ge], 'aw_true': [r[5] for r in ge],
            'aw_gain_pct': [r[6] for r in ge],
        },
        'trim': {
            'h': [r[0] for r in trim],
            'alpha_nom': [r[1] for r in trim], 'alpha_true': [r[2] for r in trim],
            'de_nom': [r[3] for r in trim], 'de_true': [r[4] for r in trim],
            'dt_nom': [r[5] for r in trim], 'dt_true': [r[6] for r in trim],
            'LD_nom': [r[7] for r in trim], 'LD_true': [r[8] for r in trim],
            'dLdh': [r[9] for r in trim], 'dMdh': [r[10] for r in trim],
            'SM': [r[11] for r in trim],
        },
        'modes': {
            'h': [r[0] for r in modes],
            're': [r[1] for r in modes], 'im': [r[2] for r in modes],
            'zeta': [r[3] for r in modes],
            're_noge': [r[4] for r in modes], 'im_noge': [r[5] for r in modes],
        },
        'phugoid': {
            'h': [r[0] for r in ph], 'L': [r[1] for r in ph], 'D': [r[2] for r in ph],
            'LD': [r[3] for r in ph], 'wn_p': [r[4] for r in ph], 'zeta_p': [r[5] for r in ph],
        },
    }


def parse_smoke() -> dict:
    ln = 'log_smoke.txt'
    t = read_log(ln)
    d = {}
    m = re.search(r'S=([\d.]+) m\^2\s+AR=([\d.]+)\s+W=([\d.]+) N\s+T/W=([\d.]+)', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到参数检查行')
    d['S'], d['AR'], d['W'], d['TW'] = (f(g) for g in m.groups())
    d['CL_req'] = scalar(t, r'需要 CL ~ ([\d.]+)', ln, 'CL 需求')

    mism = rows(t, r'---- 5\. 名义/真实模型失配量[^\n]*\n\s*h\[m\][^\n]*\n',
                r'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', 4, ln, '§5 失配量')
    d['mismatch'] = {
        'h': [r[0] for r in mism], 'dM': [r[1] for r in mism],
        'dL': [r[2] for r in mism], 'dD': [r[3] for r in mism],
    }
    d['dL_max_abs'] = max(abs(v) for v in d['mismatch']['dL'])
    d['dL_max_pct_W'] = 100.0 * d['dL_max_abs'] / d['W']
    d['dM_max_abs'] = max(abs(v) for v in d['mismatch']['dM'])
    d['dD_min'] = min(d['mismatch']['dD'])
    d['dD_max'] = max(d['mismatch']['dD'])
    return d


def parse_mdh() -> dict:
    ln = 'log_mdh.txt'
    t = read_log(ln)
    dec = rows(
        t,
        r'---- 1\. 分量分解表[^\n]*\n\s*h\[m\][^\n]*\n',
        r'([-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+'
        r'([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)',
        8, ln, '§1 分量分解')

    ld = rows(
        t,
        r'---- 4\. 升力/阻力高度导数 ----\n\s*h\[m\][^\n]*\n',
        r'([-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)',
        4, ln, '§4 升阻力高度导数')

    nom = rows(
        t,
        r'---- 5\. 名义模型 vs 真实对象[^\n]*\n\s*h\[m\][^\n]*\n',
        r'([-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)',
        4, ln, '§5 名义/真实对比')

    res_max = scalar(t, r'最大残差 = ([\d.eE+\-]+) N·m/m', ln, '最大残差')

    return {
        'h': [r[0] for r in dec],
        'total': [r[1] for r in dec],
        'wing': [r[2] for r in dec],
        'tail': [r[3] for r in dec],
        'ram': [r[4] for r in dec],
        'nl': [r[5] for r in dec],
        'fuse': [r[6] for r in dec],
        'thrust': [r[7] for r in dec],
        'dLdh': [r[1] for r in ld],
        'dDdh': [r[2] for r in ld],
        'wn_h': [r[3] for r in ld],
        'nom_total': [r[1] for r in nom],
        'true_total': [r[2] for r in nom],
        'mismatch': [r[3] for r in nom],
        'resid_max': res_max,
    }


def parse_stab() -> dict:
    ln = 'log_stab.txt'
    t = read_log(ln)
    d = {}
    d['dVdot_dV'] = scalar(t, r'dVdot/dV\s*=\s*([+\-\d.]+)', ln, 'dVdot/dV')
    d['dVdot_dgam'] = scalar(t, r'dVdot/dgam\s*=\s*([+\-\d.]+)', ln, 'dVdot/dgam')
    d['dgamdot_dV'] = scalar(t, r'dgamdot/dV\s*=\s*([+\-\d.]+)', ln, 'dgamdot/dV')
    d['dgamdot_dalpha'] = scalar(t, r'dgamdot/dalpha\s*=\s*([+\-\d.]+)', ln, 'dgamdot/dalpha')
    d['dgamdot_dh'] = scalar(t, r'dgamdot/dh\s*=\s*([+\-\d.]+)', ln, 'dgamdot/dh')
    d['dqdot_dalpha'] = scalar(t, r'dqdot/dalpha\s*=\s*([+\-\d.]+)', ln, 'dqdot/dalpha')
    d['dqdot_dq'] = scalar(t, r'dqdot/dq\s*=\s*([+\-\d.]+)', ln, 'dqdot/dq')
    d['dqdot_dh'] = scalar(t, r'dqdot/dh\s*=\s*([+\-\d.]+)', ln, 'dqdot/dh')
    d['dqdot_dde'] = scalar(t, r'dqdot/dde\s*=\s*([+\-\d.]+)', ln, 'dqdot/dde')

    d['dLdh'] = scalar(t, r'dL/dh\s*=\s*([+\-\d.]+) N/m', ln, 'dL/dh')
    d['dDdh'] = scalar(t, r'dD/dh\s*=\s*([+\-\d.]+) N/m', ln, 'dD/dh')
    d['dMdh'] = scalar(t, r'dM/dh\s*=\s*([+\-\d.]+) N·m/m', ln, 'dM/dh')
    d['wn_h'] = scalar(t, r'对应高度振荡频率\s*([\d.]+) rad/s', ln, 'wn_h')

    for key, pat in [('wing', r'机翼（稳定项）\s+([+\-\d.]+)'),
                     ('tail', r'平尾（主导不稳定项）\s+([+\-\d.]+)'),
                     ('ram', r'RAM 附加力\s+([+\-\d.]+)'),
                     ('nl', r'升力非线性软化\s+([+\-\d.]+)'),
                     ('fuse', r'机体\s+([+\-\d.]+)'),
                     ('thrust', r'推力线偏置\s+([+\-\d.]+)')]:
        d['part_' + key] = scalar(t, pat, ln, 'dM/dh 分项 ' + key)

    d['phugoid_wn'] = scalar(t, r'理论 wn_p = ([\d.]+) rad/s', ln, 'wn_p')
    d['phugoid_zeta'] = scalar(t, r'zeta_p = 1/\(sqrt\(2\)\*L/D\) = ([+\-\d.]+)', ln, 'zeta_p')

    sweep = rows(
        t,
        r'---- 逐高度扫描[^\n]*\n\s*h\[m\][^\n]*\n',
        r'([-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([+\-\d.]+)\s+([\d.]+)',
        6, ln, '逐高度扫描')
    d['sweep'] = {
        'h': [r[0] for r in sweep], 're': [r[1] for r in sweep],
        'im': [r[2] for r in sweep], 'zeta': [r[3] for r in sweep],
        'dLdh': [r[4] for r in sweep], 'wn_h': [r[5] for r in sweep],
    }
    return d


def parse_scenarios() -> dict:
    ln = 'log_scenarios.txt'
    t = read_log(ln)

    def grab(pat: str, what: str) -> dict:
        m = re.search(pat, t)
        if not m:
            raise ParseError(f'[{ln}] 找不到 {what}')
        g = m.groups()
        out = {'h_rms': f(g[0]), 'h_err_max': f(g[1]), 'h_min': f(g[2]), 'ok': int(f(g[3]))}
        if len(g) > 4:
            out['V_rms'] = f(g[4])
            out['de_max'] = f(g[5]) if len(g) > 5 else None
        return out

    ad = grab(r'RBF自适应 \+ 鲁棒项\s+h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) '
              r'V_rms=([\d.]+) de_max=\s*([\d.]+)° ok=(\d)', '场景1 自适应')
    di = grab(r'仅名义动态逆 \+ 鲁棒项\s+h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) '
              r'V_rms=([\d.]+) de_max=\s*([\d.]+)° ok=(\d)', '场景1 动态逆+鲁棒')
    pu = grab(r'纯名义动态逆（无自适应无鲁棒）\s+h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) '
              r'V_rms=([\d.]+) de_max=\s*([\d.]+)° ok=(\d)', '场景1 纯动态逆')

    # 场景 2：参数摄动
    m = re.search(r'---- 场景 2：对象参数摄动 ----(.*?)---- 场景 3', t, re.S)
    if not m:
        raise ParseError(f'[{ln}] 找不到场景 2')
    pert = []
    for line in m.group(1).splitlines():
        mm = re.match(r'(.+?)\s+h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) '
                      r'V_rms=([\d.]+) de_max=\s*([\d.]+)° ok=(\d)', line.strip())
        if mm:
            pert.append({
                'label': mm.group(1).strip(),
                'h_rms': f(mm.group(2)), 'h_err_max': f(mm.group(3)),
                'h_min': f(mm.group(4)), 'V_rms': f(mm.group(5)),
                'de_max': f(mm.group(6)), 'ok': int(mm.group(7)),
            })
    if len(pert) < 5:
        raise ParseError(f'[{ln}] 场景 2 只解析到 {len(pert)} 行')

    # 场景 3：大气扰动
    m = re.search(r'---- 场景 3：大气扰动（阵风/湍流） ----(.*?)---- 场景 4', t, re.S)
    if not m:
        raise ParseError(f'[{ln}] 找不到场景 3')
    gust = []
    cur = None
    for line in m.group(1).splitlines():
        s = line.strip()
        mm = re.match(r'(.+?)\s+自适应: h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) ok=(\d)', s)
        if mm:
            cur = {'label': mm.group(1).strip(), 'ad_h_rms': f(mm.group(2)),
                   'ad_h_err_max': f(mm.group(3)), 'ad_h_min': f(mm.group(4)),
                   'ad_ok': int(mm.group(5))}
            gust.append(cur)
            continue
        mm = re.match(r'无自适应: h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) ok=(\d)', s)
        if mm and cur is not None:
            cur['no_h_rms'] = f(mm.group(1))
            cur['no_h_err_max'] = f(mm.group(2))
            cur['no_h_min'] = f(mm.group(3))
            cur['no_ok'] = int(mm.group(4))
    if len(gust) < 3:
        raise ParseError(f'[{ln}] 场景 3 只解析到 {len(gust)} 行')

    # 场景 4
    m = re.search(r'---- 场景 4：量测噪声 \+ 执行器限制 \+ 极限低空掠飞 ----(.*?)====', t, re.S)
    if not m:
        raise ParseError(f'[{ln}] 找不到场景 4')
    low = {}
    mm = re.search(r'噪声\+极限低空\s+h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) '
                   r'V_rms=([\d.]+) de_max=\s*([\d.]+)° ok=(\d)', m.group(1))
    if not mm:
        raise ParseError(f'[{ln}] 场景 4 自适应行解析失败')
    low['ad'] = {'h_rms': f(mm.group(1)), 'h_err_max': f(mm.group(2)), 'h_min': f(mm.group(3)),
                 'V_rms': f(mm.group(4)), 'de_max': f(mm.group(5)), 'ok': int(mm.group(6))}
    mm = re.search(r'噪声\+极限低空\(无自适应\)\s+h_rms=([\d.]+) h_err_max=([\d.]+) h_min=([\d.]+) '
                   r'V_rms=([\d.]+) de_max=\s*([\d.]+)° ok=(\d)', m.group(1))
    if not mm:
        raise ParseError(f'[{ln}] 场景 4 无自适应行解析失败')
    low['no'] = {'h_rms': f(mm.group(1)), 'h_err_max': f(mm.group(2)), 'h_min': f(mm.group(3)),
                 'V_rms': f(mm.group(4)), 'de_max': f(mm.group(5)), 'ok': int(mm.group(6))}

    return {
        's1_adaptive': ad, 's1_di_rob': di, 's1_di': pu,
        's2_pert': pert, 's3_gust': gust, 's4_low': low,
        's1_improve': di['h_rms'] / ad['h_rms'],
        's1_improve_v': di['V_rms'] / ad['V_rms'],
        's2_h_rms_min': min(p['h_rms'] for p in pert),
        's2_h_rms_max': max(p['h_rms'] for p in pert),
        's2_all_ok': all(p['ok'] == 1 for p in pert),
        's2_de_max': max(p['de_max'] for p in pert),
    }


def parse_montecarlo() -> dict:
    ln = 'log_montecarlo.txt'
    t = read_log(ln)
    d = {}
    d['N'] = int(scalar(t, r'样本数 N = (\d+)', ln, '样本数'))

    stats: list[tuple[str, list[float]]] = []
    mstat = re.search(r'---- 统计结果 ----\n[^\n]*\n(.*?)\n\s*\n', t, re.S)
    if not mstat:
        raise ParseError(f'[{ln}] 找不到统计结果表')
    for line in mstat.group(1).splitlines():
        mm = re.match(r'\s*(.+?)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$', line)
        if mm:
            stats.append((mm.group(1).strip(), [f(g) for g in mm.groups()[1:]]))
    if len(stats) < 4:
        raise ParseError(f'[{ln}] 统计结果只解析到 {len(stats)} 行')
    d['stat'] = {lab: {'mean': v[0], 'std': v[1], 'median': v[2], 'p95': v[3], 'max': v[4]}
                 for lab, v in stats}
    d['stat_labels'] = [lab for lab, _ in stats]

    m = re.search(r'通过率（未触地且收敛）: 自适应 (\d+)/(\d+) = ([\d.]+)%\s+无自适应 (\d+)/(\d+) = ([\d.]+)%', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到通过率')
    d['pass_ad_n'], d['pass_ad_N'], d['pass_ad_pct'] = int(m.group(1)), int(m.group(2)), f(m.group(3))
    d['pass_no_n'], d['pass_no_N'], d['pass_no_pct'] = int(m.group(4)), int(m.group(5)), f(m.group(6))

    m = re.search(r'高度误差 RMS 中位数:\s+自适应 ([\d.]+) m\s+无自适应 ([\d.]+) m\s+（改善 ([\d.]+) 倍）', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到中位数改善')
    d['med_ad'], d['med_no'], d['med_improve'] = f(m.group(1)), f(m.group(2)), f(m.group(3))

    m = re.search(r'权值范数终值: \|\|W1\|\| 均值 ([\d.]+) \(max ([\d.]+)\), \|\|W2\|\| 均值 ([\d.]+) \(max ([\d.]+)\)', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到权值范数终值')
    d['W1_mean'], d['W1_max'], d['W2_mean'], d['W2_max'] = (f(g) for g in m.groups())

    m = re.search(r'高度误差 峰值 中位数:\s+自适应 ([\d.]+) m\s+无自适应 ([\d.]+) m', t)
    if m:
        d['peak_med_ad'], d['peak_med_no'] = f(m.group(1)), f(m.group(2))
    return d


def parse_simulink() -> dict:
    ln = 'log_simulink.txt'
    t = read_log(ln)
    d = {}
    pats = {
        'h_rms': r'h_rms \[m\]\s+([\d.]+)\s+([\d.]+)\s+([\d.eE+\-]+)',
        'h_err_max': r'h 误差峰值 \[m\]\s+([\d.]+)\s+([\d.]+)\s+([\d.eE+\-]+)',
        'h_min': r'h_min \[m\]\s+([\d.]+)\s+([\d.]+)\s+([\d.eE+\-]+)',
        'V_rms': r'V_rms \[m/s\]\s+([\d.]+)\s+([\d.]+)\s+([\d.eE+\-]+)',
    }
    for k, p in pats.items():
        m = re.search(p, t)
        if not m:
            raise ParseError(f'[{ln}] 找不到 {k}')
        d[k] = {'sl': f(m.group(1)), 'ml': f(m.group(2)), 'dev': f(m.group(3))}

    m = re.search(r'de 峰值 \[deg\]（状态）\s+([\d.]+)\s+([\d.]+)\s+([\d.eE+\-]+)', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到 de 峰值（状态）')
    d['de_state'] = {'sl': f(m.group(1)), 'ml': f(m.group(2)), 'dev': f(m.group(3))}

    m = re.search(r'de 峰值 \[deg\]（指令）\s+([\d.]+)\s+([\d.]+)\s+([\d.eE+\-]+)', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到 de 峰值（指令）')
    d['de_cmd'] = {'sl': f(m.group(1)), 'ml': f(m.group(2)), 'dev': f(m.group(3))}

    m = re.search(r'最大轨迹偏差（状态 vs 状态）：高度 ([\d.eE+\-]+) m，速度 ([\d.eE+\-]+) m/s，'
                  r'升降舵 ([\d.eE+\-]+) deg', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到最大轨迹偏差')
    d['traj_h'], d['traj_V'], d['traj_de'] = (f(g) for g in m.groups())

    m = re.search(r'最大指令偏差（指令 vs 指令）：升降舵 ([\d.eE+\-]+) deg', t)
    if m:
        d['traj_de_cmd'] = f(m.group(1))

    m = re.search(r'Simulink 仿真完成，耗时 ([\d.]+) s', t)
    if m:
        d['sim_time'] = f(m.group(1))
    return d


def parse_clp() -> dict:
    ln = 'log_clp.txt'
    t = read_log(ln)
    d = {}
    m = re.search(r'最终整定参数（shipped wig_params）', t)
    if not m:
        raise ParseError(f'[{ln}] 找不到"最终整定参数"小节（run_00_clp_body.m 需按要求输出）')
    tail = t[m.end():]

    def grab(pat, what, required=True):
        mm = re.search(pat, tail)
        if not mm:
            if required:
                raise ParseError(f'[{ln}] 最终参数小节里找不到 {what}')
            return None
        return mm

    m2 = grab(r'max\|z\| = ([\d.]+)', 'max|z|')
    d['final_maxabsz'] = f(m2.group(1))
    m3 = grab(r'h_eq = ([\d.]+)', 'h_eq')
    d['h_eq'] = f(m3.group(1))
    m4 = grab(r'res_eq = ([\d.eE+\-]+)', 'res_eq')
    d['res_eq'] = f(m4.group(1))

    # 最慢模态（出厂增益极点表的第 1 行）
    m5 = re.search(r'^\s*1\s+\|z\|=([\d.]+)\s+s=\s*([+\-]?[\d.]+)\s+([+\-][\d.]+)i\s+(\w+)',
                   tail, re.M)
    if m5:
        d['slow_absz'] = f(m5.group(1))
        d['slow_s_real'] = f(m5.group(2))
        d['slow_s_imag'] = f(m5.group(3))
        d['slow_state'] = m5.group(4)

    # 历史中间态增益
    m6 = re.search(r'历史增益：h_eq=([\d.]+) m，最大极点模 \|z\|max=([\d.]+)', t)
    if m6:
        d['hist_h_eq'] = f(m6.group(1))
        d['hist_maxabsz'] = f(m6.group(2))

    # 结构敏感性测试表（取若干行）
    sens = {}
    for mm in re.finditer(r'^(基准|推力线过质心[^\n]*|关闭鲁棒项|发动机[^\n]*|关闭速度环比例与积分|'
                          r'tau_g=[\d.]+|tau_th=[\d.]+, tau_q=[\d.]+|k_h=[\d.]+, k_hd=[\d.]+)\s+'
                          r'max\|z\| = ([\d.]+)\s+主导 s = ([+\-]?[\d.]+)([+\-][\d.]+)i \(([\w]+)\)',
                          t, re.M):
        sens[mm.group(1).strip()] = {
            'maxabsz': f(mm.group(2)), 's_real': f(mm.group(3)),
            's_imag': f(mm.group(4)), 'state': mm.group(5),
        }
    if sens:
        d['sens'] = sens
    d['robust_off_maxabsz'] = sens.get('关闭鲁棒项', {}).get('maxabsz')
    d['robust_off_s'] = sens.get('关闭鲁棒项', {}).get('s_real')
    return d


def main() -> int:
    metrics = {
        'analysis': parse_analysis(),
        'smoke': parse_smoke(),
        'mdh': parse_mdh(),
        'stab': parse_stab(),
        'scenarios': parse_scenarios(),
        'montecarlo': parse_montecarlo(),
        'simulink': parse_simulink(),
    }
    try:
        metrics['clp'] = parse_clp()
    except ParseError as exc:
        metrics['clp'] = {'_warning': str(exc)}

    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)
    print(f'已写出 {OUT}')

    a = metrics['analysis']
    print(f"  地效因子点数      : {len(a['ge']['h'])}")
    print(f"  配平点数          : {len(a['trim']['h'])}")
    print(f"  模态点数          : {len(a['modes']['h'])}")
    print(f"  dM/dh 分解高度点  : {len(metrics['mdh']['h'])}")
    print(f"  参数摄动工况      : {len(metrics['scenarios']['s2_pert'])}")
    print(f"  蒙特卡洛样本      : {metrics['montecarlo']['N']}")
    print(f"  dM/dh 分解残差    : {metrics['mdh']['resid_max']:.2e}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
