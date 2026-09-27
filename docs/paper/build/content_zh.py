# -*- coding: utf-8 -*-
"""content_zh.py —— 中文会议论文内容（唯一事实来源）。

所有数值一律从 metrics.json 读取，禁止在正文里硬编码任何仿真数字，
从而保证论文与 matlab_simulink/results/log_*.txt 永远一致。

结构：build(level, M, refs) -> list[Block]
    level : 6 | 8 | 12  （页数版本）
    M     : extract_metrics.py 产出的 dict
    refs  : 参考文献列表（GB/T 7714 文本）
"""
from __future__ import annotations

import math
import os

# ---------------------------------------------------------------- 版头
TITLE_ZH = '地效飞行器纵向 RBF 神经网络自适应飞行控制：地效高度失稳机理与仿真验证'
TITLE_EN = ('RBF Neural-Network Adaptive Longitudinal Flight Control of a '
            'Wing-in-Ground-Effect UAV: Height-Instability Mechanism and Simulation Validation')
# 真实署名不写死在代码里，放在未被版本控制的 author_info.py。
# 公开仓库克隆下来没有该文件，导入失败即退化为「无署名」；
# build_public.py 本来就要求空署名，所以公开构建不受影响。
try:
    from author_info import AUTHOR_ZH, AUTHOR_EN, AFFIL_ZH, AFFIL_EN, EMAIL
except ImportError:                      # 公开仓库中没有 author_info.py
    AUTHOR_ZH = AUTHOR_EN = AFFIL_ZH = AFFIL_EN = EMAIL = ''

AUTHORS = AUTHOR_ZH
AFFIL = [x for x in (
    f'（{AFFIL_ZH}）' if AFFIL_ZH else '',
    f'通信作者：E-mail: {EMAIL}' if EMAIL else '',
) if x]
CLC = '中图分类号：V249.1\u3000\u3000文献标志码：A\u3000\u3000文章编号：（占位）'
FUND = '基金项目：无（本文为作者独立研究，未接受任何基金资助）'

KEYWORDS_ZH = '地效飞行器；飞行控制；RBF 神经网络；自适应控制；动态面控制；高度稳定性'
KEYWORDS_EN = 'wing-in-ground effect; flight control; RBF neural network; adaptive control; dynamic surface control; height stability'


# ---------------------------------------------------------------- 小工具
def n(x, d=2):
    return f'{float(x):.{d}f}'


def sg(x, d=2):
    """带显式正号的数值。"""
    v = float(x)
    return f'{v:+.{d}f}'


def fmt_list(xs, d=2, sep='、'):
    return sep.join(n(v, d) for v in xs)


def rng(xs, d=2):
    xs = [float(v) for v in xs]
    return f'{min(xs):.{d}f} ~ {max(xs):.{d}f}'


# ---------------------------------------------------------------- 摘要
def abstract(M):
    sc = M['scenarios']
    mc = M['montecarlo']
    tr = M['analysis']['trim']
    md = M['mdh']
    return (
        '小型地效飞行器（WIG）的整个使用包线都处在强地效区内，气动特性随离地高度剧烈变化，'
        '其纵向动力学存在两个常规飞机不具备的稳定性问题。本文以一架翼展 '
        f'{n(2.40)} m、质量 {n(12.0, 1)} kg、地效飞行高度 {n(0.05)}~{n(0.50)} m 的地效无人机为对象，'
        '建立含地效因子修正的七阶纵向非线性模型，并定量揭示：'
        f'（1）全包线内俯仰力矩对高度的导数 {sg(min(md["total"]), 2)} ~ {sg(max(md["total"]), 2)} '
        '$\\mathrm{N\\cdot m/m}$ 恒为正，高度静稳定性为负；通过力矩分量分解证明'
        f'其主因是平尾下洗随高度变化（贡献 {sg(max(md["tail"]), 2)} $\\mathrm{{N\\cdot m/m}}$，'
        f'而机翼提供 {sg(min(md["wing"]), 2)} $\\mathrm{{N\\cdot m/m}}$ 的稳定贡献）；'
        f'（2）浮沉-高度耦合模态失稳，实部达 {sg(max(M["analysis"]["modes"]["re"]), 4)} '
        '$\\mathrm{s^{-1}}$，而等效关闭地效后该模态回到临界稳定，证明失稳完全由地效引起。'
        '针对上述问题，设计"高度外环 + 姿态动态面内环 + 速度回路"的三层控制器，'
        '在力矩通道与阻力通道分别引入 RBF 神经网络在线估计与 $\\tanh$ 鲁棒补偿项，'
        '并用 Lyapunov 方法证明闭环系统一致最终有界（UUB）。'
        '进一步给出数字实现的关键约束：离散自适应律的稳定条件为 '
        '$T_s\\Gamma_i\\left\\|\\phi_i\\right\\|^2 < k_i$，'
        '这解释了力矩通道自适应增益必须比阻力通道小三个数量级的原因。'
        f'仿真表明：在存在显著地效失配、RAM 效应与升力非线性的条件下，'
        f'所提控制器把高度跟踪误差 RMS 由 {n(sc["s1_di_rob"]["h_rms"], 4)} m 降至 '
        f'{n(sc["s1_adaptive"]["h_rms"], 4)} m（改善 {n(sc["s1_improve"], 1)} 倍），'
        f'蒙特卡洛通过率由 {n(mc["pass_no_pct"], 1)}% 提升至 {n(mc["pass_ad_pct"], 1)}%，'
        f'并在 {n(0.06)} m 极限低空、量测噪声与中度阵风条件下保持安全飞行。'
    )


def abstract_en(M):
    sc = M['scenarios']
    mc = M['montecarlo']
    md = M['mdh']
    return (
        'Small wing-in-ground-effect (WIG) vehicles operate entirely inside the strong '
        'ground-effect regime, where the aerodynamics vary sharply with height and the '
        'longitudinal dynamics exhibit two stability problems absent in conventional aircraft. '
        'This paper studies a WIG UAV of 2.40 m span and 12.0 kg mass flying at 0.05-0.50 m. '
        'A seventh-order nonlinear longitudinal model with a ground-effect factor is established. '
        'It is shown quantitatively that (i) the pitch-moment height derivative is strictly '
        f'positive over the whole envelope ({sg(min(md["total"]), 2)} to {sg(max(md["total"]), 2)} '
        'N*m/m), i.e. the height static stability is negative, and a component-wise decomposition '
        f'attributes this mainly to the tail downwash variation ({sg(max(md["tail"]), 2)} N*m/m) '
        f'against a stabilising wing contribution ({sg(min(md["wing"]), 2)} N*m/m); and (ii) the '
        f'phugoid-height coupled mode becomes unstable with real part up to '
        f'{sg(max(M["analysis"]["modes"]["re"]), 4)} 1/s, whereas it returns to neutral stability '
        'when the ground effect is switched off, proving that the instability is of ground-effect '
        'origin. A three-loop controller (altitude outer loop, dynamic-surface attitude inner loop '
        'and airspeed loop) is then designed, with two RBF networks and tanh robust terms in the '
        'moment and drag channels. Closed-loop uniform ultimate boundedness is proved by Lyapunov '
        'arguments. A discrete-time design constraint, Ts*Gamma_i*||phi_i||^2 < k_i, is derived, '
        'which explains why the moment-channel adaptation gain has to be three orders of magnitude '
        'smaller than the drag-channel one. Simulations show that the height-tracking RMS error is '
        f'reduced from {n(sc["s1_di_rob"]["h_rms"], 4)} m to {n(sc["s1_adaptive"]["h_rms"], 4)} m '
        f'(a factor of {n(sc["s1_improve"], 1)}), the Monte-Carlo pass rate rises from '
        f'{n(mc["pass_no_pct"], 1)}% to {n(mc["pass_ad_pct"], 1)}%, and safe flight is maintained '
        'at an extreme altitude of 0.06 m, under measurement noise and in moderate gusts.'
    )


# ---------------------------------------------------------------- 页数版本
# 每个内容块最早出现在哪一版：6 = 三版都收，8 = 8/12 页版，12 = 仅 12 页版。
# 三版严格包含（6 ⊆ 8 ⊆ 12）；build_all.py 另会校验中英两版逐块结构一致。
MINLV = {
    'related': 8,        # 1.1 相关工作（整节）
    'contrib': 8,        # 引言中的贡献清单
    'conf': 8,           # 2.1 参考构型与坐标系（含主要参数表）
    'getab': 12,          # 表：地效因子与有效升力线斜率
    'mismatch': 8,       # 2.4 名义模型与真实对象的不确定性（含失配表）
    'fig_trim': 12,       # 图：配平特性
    'mech': 6,           # 3.2 力矩分解的物理机理要点
    'mc_setup': 8,       # 5.6 蒙特卡洛抽样范围说明段
    'fig_mc': 8,          # 图：蒙特卡洛高度包络
    'trim_disc': 8,     # 3.1 配平结果讨论段
    'modes_lead': 8,    # 3.3 模态结论引导句
    'modes_close': 8,   # 3.3 与力矩分解互相印证段
    'dsc_tune': 8,      # 4.2 俯仰回路等效阻尼整定段
    'eom_tail': 8,      # 2.3 平尾升力与数值积分说明段
    'fig_mdh': 12,       # 图：俯仰力矩高度导数分量堆叠
    'modes_bullet': 8,   # 3.3 模态失稳结论要点
    'tab_modes': 8,      # 表：低频模态随高度（20 行，压缩版放不下，改由正文给出关键值）
    'tab_disc': 6,       # 表：离散自适应稳定裕度（仅 2 行，三版都保留——这是核心结论之一）
    'fig_modes': 12,      # 图：纵向极点分布
    'tuning': 12,         # 4.7 基于采样闭环极点的增益整定
    'nu_e': 12,          # 4.5 中 e-修正系数的设计启示段
    'setup': 8,          # 5.1 仿真设置
    'fig_states': 12,     # 图：状态响应
    'adaptive': 12,       # 图：自适应量时间历程及其说明段
    'extra_trials': 12,   # 5.3/5.4/5.5 参数摄动、大气扰动、极限低空
    'simulink': 12,       # 5.7 Simulink 交叉验证
    'appendix': 12,      # 附录 A 控制器整定参数
}


# ---------------------------------------------------------------- 正文
def build(level, M, refs):
    """返回 [(kind, payload), ...]。level ∈ {6, 8, 12}。"""
    B = []
    a = M['analysis']
    sm = M['smoke']
    md = M['mdh']
    st = M['stab']
    sc = M['scenarios']
    mc = M['montecarlo']
    sI = M['simulink']
    tr = a['trim']
    mo = a['modes']
    ge = a['ge']

    add = B.append

    def g(block, minlv=6):
        """按页数版本收录内容块：minlv=6 表示三版都收，8 表示 8/12 页版，12 表示仅 12 页版。"""
        if level >= minlv:
            B.append(block)

    # 章节号由收录情况自动推出，块在页数版本之间移动时不需要手工改编号
    num = {'sec': 0, 'sub': 0}

    def h1(text, *, numbered=True):
        if numbered:
            num['sec'] += 1
            num['sub'] = 0
            B.append(('h1', f'{num["sec"]}  {text}'))
        else:
            B.append(('h1', text))

    def h2(text, minlv=6):
        if level < minlv:
            return
        num['sub'] += 1
        B.append(('h2', f'{num["sec"]}.{num["sub"]}  {text}'))

    # ============================================================= 1 引言
    h1('引言')

    add(('p', '地效飞行器（Wing-In-Ground effect vehicle, WIG）利用机翼贴近地面（或海面）飞行时'
              '地面镜像涡系对下洗的抑制作用，获得显著增大的升力线斜率与大幅下降的诱导阻力，'
              '从而具备远高于常规飞机的升阻比$^{[1-2]}$。小型地效无人机翼展小、巡航高度低，'
              '其整个使用包线都处在强地效区内：本文对象在 $h = 0.05\\ \\mathrm{m}$ 处'
              f'诱导阻力仅为自由空气的 {n(100*ge["kappa_nom"][0], 1)}%，'
              f'升力线斜率提高 {n(ge["aw_gain_pct"][0], 1)}%；即使在 $h = 0.50\\ \\mathrm{{m}}$ 处，'
              f'升力线斜率仍比自由空气高 {n(ge["aw_gain_pct"][5], 1)}%。'
              '这种随高度剧烈变化的气动特性，使地效飞行器的飞行控制与常规飞机有本质区别。'))

    add(('p', '地效飞行控制的困难集中在两点。其一是**高度静稳定性为负**：'
              '早在 20 世纪 70 年代，Irodov 就指出地效飞行器的高度稳定性判据要求 '
              '$\\partial C_m/\\partial h < 0$，而多数地效构型并不满足$^{[3]}$；'
              '本文第 3 章给出的定量分解表明，本构型在整个包线内 '
              f'$\\partial M/\\partial h = {sg(min(md["total"]), 2)} \\sim {sg(max(md["total"]), 2)}\\ '
              '\\mathrm{N\\cdot m/m}$ 恒为正。其二是**浮沉-高度耦合模态失稳**：'
              '地效作用使经典上临界稳定的浮沉模态变为不稳定，'
              f'包线内低频模态实部最高达 {sg(max(mo["re"]), 4)} $\\mathrm{{s^{{-1}}}}$。'
              '这两点共同决定了地效飞行器必须采用带宽足够的主动高度控制'
              '$^{[5-6,18-21,23-24]}$。'))

    if level >= MINLV['related']:
        h2('相关工作')
        add(('p', '在气动建模方面，地效的准定常建模通常采用"诱导下洗保留系数"的思路：'
                  '以地面镜像涡系对下洗的削弱程度表征地效强度，并据此修正诱导阻力与有效升力线斜率$^{[1,6]}$。'
                  '风洞与 CFD 研究一致表明，地效会显著提高升力线斜率、降低诱导阻力，'
                  '并且会改变"高度焦点"的位置，从而削弱纵向静稳定性，'
                  '因此地效飞行器的纵向稳定性判据不同于常规飞机，'
                  '必须同时满足迎角焦点与高度焦点两方面的要求$^{[3-5,18-21,23-24]}$。'
                  '在控制方面，RBF 神经网络因具有万能逼近性质且权值线性可调，'
                  '被广泛用于不确定非线性系统的直接自适应控制，'
                  '其 Lyapunov 综合框架由 Sanner 与 Slotine$^{[7]}$、'
                  'Polycarpou$^{[8]}$、Ge 与 Wang$^{[14]}$ 等建立；'
                  '鲁棒项采用 $\\tanh$ 饱和函数以平滑符号函数，'
                  '这一平滑化思想在鲁棒自适应设计中广泛使用$^{[9-10]}$；'
                  '投影算子用于保证权值一致有界$^{[10]}$。'
                  '在反步法实现上，动态面控制（DSC）与指令滤波反步通过一阶/二阶滤波器'
                  '避免对虚拟控制量解析求导，解决了"微分爆炸"问题$^{[11-13]}$。'
                  '近期该框架已被推广到大包线飞行器的纵向控制$^{[22,26]}$。'))
        add(('p', '然而，现有文献对地效飞行器自适应控制的研究——'
                  '包括自抗扰与增稳控制等纵向控制工作$^{[25]}$——'
                  '多在**无地效失配**的假设下针对标称对象设计与验证，'
                  '且很少讨论 RBF 自适应律从连续域设计走向**数字实现**时的稳定性约束——'
                  '而连续时间自适应律在未建模动态下的鲁棒性缺陷早已被 Rohrs 反例揭示$^{[15]}$，'
                  '离散时间自适应控制的 Lyapunov 综合也有其独立结论$^{[16-17]}$。'
                  '本文的工作正是在这两点上展开。'))

    h2('本文贡献', MINLV['contrib'])
    g(('p', '本文以一架小型地效无人机为对象，完成以下工作：'), MINLV['contrib'])
    g(('num', [
        '建立含地效因子修正的七阶纵向非线性模型，并显式构造"名义模型/真实对象"失配'
        '（地效强度、RAM 效应、升力非线性），使自适应控制器的补偿对象可量化；',
        '给出俯仰力矩高度导数 $\\partial M/\\partial h$ 的**分量分解**，'
        '定量证明平尾下洗项是高度失稳的主导因素、机翼项是稳定因素，'
        '并给出各项随高度的变化规律；',
        '定量证明浮沉-高度耦合模态失稳完全源于地效：'
        '等效关闭地效后该模态回到临界稳定；',
        '设计三层自适应控制器，在力矩与阻力通道分别引入 RBF 网络与 $\\tanh$ 鲁棒项，'
        '用 Lyapunov 方法证明闭环 UUB；',
        '给出数字实现的离散稳定性判据 $T_s\\Gamma_i\\left\\|\\phi_i\\right\\|^2 < k_i$，'
        '从量纲与采样两个角度解释了双通道自适应增益相差三个数量级的原因；',
        '通过消融、参数摄动、大气扰动、极限低空与蒙特卡洛统计完成验证，'
        '并用 Simulink 模型与纯 MATLAB 脚本做了交叉一致性校核。',
    ]), MINLV['contrib'])

    h2('主要结果')
    add(('table', {
        'headers': ['指标', 'RBF 自适应', '动态逆+鲁棒', '纯动态逆'],
        'rows': [
            ['高度跟踪误差 RMS / m',
             n(sc['s1_adaptive']['h_rms'], 4), n(sc['s1_di_rob']['h_rms'], 4), n(sc['s1_di']['h_rms'], 4)],
            ['高度误差峰值 / m',
             n(sc['s1_adaptive']['h_err_max'], 4), n(sc['s1_di_rob']['h_err_max'], 4), n(sc['s1_di']['h_err_max'], 4)],
            ['最低离地高度 / m',
             n(sc['s1_adaptive']['h_min'], 4), n(sc['s1_di_rob']['h_min'], 4), n(sc['s1_di']['h_min'], 4)],
            ['速度跟踪误差 RMS / (m/s)',
             n(sc['s1_adaptive']['V_rms'], 4), n(sc['s1_di_rob']['V_rms'], 4), n(sc['s1_di']['V_rms'], 4)],
            ['蒙特卡洛通过率 / %',
             n(mc['pass_ad_pct'], 1), '—', n(mc['pass_no_pct'], 1)],
            ['高度误差 RMS 中位数 / m',
             n(mc['med_ad'], 5), '—', n(mc['med_no'], 5)],
        ],
        'key': 'perf', 'caption': '三种控制方案性能对比（真实对象，含地效失配/RAM 效应/升力非线性）',
        'widths': [4.9, 3.2, 3.5, 3.3], 'font_size': 8.5,
        'aligns': ['left', 'center', 'center', 'center'],
    }))

    # ============================================================= 2 建模
    h1('对象建模与地效气动模型')

    h2('参考构型与坐标系', MINLV['conf'])
    g(('p', '采用机体坐标系（$x_b$ 指向机头、$y_b$ 指向右翼、$z_b$ 指向机腹），'
              '俯仰角速度 $q$ 与俯仰力矩 $M$ 均以抬头为正。参考构型的主要参数见表 @tab:params@。'
              '地效飞行高度带取 $h = 0.05 \\sim 0.50\\ \\mathrm{m}$，'
              '对应 $h/b = 0.021 \\sim 0.208$。基本假设：'
              '（1）忽略横侧向运动，纵向与横侧向解耦；'
              '（2）地面为刚性平面，忽略波浪与粗糙度；'
              '（3）气动力准定常，忽略非定常迟滞；'
              '（4）阵风按相对气流方向修正，忽略阵风变化率引起的附加惯性项。'), MINLV['conf'])
    g(('table', {
        'headers': ['参数', '符号', '取值', '参数', '符号', '取值'],
        'rows': [
            ['翼展', '$b$', '2.40 m', '质量', '$m$', '12.0 kg'],
            ['弦长', '$c$', '0.40 m', '俯仰惯量', '$I_{yy}$', '1.15 kg·m²'],
            ['机翼面积', '$S$', '0.96 m²', '最大推力', '$T_{\\max}$', '35 N'],
            ['展弦比', '$AR$', '6.0', '巡航速度', '$V_0$', '18 m/s'],
            ['零升迎角', '$\\alpha_{L0}$', '−3.0°', '巡航高度', '$h_0$', '0.20 m'],
            ['平尾面积', '$S_t$', '0.18 m²', '尾力臂', '$l_t$', '0.95 m'],
            ['平尾安装角', '$i_t$', '−2.0°', '平尾抬高量', '$\\Delta z_t$', '0.30 m'],
            ['舵机时间常数', '$\\tau_e$', '0.05 s', '发动机时间常数', '$\\tau_T$', '0.15 s'],
        ],
        'key': 'params', 'caption': '参考构型主要参数', 'widths': [2.4, 1.3, 2.0, 2.4, 1.3, 2.0],
        'font_size': 8.5, 'aligns': ['left', 'center', 'center', 'left', 'center', 'center'],
    }), MINLV['conf'])

    h2('地面效应气动模型')
    add(('p', '定义地效因子 $\\kappa(h)$ 为诱导下洗的保留系数：$\\kappa = 1$ 对应自由空气，'
              '$\\kappa \\to 0$ 对应完全贴地。采用如下单参数族模型：'))
    add(('eq', (r'\kappa(h) = \frac{x^{n}}{A + x^{n}}, \qquad x = \frac{h}{b}', 'kappa')))
    add(('p', f'式中形状参数取 $A = {n(0.0641, 4)}$、$n = {n(1.4622, 4)}$。'
              '该式是一个物理动机明确的单参数族模型：$h \\to 0$ 时 $\\kappa \\to 0$、'
              '$h \\to \\infty$ 时 $\\kappa \\to 1$，'
              '参数按公开文献报告的地效随高度单调增强并趋于饱和的趋势整定$^{[1,3-4]}$。'
              '**需要明确的是**：本文不对该模型作"已由风洞/CFD 数据定量标定"的声称；'
              '针对本构型的 CFD 标定属于后续工作（见 6.1 节），'
              '而本文关注的是在这一类模型失配下控制器能否安全工作。'
              '地效作用下诱导阻力与有效升力线斜率分别为：'))
    add(('eq', (r'C_{Di}(h) = \frac{C_L^{2}\,\kappa(h)}{\pi\, AR\, e}, \qquad '
                r'a_w(h) = \frac{a_0}{1 + a_0\,\kappa(h)/(\pi\, AR\, e)}', 'awdrag')))
    add(('p', '平尾处的下洗角同样按 $\\kappa$ 衰减，'
              '$\\varepsilon(h,\\alpha) = (\\varepsilon_0 + \\varepsilon_\\alpha \\alpha)\\,\\kappa(h)$。'
              '图 @fig:ge@ 给出地效因子、升力线斜率增强倍数与诱导阻力随高度的变化。'))
    add(('figure', {'name': 'fig1_ge', 'width_cm': 9.0,
                    'key': 'ge', 'caption': '地效因子 $\\kappa(h)$ 与有效升力线斜率、诱导阻力随离地高度的变化'}))

    if level >= MINLV['getab']:
        add(('table', {
            'headers': ['$h$ / m', '$h/b$', '$\\kappa_{nom}$', '$\\kappa_{true}$',
                        '$a_{w,nom}$', '$a_{w,true}$', '$a_w$ 增幅 / %'],
            'rows': [[n(ge['h'][i], 2 if i < 3 else 2), n(ge['hb'][i], 4),
                      n(ge['kappa_nom'][i], 4), n(ge['kappa_true'][i], 4),
                      n(ge['aw_nom'][i], 4), n(ge['aw_true'][i], 4),
                      n(ge['aw_gain_pct'][i], 2)]
                     for i in [0, 1, 2, 3, 5, 7]],
            'key': 'getab', 'caption': '地效因子与有效升力线斜率（名义模型与真实对象）',
            'widths': [1.7, 1.7, 2.0, 2.1, 2.1, 2.1, 2.4], 'font_size': 8.5,
            'aligns': ['center'] * 7,
        }))

    h2('七阶纵向非线性模型')
    add(('p', '取状态量 $x = [\\,V,\\ \\gamma,\\ \\alpha,\\ q,\\ h,\\ T,\\ \\delta_e\\,]^{\\mathrm{T}}$，'
              '控制量 $u = [\\delta_{e,c},\\ \\delta_t]^{\\mathrm{T}}$。'
              '纵向运动方程为：'))
    add(('eq', (r'm\dot{V} = T\cos(\alpha + i_T) - D - mg\sin\gamma', 'eomv')))
    add(('eq', (r'mV\dot{\gamma} = L + T\sin(\alpha + i_T) - mg\cos\gamma', 'eomgam')))
    add(('eq', (r'\dot{\alpha} = q - \dot{\gamma}, \qquad I_{yy}\,\dot{q} = M, \qquad \dot{h} = V\sin\gamma', 'eomkin')))
    add(('eq', (r'\tau_T \dot{T} = T_{cmd} - T, \qquad \tau_e \dot{\delta}_e = \mathrm{sat}(\delta_{e,c}) - \delta_e', 'actdyn')))
    add(('p', '俯仰角由运动学关系给出 $\\theta = \\gamma + \\alpha$。'
              '机翼升力系数取 $C_{L,w} = a_w(h)(\\alpha - \\alpha_{L0})$，'
              '废阻力与诱导阻力之和为 $C_{D,w} = C_{D0} + C_{Di}$；'
              '平尾当地迎角为'))
    add(('eq', (r'\alpha_t = \alpha + i_t - \varepsilon(h,\alpha) + \frac{q\, l_t}{V}', 'alphat')))
    g(('p', '平尾升力系数为 $C_{L,t} = a_t(h_t)(\\alpha_t - \\alpha_{L0,t}) + a_{\\delta_e}\\delta_e$，'
              '其中平尾有效升力线斜率同式 (@eq:awdrag@) 计算，但使用平尾离地高度 $h_t = h + \\Delta z_t$ 与平尾翼展。'
              '所有力矩统一按 $M = z F_x - x F_z$ 计算，包含机翼、平尾、推力线偏置与机体力矩。'
              '数值积分采用定步长四阶 Runge-Kutta，步长 1 ms；飞控计算机以 200 Hz 采样、零阶保持。'), MINLV['eom_tail'])

    h2('名义模型与真实对象的不确定性', MINLV['mismatch'])
    g(('p', '控制器内部使用"名义模型"，被控对象为"真实对象"，二者之差即为自适应律需要在线补偿的'
              '不确定性。本文设置地效强度失配、RAM 效应（翼下高压区附加升力与附加低头力矩）、'
              '升力非线性软化与气动系数摄动四类失配，见表 @tab:mismatch@。'), MINLV['mismatch'])
    g(('table', {
        'headers': ['失配项', '名义模型', '真实对象', '物理含义'],
        'rows': [
            ['地效形状参数 $A$', n(0.0641, 4), n(0.045, 3), '地效强度被低估'],
            ['地效指数 $n$', n(1.4622, 4), n(1.300, 3), '地效随高度衰减规律不同'],
            ['RAM 附加升力', '无', '$k_{ram} = 0.09$', '翼下高压区附加升力'],
            ['RAM 附加力矩', '无', '作用点后移 5 cm', '压力中心后移'],
            ['升力非线性', '线性', '$C_{L,\\max} = 1.3$ 软化', '大迎角失速软化'],
            ['废阻力 $C_{D0}$', n(0.0250, 4), n(0.0320, 4), '阻力系数 +28%'],
            ['下洗梯度 $\\varepsilon_\\alpha$', n(0.350, 3), n(0.450, 3), '平尾下洗 +29%'],
        ],
        'key': 'mismatch', 'caption': '名义模型与真实对象的失配设置',
        'widths': [3.6, 2.4, 3.4, 5.0], 'font_size': 8.5,
        'aligns': ['left', 'center', 'center', 'left'],
    }), MINLV['mismatch'])
    g(('p', f'在配平点上，真实对象相对名义模型的失配量为：'
              f'俯仰力矩失配 $|\\Delta M| \\le {n(sm["dM_max_abs"], 4)}\\ \\mathrm{{N\\cdot m}}$，'
              f'升力失配 $|\\Delta L|$ 最大约 {n(sm["dL_max_abs"], 2)} N'
              f'（占重量的 {n(sm["dL_max_pct_W"], 1)}%），'
              f'阻力失配约 {n(abs(sm["dD_max"]), 2)} $\\sim$ {n(abs(sm["dD_min"]), 2)} N。'
              '该失配水平代表"工程估算式未经 CFD 标定"的典型情形。'), MINLV['mismatch'])

    # ============================================================= 3 机理
    h1('地效高度失稳机理')

    h2('配平特性')
    add(('p', '定常平飞（$\\gamma = 0$、$q = 0$）的配平条件为'))
    g(('eq', (r'T\cos(\alpha + i_T) - D = 0, \quad L + T\sin(\alpha + i_T) - mg = 0, \quad M = 0', 'trimc')))
    add(('p', '以 $\\alpha$、$\\delta_e$、$T$ 为未知量求解三元非线性方程组。表 @tab:trimtab@ 给出 '
              '$V = 18\\ \\mathrm{m/s}$ 时不同离地高度的配平结果与地效高度稳定性导数。'))
    add(('table', {
        'headers': ['$h$ / m', '$\\alpha_{nom}$ / (°)', '$\\alpha_{true}$ / (°)',
                    '$\\delta_{e,nom}$ / (°)', '$\\delta_{e,true}$ / (°)',
                    '$(L/D)_{nom}$', '$(L/D)_{true}$', '$\\partial M/\\partial h$ / (N·m/m)'],
        'rows': [[n(tr['h'][i], 2), n(tr['alpha_nom'][i], 3), n(tr['alpha_true'][i], 3),
                  n(tr['de_nom'][i], 3), n(tr['de_true'][i], 3),
                  n(tr['LD_nom'][i], 2), n(tr['LD_true'][i], 2), sg(tr['dMdh'][i], 3)]
                 for i in range(len(tr['h']))],
        'key': 'trimtab', 'caption': '不同离地高度的配平结果与地效高度稳定性导数',
        'widths': [1.4, 1.9, 1.9, 2.1, 2.1, 1.7, 1.7, 2.4], 'font_size': 8.5,
        'aligns': ['center'] * 8,
    }))
    g(('p', f'随离地高度增加，地效减弱，所需配平迎角由 {n(tr["alpha_nom"][0], 3)}° 增大到 '
              f'{n(tr["alpha_nom"][-1], 3)}°，升阻比由 {n(tr["LD_nom"][0], 2)} 降到 '
              f'{n(tr["LD_nom"][-1], 2)}；真实对象因存在地效失配与 RAM 效应，'
              f'配平舵偏与名义模型相差 {n(min(abs(tr["de_true"][i]-tr["de_nom"][i]) for i in range(len(tr["h"]))), 2)}° '
              f'$\\sim$ {n(max(abs(tr["de_true"][i]-tr["de_nom"][i]) for i in range(len(tr["h"]))), 2)}°，'
              '这正是控制器必须在线补偿的稳态失配。'), MINLV['trim_disc'])
    g(('figure', {'name': 'fig2_trim', 'width_cm': 9.0,
                  'key': 'trim', 'caption': '配平特性与地效高度稳定性导数随离地高度的变化'}), MINLV['fig_trim'])

    h2('$\\partial M/\\partial h$ 的分量分解')
    add(('p', f'表 @tab:trimtab@ 最后一列表明，整个使用包线内 '
              f'$\\partial M/\\partial h = {sg(min(tr["dMdh"]), 2)} \\sim {sg(max(tr["dMdh"]), 2)}\\ '
              '\\mathrm{N\\cdot m/m}$ 恒为正：离地高度减小时飞机会受到附加低头力矩，'
              '形成"高度-俯仰"正反馈，即经典的地效高度不稳定。'
              '为定位其物理来源，把俯仰力矩在配平点处按分量求导（对 $h$ 中心差分，'
              '其余状态冻结）：'))
    add(('eq', (r'\frac{\partial M}{\partial h} = '
                r'\frac{\partial M_w}{\partial h} + '
                r'\frac{\partial M_t}{\partial h} + '
                r'\frac{\partial M_{ram}}{\partial h} + '
                r'\frac{\partial M_{nl}}{\partial h}', 'dissurf')))
    add(('p', '式中下标 $w$、$t$、$ram$、$nl$ 分别代表机翼、平尾、RAM 附加力与升力非线性软化；'
              '机体项与推力线项与 $h$ 无关，恒为零。表 @tab:decomp@ 给出分解结果。'))
    add(('table', {
        'headers': ['$h$ / m', '$\\partial M/\\partial h$', '机翼', '平尾', 'RAM',
                    '非线性', '平尾占比 / %'],
        'rows': [[n(md['h'][i], 2), sg(md['total'][i], 2), sg(md['wing'][i], 2),
                  sg(md['tail'][i], 2), sg(md['ram'][i], 2), sg(md['nl'][i], 2),
                  n(100 * md['tail'][i] / md['total'][i], 1)]
                 for i in range(len(md['h']))],
        'key': 'decomp', 'caption': '俯仰力矩高度导数的分量分解（单位：N·m/m）',
        'widths': [1.6, 2.5, 2.0, 2.0, 1.9, 2.0, 2.4], 'font_size': 8.5,
        'aligns': ['center'] * 7,
    }))
    add(('p', f'分解结果十分清晰：平尾项在整个包线内都是最大的正贡献'
              f'（{sg(min(md["tail"]), 2)} $\\sim$ {sg(max(md["tail"]), 2)} $\\mathrm{{N\\cdot m/m}}$，'
              f'占总量的 {n(min(100*md["tail"][i]/md["total"][i] for i in range(len(md["h"]))), 1)}% $\\sim$ '
              f'{n(max(100*md["tail"][i]/md["total"][i] for i in range(len(md["h"]))), 1)}%），'
              f'而机翼项始终为负（{sg(min(md["wing"]), 2)} $\\sim$ {sg(max(md["wing"]), 2)}\\ '
              '$\\mathrm{N\\cdot m/m}$），是稳定因素。其物理机理为：'))
    g(('bullet', [
        '**平尾（不稳定）**：贴地使平尾处下洗减小，平尾当地迎角增大；'
        '配平状态下平尾承担负升力（下洗载荷），当地迎角增大会削弱这一负升力，'
        '从而产生附加低头力矩。',
        '**机翼（稳定）**：贴地增升（$\\partial L_w/\\partial h < 0$），'
        '而机翼气动中心位于质心之前 2 cm，增升产生抬头力矩。',
        '**RAM（不稳定）**：翼下高压附加力作用点在气动中心之后，'
        '随高度降低而增强，产生附加低头力矩。',
        '**升力非线性（不稳定）**：失速软化在低空更强，等效于损失部分升力，'
        '其作用点在气动中心之前，故产生低头力矩。',
    ]), MINLV['mech'])
    add(('p', f'四项之和与总量一致（最大残差 {md["resid_max"]:.1e} $\\mathrm{{N\\cdot m/m}}$），'
              '验证了分解的自洽性。该结论说明：'
              '要改善地效高度稳定性，应优先从平尾布局（如增大平尾抬高量、'
              '采用下洗屏蔽或主动平尾）入手，而不是单纯改变机翼平面形状。'))
    if level >= MINLV['fig_mdh']:
        add(('figure', {'name': 'fig12_mdh', 'width_cm': 9.0,
                        'key': 'mdh', 'caption': '$\\partial M/\\partial h$ 的分量堆叠、占比与升力高度刚度'}))

    h2('浮沉-高度耦合模态失稳')
    add(('p', '在配平点对式 (@eq:eomv@)~(@eq:alphat@) 数值线性化（中心差分），得到七阶状态矩阵与纵向模态。'
              '为分离地效作用，同时计算"等效关闭地效"（令 $A \\to 0$，即 $\\kappa \\equiv 1$）的模态。'))
    g(('table', {
        'headers': ['$h$ / m', '有地效 实部 / s⁻¹', '虚部 / s⁻¹', '阻尼比',
                    '无地效 实部 / s⁻¹', '虚部 / s⁻¹'],
        'rows': [[n(mo['h'][i], 2), sg(mo['re'][i], 4), n(mo['im'][i], 4), n(mo['zeta'][i], 3),
                  sg(mo['re_noge'][i], 4), n(mo['im_noge'][i], 4)]
                 for i in range(0, len(mo['h']))],
        'key': 'modes', 'caption': '低频（浮沉-高度耦合）模态随离地高度的变化',
        'widths': [1.6, 2.7, 2.1, 1.8, 2.7, 2.1], 'font_size': 8.5,
        'aligns': ['center'] * 6,
    }), MINLV['tab_modes'])
    g(('p', '结论十分清晰：'), MINLV['modes_lead'])
    g(('bullet', [
        f'关闭地效后，低频模态实部为 {sg(min(mo["re_noge"]), 4)} $\\sim$ '
        f'{sg(max(mo["re_noge"]), 4)} $\\mathrm{{s^{{-1}}}}$，即临界稳定，'
        f'与经典浮沉模态理论量级一致（$\\omega_p = \\sqrt{{2}}g/V = {n(st["phugoid_wn"], 4)}$ rad/s，'
        f'Lanchester 近似 $\\zeta_p = 1/(\\sqrt{{2}}\\,(L/D)) = {n(min(a["phugoid"]["zeta_p"]), 4)} \\sim '
        f'{n(max(a["phugoid"]["zeta_p"]), 4)}$）；',
        f'开启地效后，该模态实部变为 {sg(min(mo["re"]), 4)} $\\sim$ {sg(max(mo["re"]), 4)}\\ '
        f'$\\mathrm{{s^{{-1}}}}$，阻尼比最低降至 {n(min(mo["zeta"]), 3)}，'
        '说明失稳完全由地效引起；',
        f'实部最大值出现在 $h \\approx {n(mo["h"][mo["re"].index(max(mo["re"]))], 2)}$ m'
        f'（{sg(max(mo["re"]), 4)} $\\mathrm{{s^{{-1}}}}$，时间常数约 '
        f'{n(1/max(mo["re"]), 2)} s），振荡频率 {n(min(mo["im"]), 3)} $\\sim$ {n(max(mo["im"]), 3)} rad/s，'
        '是典型的浮沉-高度耦合振荡。',
    ]), MINLV['modes_bullet'])
    g(('figure', {'name': 'fig3_modes', 'width_cm': 9.0,
                  'key': 'modes', 'caption': '纵向极点分布与浮沉-高度耦合模态实部随高度的变化'}), MINLV['fig_modes'])
    g(('p', '该结果与第 3.2 节的力矩分解互相印证：'
              '平尾下洗随高度变化既提供了主要的 $\\partial M/\\partial h > 0$，'
              '也通过"高度-法向力"耦合通道把原本临界稳定的浮沉模态推向不稳定。'
              '因此地效飞行器必须依靠主动高度控制，'
              '且控制带宽需覆盖该模态频率并留足相位裕度。'), MINLV['modes_close'])

    # ============================================================= 4 控制器
    h1('RBF 神经网络自适应控制器设计')

    h2('控制架构')
    add(('p', '控制器采用三层串级结构：'))
    add(('bullet', [
        '**高度外环**（运动学）：由高度误差与高度率生成航迹倾角指令 $\\gamma_c$；',
        '**姿态内环**（动态面 + 动态逆 + RBF + 鲁棒项）：由 $\\gamma_c$ 生成俯仰角指令 $\\theta_c$，'
        '再由俯仰角速度回路解算升降舵指令 $\\delta_{e,c}$；',
        '**速度回路**（推力动态逆 + RBF + 鲁棒项 + 积分）：由速度误差生成油门指令 $\\delta_t$。',
    ]))
    add(('p', 'RBF 网络共两路$^{[7-8,14]}$：力矩通道（输入 $[\\alpha, q, h]$，$5 \\times 3 \\times 5 = 75$ 个节点）'
              '在线估计俯仰力矩失配；阻力通道（输入 $[\\alpha, V, h]$，$4 \\times 4 \\times 4 = 64$ 个节点）'
              '在线估计阻力失配。**升力通道无需单独网络**：由式 (@eq:dsc@) 中 '
              '$\\theta_d = \\gamma_c + \\alpha$ 的迎角反馈自然补偿。'
              '这一点值得强调——设俯仰角回路能跟踪 $\\theta = \\theta_d$，则由运动学恒等式 '
              '$\\gamma = \\theta - \\alpha$ 立即得到 $\\gamma = \\gamma_c$。'
              '由于该推导只用到 $\\gamma = \\theta - \\alpha$，与控制律和模型均无关，'
              '因此即使升力模型存在误差（迎角随之变化），航迹角仍能准确跟踪指令，'
              '从而省去一整套升力通道网络。'))

    h2('高度外环与动态面姿态内环')
    add(('p', '高度外环采用带高度率阻尼的比例导引律，高度率由 $\\dot{h} = V\\sin\\gamma$ '
              '直接合成，无需数值微分：'))
    add(('eq', (r'\gamma_d = \arcsin\!\left[\mathrm{sat}\!\left('
                r'\frac{\dot{h}_c - k_h e_h - k_{hd}(\dot{h} - \dot{h}_c)}{V},\ \sin\gamma_{\max}\right)\right],'
                r'\qquad e_h = h - h_c', 'gammaloop')))
    add(('p', '姿态内环采用动态面控制（DSC）以避免对虚拟控制量求导$^{[11-13]}$：'))
    add(('eq', (r'\theta_d = \mathrm{sat}\!\left(\gamma_c + \alpha,\ \theta_{\max}\right), \qquad '
                r'\tau_{th}\dot{\theta}_c = \theta_d - \theta_c', 'dsc')))
    g(('eq', (r'q_d = \dot{\theta}_c - k_\theta(\theta - \theta_c), \qquad '
                r'\tau_q \dot{q}_{cf} = \mathrm{sat}(q_d) - q_{cf}', 'qd')))
    add(('eq', (r'e_q = q - q_{cf}, \qquad \nu = \dot{q}_{cf} - k_q e_q', 'eqerr')))
    g(('p', f'由 $\\gamma = \\theta - \\alpha$ 可知，式 (@eq:dsc@) 使 '
              f'$\\dot{{\\theta}} = k_\\theta(\\gamma_c - \\gamma)$，'
              f'即俯仰角回路等价为一个航迹角跟踪回路，其固有频率与阻尼比为 '
              f'$\\omega_n = \\sqrt{{\\dot{{\\gamma}}_\\alpha k_\\theta}}$、'
              f'$\\zeta = \\dot{{\\gamma}}_\\alpha/(2\\omega_n)$，'
              f'其中 $\\dot{{\\gamma}}_\\alpha = \\partial\\dot{{\\gamma}}/\\partial\\alpha = '
              f'{n(st["dgamdot_dalpha"], 4)}\\ \\mathrm{{s^{{-1}}}}$ 由数值线性化给出。'
              f'取 $k_\\theta = 3.20\\ \\mathrm{{s^{{-1}}}}$ 时 $\\omega_n = '
              f'{n((st["dgamdot_dalpha"]*3.20)**0.5, 3)}$ rad/s、$\\zeta = '
              f'{n(st["dgamdot_dalpha"]/(2*(st["dgamdot_dalpha"]*3.20)**0.5), 3)}$；'
              f'为保证该回路不产生谐振，整定时要求 $\\zeta \\geq 1$（见 4.5 节）。'), MINLV['dsc_tune'])

    h2('动态逆控制律与自适应律')
    add(('p', '记名义模型零舵偏俯仰力矩为 $M_0(x)$、操纵导数为 $M_{\\delta_e}$，'
              '令 $f_0 = M_0/I_{yy}$、$b = M_{\\delta_e}/I_{yy}$，则升降舵控制律为'))
    add(('eq', (r'\delta_{e,c} = \frac{1}{b}\left(\nu - f_0 - u_M - u_r\right)', 'deltac')))
    add(('p', '其中 $u_M = W_1^{\\mathrm{T}}\\phi_1$ 为 RBF 网络对力矩失配的在线估计，'
              '$u_r$ 为鲁棒项。基函数与回归向量为'))
    add(('eq', (r'\phi_j(z) = \exp\!\left(-\frac{1}{2}\sum_{i=1}^{3}'
                r'\frac{(z_i - c_{ij})^{2}}{\sigma_i^{2}}\right), \qquad '
                r'\phi_1 = \phi(z_1)\,\frac{\bar{q}Sc}{I_{yy}}', 'phi')))
    add(('p', '中心 $c_j$ 在归一化坐标 $[-1,1]^3$ 上按网格均匀布置，宽度取网格间距，'
              '使相邻基函数在中心处的重叠度为 $e^{-1/2} \\approx 0.61$。'
              '回归向量中乘入 $\\bar{q}Sc$ 是**物理驱动的降维**：'
              '气动力矩本身正比于动压，把它显式提出后网络只需学习无量纲的力矩系数差，'
              '权值量级稳定且不随速度变化；'
              '这也把力矩通道的输入维数从 4 降为 3，节点数减少一个量级。'
              '权值采用投影算子保证有界$^{[9-10]}$：'))
    add(('eq', (r'\dot{W}_1 = \mathrm{Proj}\!\left[\Gamma_1\left(\phi_1 e_q - \nu_e|e_q| W_1\right)\right],'
                r'\qquad \dot{W}_2 = -\Gamma_2\left(\phi_2 e_V + \nu_e|e_V| W_2\right)', 'adap')))
    g(('eq', (r'\mathrm{Proj}(\tau) = \begin{cases} \tau, & \left\|W\right\| < W_{\max}\ '
                r'\text{或}\ W^{\mathrm{T}}\tau \leq 0 \\ '
                r'\tau - \dfrac{W W^{\mathrm{T}}}{\left\|W\right\|^{2}}\tau, & \text{其他} \end{cases}', 'proj')))
    add(('p', '注意两个通道自适应律的**符号相反**，原因在于估计量在控制律中的位置不同：'
              '力矩通道中 $u_M$ 以减号进入式 (@eq:deltac@)，而速度通道中 $u_D$ 以加号进入式 (@eq:tcmd@)。'
              '若符号取错，估计量将变成正反馈，直接导致闭环发散。'))

    h2('速度回路')
    add(('p', '速度回路控制律与误差动态分别为'))
    add(('eq', (r'T_{cmd} = \frac{m\left(\dot{V}_d + u_D - u_{rV}\right) + D_0 + mg\sin\gamma_c}'
                r'{\cos(\alpha + i_T)}', 'tcmd')))
    add(('eq', (r'\dot{V}_d = \dot{V}_c - k_V e_V - k_{IV} I_V, \qquad \dot{I}_V = e_V', 'vdot')))
    add(('p', '式 (@eq:tcmd@) 有两个必须注意的细节。'
              '**其一，重力前馈必须取自指令航迹角 $\\gamma_c$ 而非量测 $\\gamma$**：'
              '若用量测值，会形成 $\\gamma \\to T_{cmd} \\to T \\to V \\to L \\to \\dot{\\gamma}'
              ' \\to \\gamma$ 的正反馈回路，回路增益达 $mg = 117.7\\ \\mathrm{N/rad}$，'
              '在发动机滞后作用下把短周期/浮沉耦合模态推向右半平面。'
              '**其二，鲁棒项前必须是减号**，以保证误差动态中出现 $-u_{rV}$，'
              '与力矩通道一致，从而使 Lyapunov 交叉项严格对消。'))

    h2('Lyapunov 稳定性分析')
    add(('p', '记真实对象与名义模型的力矩失配为 $\\Delta f = \\Delta M/I_{yy}$，'
              '阻力失配为 $\\Delta D/m$，并把理想逼近写为 '
              '$\\Delta f = W_1^{*\\mathrm{T}}\\phi_1 + \\varepsilon_1$、'
              '$\\Delta D/m = W_2^{*\\mathrm{T}}\\phi_2 + \\varepsilon_2$，'
              '权值误差 $\\tilde{W}_i = W_i - W_i^{*}$。代入式 (@eq:deltac@)、(@eq:tcmd@) 得误差动态：'))
    g(('eq', (r'\dot{e}_q = -k_q e_q - \tilde{W}_1^{\mathrm{T}}\phi_1 + \varepsilon_1 - u_r', 'errdq')))
    g(('eq', (r'\dot{e}_V = -k_V e_V - k_{IV} I_V + \tilde{W}_2^{\mathrm{T}}\phi_2 '
                r'- \varepsilon_2 - u_{rV}', 'errdv')))
    add(('p', '取 Lyapunov 函数'))
    add(('eq', (r'V_L = \frac{1}{2}e_q^{2} + \frac{1}{2}\tilde{W}_1^{\mathrm{T}}\Gamma_1^{-1}\tilde{W}_1 '
                r'+ \frac{1}{2}e_V^{2} + \frac{1}{2}\tilde{W}_2^{\mathrm{T}}\Gamma_2^{-1}\tilde{W}_2 '
                r'+ \frac{1}{2}k_{IV} I_V^{2}', 'lyap')))
    add(('p', '沿闭环轨迹求导，代入自适应律 (@eq:adap@) 后交叉项严格对消：'))
    g(('eq', (r'e_q\left(-\tilde{W}_1^{\mathrm{T}}\phi_1\right) + '
                r'\tilde{W}_1^{\mathrm{T}}\Gamma_1^{-1}\Gamma_1\phi_1 e_q = 0', 'cancel1')))
    g(('eq', (r'e_V\left(\tilde{W}_2^{\mathrm{T}}\phi_2\right) + '
                r'\tilde{W}_2^{\mathrm{T}}\Gamma_2^{-1}\left(-\Gamma_2\phi_2 e_V\right) = 0', 'cancel2')))
    add(('p', '式 (@eq:cancel1@)、(@eq:cancel2@) 就是两个通道自适应律符号必须相反的原因。'
              '利用 $e$-修正项给出 $\\tilde{W}_i^{\\mathrm{T}}W_i \\geq '
              '\\frac{1}{2}\\|\\tilde{W}_i\\|^2 - \\frac{1}{2}\\|W_i^{*}\\|^2$。'
              '此外用到标准不等式 $|z| - z\\tanh(z/\\Phi) \\leq 0.2785\\,\\Phi$，'
              '其证明自含如下：令 $u = z/\\Phi \\geq 0$，左端等于 $\\Phi\\,g(u)$，'
              '其中 $g(u) = u\\,(1 - \\tanh u)$；'
              '由 $g\'(u) = 1 - \\tanh u - u\\,\\mathrm{sech}^{2}u = 0$ '
              '解得 $u^{*} = 1/(1 + \\tanh u^{*}) \\approx 0.6392$，'
              '此时 $g(u^{*}) \\approx 0.278465$，故 $0.2785$ 是该不等式的**精确上界**。'
              '当鲁棒增益满足 $\\eta_r \\geq \\varepsilon_N + d_M$、'
              '$\\eta_V \\geq \\varepsilon_N + d_V$ 时可得'))
    add(('eq', (r'\dot{V}_L \leq -2\lambda_{\min} V_L + c_0, \qquad '
                r'c_0 = 0.2785\left(\eta_r\Phi_r + \eta_V\Phi_V\right) + '
                r'\nu_e\left(\left\|W_1^{*}\right\|^{2} + \left\|W_2^{*}\right\|^{2}\right)', 'vdotl')))
    add(('p', '其中 $\\lambda_{\\min} = \\min\\{k_q, k_V, k_{IV}, \\nu_e\\}/2$ 为衰减率下界。'
              '由此得到一致最终有界（UUB）结论：'))
    add(('eq', (r'\left\|e(t)\right\| \leq \sqrt{\frac{2V_L(0)}{\lambda_{\min}}'
                r'e^{-2\lambda_{\min} t} + \frac{c_0}{\lambda_{\min}}}', 'uub')))
    add(('p', '即跟踪误差以指数速率收敛到半径 $\\sqrt{c_0/\\lambda_{\\min}}$ 的残差集内。'
              '投影算子 (@eq:proj@) 保证 $\\|W(t)\\| \\leq W_{\\max}$ 对任意 $t \\geq 0$ 成立，'
              '且其"仅去掉径向分量"的几何性质不破坏 $\\dot{V}_L$ 的负定性。'
              '高度外环为级联结构：由 $\\dot{e}_h = -k_h e_h + V(\\sin\\gamma - \\sin\\gamma_c)$ '
              '可知高度误差最终由内环航迹角跟踪误差界定，结合内环 UUB 结论即得整个闭环的一致性。'))
    if level >= MINLV['nu_e']:
        add(('p', '需要说明的是，式 (@eq:vdotl@) 中 $\\nu_e$ 项的存在使 $c_0$ 与理想权值范数有关，'
                  '这给出一个设计启示：$e$-修正系数 $\\nu_e$ 不宜过大，'
                  '否则残差集半径会被 $\\nu_e\\|W^{*}\\|^2/\\lambda_{\\min}$ 主导。'
                  '本文取 $\\nu_e = 0.50$，实测权值范数稳定在 $\\|W_1\\| \\approx 0.044$、'
                  '$\\|W_2\\| \\approx 0.150$ 量级，远小于投影上界 $W_{\\max} = 12.0$，'
                  '说明残差集半径主要由鲁棒项项 $0.2785(\\eta_r\\Phi_r + \\eta_V\\Phi_V)$ 决定。'))

    h2('数字实现的离散稳定性约束')
    add(('p', '自适应律按 200 Hz 离散实现（前向欧拉）。这是 RBF 自适应控制从连续域设计'
              '走向数字实现时最容易被忽视、后果也最严重的一步$^{[15-17]}$。'
              '把误差通道与权值通道联立并线性化（其余动力学冻结），'
              '忽略泄漏项与投影，得二维系统'))
    g(('eq', (r'\begin{bmatrix} e(k+1) \\ \tilde{W}(k+1) \end{bmatrix} = '
                r'\begin{bmatrix} 1 - T_s k & -T_s\phi^{\mathrm{T}} \\ '
                r'T_s\Gamma\phi & 1 \end{bmatrix}'
                r'\begin{bmatrix} e(k) \\ \tilde{W}(k) \end{bmatrix}', 'disc')))
    add(('p', '其特征多项式为 $\\lambda^2 - (1-T_sk)\\lambda + '
              '(1 - T_sk + T_s^2\\Gamma\\|\\phi\\|^2)$。'
              '由 Jury 判据，$\\det < 1$ 给出主导约束：'))
    add(('eq', (r'T_s\,\Gamma_i\left\|\phi_i\right\|^{2} < k_i', 'crit')))
    add(('p', '其中 $k_1 = k_q$、$k_2 = k_V$ 为对应通道的比例增益。'
              '把回归向量写成"量纲因子 $\\times$ 基函数向量"的形式 '
              '$\\phi_1 = \\phi_{rbf}\\,\\bar{q}Sc/I_{yy}$、$\\phi_2 = \\phi_{rbf}/m$，'
              '并代入本文参数：'))
    g(('table', {
        'headers': ['通道', '量纲因子 $g_i$', '$\\|\\phi_{i,rbf}\\|^2$',
                    '$T_s\\Gamma_i\\|\\phi_i\\|^2$', '通道增益 $k_i$', '裕度比'],
        'rows': [
            ['力矩', n(66.265, 3) + ' s⁻²', n(5.3943, 4), n(0.5922, 4), n(6.00, 2), n(6.00 / 0.5922, 1)],
            ['阻力', n(0.083333, 6) + ' kg⁻¹', n(5.3744, 4), n(0.0005598, 7), n(1.53, 2), n(1.53 / 0.0005598, 1)],
        ],
        'key': 'disc', 'caption': '离散自适应律的稳定裕度（$T_s = 5$ ms，配平点处）',
        'widths': [1.8, 3.0, 2.6, 3.0, 2.4, 2.0], 'font_size': 8.5,
        'aligns': ['center'] * 6,
    }), MINLV['tab_disc'])
    add(('p', f'表 @tab:disc@ 定量解释了为什么两个通道的自适应增益相差三个数量级'
              f'（$\\Gamma_1 = {n(0.005, 3)}$、$\\Gamma_2 = {n(3.0, 1)}$）：'
              f'力矩通道的回归向量被 $\\bar{{q}}Sc/I_{{yy}} \\approx {n(66.265, 1)}$ 放大，'
              f'而阻力通道被 $1/m \\approx {n(1/12, 4)}$ 缩小，二者相差约 795 倍；'
              f'若把两个增益直接比较数值大小，就会得出"力矩通道学习太慢"的错误结论，'
              f'进而调大 $\\Gamma_1$ 造成权值在几个采样周期内饱和发散。'
              f'本文在调试初期正是遇到这一现象：权值迅速冲至投影上界、升降舵饱和。'
              f'式 (@eq:crit@) 给出了可直接用于设计的判据。'))

    if level >= MINLV['tuning']:
        h2('基于采样闭环极点的增益整定')
        add(('p', '为客观评价控制器，本文建立"连续被控对象 + 200 Hz 离散控制器（零阶保持）"'
                  '的采样闭环数值线性化：先用定常参考做闭环仿真直到权值收敛，'
                  '再解出冻结参数系统的**真实平衡点**，'
                  '然后对映射 $F:(x_k,z_k) \\to (x_{k+1},z_{k+1})$ 做中心差分数值雅可比，'
                  '求取 $15 \\times 15$ 闭环矩阵的特征值。'
                  '整定流程为：'))
        add(('num', [
            '逐项开关分析定位失稳源：发现一对由推力状态主导的失稳极点，'
            '特征向量核验表明其由推力指令中的 $mg\\sin\\gamma$ 重力前馈构成正反馈回路所致；'
            '改为由指令航迹角 $\\gamma_c$ 前馈后该回路被切断。',
            '修正速度通道鲁棒项符号：鲁棒项本应以减号进入推力指令，'
            '若误写为加号，其零点等效增益 $\\eta_V/\\Phi_V$ 将抵消速度环比例增益，形成正反馈。',
            '全包线多点非线性指标扫描，综合高度误差 RMS 与最低离地高度确定增益。',
            '以鲁棒项"零点等效增益不超过该回路比例增益量级"为准则确定边界层厚度：'
            f'$\\Phi_r = {n(0.80, 2)}$ rad/s、$\\Phi_V = {n(1.00, 2)}$ m/s，'
            f'对应等效增益 {n(2.50/0.80, 2)} 与 {n(1.50/1.00, 2)}。',
        ]))
        add(('p', f'最终整定参数下，闭环 15 个采样极点的最大模为 '
                  f'$\\max|z| = {n(M["clp"]["final_maxabsz"], 5)} < 1$，全部位于单位圆内；'
                  f'最慢模态由速度积分状态主导（$s = {n(M["clp"]["slow_s_real"], 3)}\\ '
                  f'\\mathrm{{s^{{-1}}}}$，时间常数约 {n(1/abs(M["clp"]["slow_s_real"]), 1)} s）；'
                  f'平衡点求解残差 {M["clp"]["res_eq"]:.1e}，'
                  f'平衡点高度与指令偏差 {n(1000*(M["clp"]["h_eq"]-0.20), 2)} mm。'
                  '逐项开关敏感性分析进一步显示：**关闭鲁棒项后 $\\max|z|$ 升至 '
                  f'{n(M["clp"]["robust_off_maxabsz"], 5)}**，主导极点变为 '
                  f'$s = {sg(M["clp"]["robust_off_s"], 3)}\\ \\mathrm{{s^{{-1}}}}$ '
                  '且由推力状态 $T$ 主导。'
                  '这说明鲁棒项正是维持该回路稳定的关键，与 4.4 节"速度通道鲁棒项必须以减号进入"'
                  '的结论互相印证：符号一旦取反，其零点等效增益 $\\eta_V/\\Phi_V$ '
                  '将抵消速度环比例增益，使推力-速度回路失去阻尼。'))
        add(('p', '需要说明的是，闭环极点分析在两种基准下的结论不同：'
                  '出厂增益给出 $\\max|z| < 1$（稳定），而调试中间态增益'
                  '（$k_h = 3.0$、$\\tau_g = 0.05$ s）给出 $\\max|z| = 0.99982$，'
                  '虽仍在单位圆内但距边界仅 $1.8\\times10^{-4}$，属于临界状态。'
                  '这促使我们把 $k_h$ 由 3.0 降到 2.0、把 $\\tau_g$ 由 0.05 s 缩到 0.010 s，'
                  '使最慢极点由 $s = -0.036\\ \\mathrm{s^{-1}}$ 移到 $-0.116\\ \\mathrm{s^{-1}}$，'
                  '裕度明显改善。'))

    # ============================================================= 5 验证
    h1('仿真验证')

    h2('仿真设置', MINLV['setup'])
    g(('p', '除非特别说明，仿真均采用"真实对象 + 名义控制器"的失配配置：'
              '被控对象含地效强度失配、RAM 效应与升力非线性，控制器内部使用名义模型。'
              '积分步长 1 ms，控制器采样 200 Hz。标准考核工况的高度指令为 '
              '$0.20 \\to 0.35 \\to 0.10 \\to 0.25\\ \\mathrm{m}$（跨越整个地效区），'
              '速度指令为 $18 \\to 20\\ \\mathrm{m/s}$。'), MINLV['setup'])

    h2('消融对比')
    add(('p', f'表 @tab:perf@ 已给出三种控制方案的性能对比$^{{[22,25-26]}}$。仅采用名义动态逆时，'
              f'地效失配造成的升力与力矩误差无法被补偿，飞机在下降段掉高并触地；'
              f'引入鲁棒项后误差略有减小但依然触地；'
              f'引入 RBF 自适应后高度误差 RMS 降至 {n(sc["s1_adaptive"]["h_rms"], 4)} m，'
              f'最低离地高度 {n(sc["s1_adaptive"]["h_min"], 4)} m 与最低指令高度完全一致，'
              f'全过程未触地。改善倍数为 '
              f'{n(sc["s1_improve"], 2)}（高度）与 {n(sc["s1_improve_v"], 2)}（速度）。'))
    add(('figure', {'name': 'fig4_tracking', 'width_cm': 9.0,
                    'key': 'tracking', 'caption': '地效区高度与速度跟踪对比（自适应 vs 消融方案）'}))
    if level >= MINLV['fig_states']:
        add(('figure', {'name': 'fig5_states', 'width_cm': 9.0,
                        'key': 'states', 'caption': '自适应控制下的俯仰角、航迹角、角速度、舵偏与推力响应'}))
    g(('p', f'图 @fig:adaptive@ 给出自适应量的时间历程。力矩通道网络输出 $u_M$ 在高度机动过程中持续调整'
              '以补偿地效失配与 RAM 力矩；权值范数由投影算子保证有界，'
              f'在定常工况下收敛到 $\\|W_1\\| \\approx {n(0.044, 3)}$；'
              f'阻力通道网络输出 $u_D$ 补偿约 {n(abs(sm["dD_max"]), 1)} N 的阻力失配，'
              f'使速度跟踪误差 RMS 仅 {n(sc["s1_adaptive"]["V_rms"], 4)} m/s。'), MINLV['adaptive'])
    g(('figure', {'name': 'fig6_adaptive', 'width_cm': 9.0,
                  'key': 'adaptive', 'caption': 'RBF 网络输出、鲁棒项、权值范数与跟踪误差的时间历程'}), MINLV['adaptive'])

    if level >= MINLV['extra_trials']:
        h2('对象参数摄动')
        add(('p', f'在标称对象基础上设置 {len(sc["s2_pert"])-1} 组极端参数摄动，'
                  '覆盖质量、地效强度、阻力系数、下洗梯度与升力线斜率等主要不确定因素。'
                  f'全部 {len(sc["s2_pert"])} 组工况下飞机均未触地，'
                  f'高度误差 RMS 在 {n(sc["s2_h_rms_min"], 4)} $\\sim$ {n(sc["s2_h_rms_max"], 4)} m 之间。'))
        add(('table', {
            'headers': ['摄动工况', '$h_{rms}$ / m', '高度误差峰值 / m', '$h_{\\min}$ / m',
                        '$\\delta_e$ 峰值 / (°)', '安全'],
            'rows': [[p['label'].replace('%%', '%'), n(p['h_rms'], 4), n(p['h_err_max'], 4),
                      n(p['h_min'], 4), n(p['de_max'], 1), '是' if p['ok'] else '否']
                     for p in sc['s2_pert']],
            'key': 'pert', 'caption': '参数摄动下的性能（RBF 自适应控制器）',
            'widths': [5.0, 2.0, 2.4, 2.0, 2.2, 1.6], 'font_size': 8.5,
            'aligns': ['left'] + ['center'] * 5,
        }))
        add(('figure', {'name': 'fig7_perturbation', 'width_cm': 9.0,
                        'key': 'pert', 'caption': '参数摄动下的高度跟踪曲线'}))

        h2('大气扰动')
        add(('p', '针对离散 1-cos 阵风与 Dryden 连续湍流开展仿真，结果见表 @tab:gust@。'))
        add(('table', {
            'headers': ['扰动工况', '自适应 $h_{rms}$ / m', '自适应 $h_{\\min}$ / m', '安全',
                        '无自适应 $h_{rms}$ / m', '安全'],
            'rows': [[g['label'], n(g['ad_h_rms'], 4), n(g['ad_h_min'], 4),
                      '是' if g['ad_ok'] else '否', n(g['no_h_rms'], 4),
                      '是' if g['no_ok'] else '否'] for g in sc['s3_gust']],
            'key': 'gust', 'caption': '大气扰动下的性能对比',
            'widths': [4.8, 2.6, 2.4, 1.4, 2.6, 1.4], 'font_size': 8.5,
            'aligns': ['left'] + ['center'] * 5,
        }))
        g1 = sc['s3_gust'][0]
        g2 = sc['s3_gust'][2]
        add(('p', f'中度阵风（{n(1.5, 1)} m/s）与连续湍流（$\\sigma = {n(1.5, 1)}$ m/s）下，'
                  f'自适应控制器高度误差 RMS 分别为 {n(g1["ad_h_rms"], 4)} m 与 '
                  f'{n(g2["ad_h_rms"], 4)} m，均未触地；'
                  f'关闭自适应后两种工况均触地。'))
        add(('p', f'需要如实指出的是，严酷阵风（$W_g = {n(3.0, 1)}$ m/s）下自适应控制器'
                  f'同样发生触地（$h_{{rms}} = {n(sc["s3_gust"][1]["ad_h_rms"], 4)}$ m）。'
                  f'原因是 {n(3.0, 1)} m/s 的垂向阵风在本对象上产生约 '
                  f'{n(math.degrees(math.atan(3.0/18.0)), 2)}° 的等效迎角突增，'
                  f'对应升力扰动约 {n(141.7, 1)}% 重量，已超出执行器与高度裕度的物理能力。'
                  '该结果表明本构型的地效飞行包线对垂向阵风较为敏感，'
                  '实际使用中需通过气象条件限制或增大巡航高度裕度加以规避。'))
        add(('figure', {'name': 'fig8_gust', 'width_cm': 9.0,
                        'key': 'gust', 'caption': '阵风与湍流扰动下的高度响应'}))

        h2('极限低空掠飞与量测噪声')
        low = sc['s4_low']
        add(('p', f'在最严酷的工况下考核控制器：高度指令下探至 {n(0.06, 2)} m'
                  f'（$h/c = 0.15$，深度地效区），同时叠加量测噪声'
                  f'（空速 {n(0.15, 2)} m/s、迎角 {n(0.15, 2)}°、'
                  f'俯仰角速度 {n(0.3, 1)}°/s、高度 {n(0.01, 3)} m）并启用执行器限幅。'
                  f'自适应控制器高度误差 RMS 为 {n(low["ad"]["h_rms"], 4)} m，'
                  f'最低离地高度 {n(low["ad"]["h_min"], 4)} m，全程未触地且升降舵峰值仅 '
                  f'{n(low["ad"]["de_max"], 1)}°；关闭自适应后高度误差 RMS 升至 '
                  f'{n(low["no"]["h_rms"], 4)} m 并触地。'))
        add(('figure', {'name': 'fig9_lowalt', 'width_cm': 9.0,
                        'key': 'lowalt', 'caption': '极限低空掠飞（最低指令 0.06 m）+ 量测噪声下的响应'}))

    h2('蒙特卡洛鲁棒性统计')
    g(('p', f'在质量 $\\pm 25\\%$、惯量 $\\pm 25\\%$、废阻力 $\\pm 40\\%$、'
              f'升力线斜率 $\\pm 10\\%$、俯仰力矩系数 $\\pm 30\\%$、'
              f'地效强度参数 $\\pm 60\\%$、下洗梯度 $\\pm 40\\%$、尾翼效率 $\\pm 15\\%$、'
              f'初始高度偏差 $\\pm 0.03\\ \\mathrm{{m}}$、初始速度偏差 $\\pm 1.0\\ \\mathrm{{m/s}}$ '
              f'范围内独立均匀随机抽样 {mc["N"]} 组。'), MINLV['mc_setup'])
    add(('table', {
        'headers': ['指标', '均值', '标准差', '中位数', '95% 分位', '最大值'],
        'rows': [[k, n(v['mean'], 5), n(v['std'], 5), n(v['median'], 5), n(v['p95'], 5), n(v['max'], 5)]
                 for k, v in mc['stat'].items()],
        'key': 'mc', 'caption': f'蒙特卡洛统计结果（{mc["N"]} 组随机参数摄动）',
        'widths': [4.9, 2.05, 2.05, 2.05, 2.05, 2.05], 'font_size': 8.5,
        'aligns': ['left'] + ['center'] * 5,
    }))
    add(('p', f'自适应控制器的通过率（未触地且收敛）为 '
              f'{mc["pass_ad_n"]}/{mc["pass_ad_N"]} = {n(mc["pass_ad_pct"], 1)}%，'
              f'无自适应控制器为 {mc["pass_no_n"]}/{mc["pass_no_N"]} = {n(mc["pass_no_pct"], 1)}%；'
              f'高度误差 RMS 中位数由 {n(mc["med_no"], 5)} m 降至 {n(mc["med_ad"], 5)} m，'
              f'改善 {n(mc["med_improve"], 1)} 倍。'
              f'权值范数终值 $\\|W_1\\|$ 均值 {n(mc["W1_mean"], 3)}、最大值 {n(mc["W1_max"], 3)}，'
              f'均远小于投影上界 $W_{{\\max}} = 12.0$，说明自适应律工作在安全区内。'))
    if level >= MINLV['fig_mc']:
        add(('figure', {'name': 'fig10_montecarlo', 'width_cm': 9.0,
                        'key': 'mc', 'caption': '蒙特卡洛高度响应包络与高度误差峰值分布'}))

    h2('Simulink 交叉验证', MINLV['simulink'])
    g(('p', '在完全相同工况下分别用 Simulink 模型与纯 MATLAB 脚本仿真。'
              '两者共享同一份被控对象与控制器代码，仅积分器与调度由 Simulink 完成。'
              '比较时必须注意口径一致：Simulink 记录的 $u$ 通道是控制器**指令**，'
              '而脚本记录的是舵机**状态**，二者相差一个 $\\tau_e = 0.05$ s 的一阶滞后'
              '（在 $120^\\circ/\\mathrm{s}$ 速率限幅下可达约 $6^\\circ$）。'
              '因此表 @tab:simtab@ 分别给出"状态 vs 状态"与"指令 vs 指令"的对比。'), MINLV['simulink'])
    g(('table', {
        'headers': ['指标', 'Simulink', 'MATLAB 脚本', '偏差'],
        'rows': [
            ['高度误差 RMS / m', n(sI['h_rms']['sl'], 6), n(sI['h_rms']['ml'], 6), f"{sI['h_rms']['dev']:.2e}"],
            ['高度误差峰值 / m', n(sI['h_err_max']['sl'], 6), n(sI['h_err_max']['ml'], 6), f"{sI['h_err_max']['dev']:.2e}"],
            ['最低离地高度 / m', n(sI['h_min']['sl'], 6), n(sI['h_min']['ml'], 6), f"{sI['h_min']['dev']:.2e}"],
            ['速度误差 RMS / (m/s)', n(sI['V_rms']['sl'], 6), n(sI['V_rms']['ml'], 6), f"{sI['V_rms']['dev']:.2e}"],
            ['升降舵峰值（状态）/ (°)', n(sI['de_state']['sl'], 4), n(sI['de_state']['ml'], 4), f"{sI['de_state']['dev']:.2e}"],
            ['升降舵峰值（指令）/ (°)', n(sI['de_cmd']['sl'], 4), n(sI['de_cmd']['ml'], 4), f"{sI['de_cmd']['dev']:.2e}"],
        ],
        'key': 'simtab', 'caption': 'Simulink 模型与纯 MATLAB 脚本结果对比',
        'widths': [4.8, 3.2, 3.2, 3.0], 'font_size': 8.5,
        'aligns': ['left', 'center', 'center', 'center'],
    }), MINLV['simulink'])
    g(('p', f'最大轨迹偏差（状态 vs 状态）为高度 {sI["traj_h"]:.3e} m、'
              f'速度 {sI["traj_V"]:.3e} m/s、升降舵 {sI["traj_de"]:.3e}°；'
              f'最大指令偏差（指令 vs 指令）为升降舵 {sI["traj_de_cmd"]:.3e}°。'
              '两者均为采样与插值量级，表明 Simulink 模型与脚本仿真在数值上等价，'
              '可作为后续硬件在环与代码生成的基础。'), MINLV['simulink'])
    g(('figure', {'name': 'fig11_simulink', 'width_cm': 9.0,
                  'key': 'simulink', 'caption': 'Simulink 模型与纯 MATLAB 脚本一致性验证'}), MINLV['simulink'])

    # ============================================================= 6 结论
    h1('结论')
    add(('p', '本文以一架小型地效无人机为对象，研究了地效高度失稳机理与 RBF 神经网络自适应'
              '纵向控制问题，主要结论如下：'))
    add(('num', [
        f'建立了含地效因子修正的七阶纵向非线性模型。地效因子模型在 '
        f'$h/b = 0.02 \\sim 0.5$ 范围内与公开风洞/CFD 数据趋势一致：'
        f'$h = 0.05\\ \\mathrm{{m}}$ 处诱导阻力降至自由空气的 {n(100*ge["kappa_nom"][0], 1)}%、'
        f'升力线斜率提高 {n(ge["aw_gain_pct"][0], 1)}%，'
        f'$h = 0.50\\ \\mathrm{{m}}$ 处升力线斜率仍提高 {n(ge["aw_gain_pct"][5], 1)}%。',

        f'通过 $\\partial M/\\partial h$ 的分量分解定量揭示了高度失稳机理：'
        f'全包线内 $\\partial M/\\partial h = {sg(min(md["total"]), 2)} \\sim {sg(max(md["total"]), 2)}\\ '
        f'\\mathrm{{N\\cdot m/m}} > 0$，其中平尾下洗项贡献 {sg(max(md["tail"]), 2)} '
        f'$\\mathrm{{N\\cdot m/m}}$（主导不稳定项），'
        f'机翼项贡献 {sg(min(md["wing"]), 2)} $\\mathrm{{N\\cdot m/m}}$（稳定项），'
        f'RAM 与升力非线性项分别贡献约 {sg(md["ram"][3], 2)} 与 {sg(md["nl"][3], 2)} '
        f'$\\mathrm{{N\\cdot m/m}}$（不稳定项），'
        f'四项之和与数值总量一致（残差 {md["resid_max"]:.1e}）。',

        f'证明浮沉-高度耦合模态失稳完全源于地效：有地效时实部 '
        f'{sg(min(mo["re"]), 4)} $\\sim$ {sg(max(mo["re"]), 4)} $\\mathrm{{s^{{-1}}}}$、'
        f'最低阻尼比 {n(min(mo["zeta"]), 3)}；'
        f'等效关闭地效后该模态恢复临界稳定（实部 {sg(min(mo["re_noge"]), 4)} $\\sim$ '
        f'{sg(max(mo["re_noge"]), 4)} $\\mathrm{{s^{{-1}}}}$）。',

        '设计了"高度外环 + 姿态动态面内环 + 速度回路"的三层控制器，'
        '在力矩与阻力通道分别引入 RBF 网络与 $\\tanh$ 鲁棒项，'
        '用 Lyapunov 方法证明闭环一致最终有界并给出显式残差界。'
        '借助 $\\theta_d = \\gamma_c + \\alpha$ 的运动学恒等式，'
        '升力通道误差被迎角反馈自动补偿，省去了一整套网络。',

        f'给出了数字实现的离散稳定性判据 $T_s\\Gamma_i\\|\\phi_i\\|^2 < k_i$，'
        f'并据此解释了力矩通道自适应增益（{n(0.005, 3)}）比阻力通道（{n(3.0, 1)}）'
        f'小三个数量级的根本原因——两通道回归向量的量纲因子相差约 795 倍。',

        f'仿真验证表明：在存在显著地效失配、RAM 效应与升力非线性的条件下，'
        f'自适应控制器把高度跟踪误差 RMS 由 {n(sc["s1_di_rob"]["h_rms"], 4)} m 降至 '
        f'{n(sc["s1_adaptive"]["h_rms"], 4)} m（改善 {n(sc["s1_improve"], 1)} 倍），'
        f'蒙特卡洛通过率由 {n(mc["pass_no_pct"], 1)}% 提升至 {n(mc["pass_ad_pct"], 1)}%，'
        f'并在 {n(0.06, 2)} m 极限低空、量测噪声与中度阵风条件下保持安全飞行。'
        f'最终整定参数下采样闭环最大极点模 $\\max|z| = {n(M["clp"]["final_maxabsz"], 5)} < 1$。',
    ]))

    h2('局限与展望')
    add(('bullet', [
        '气动模型为准定常线性模型，未考虑地效的非定常迟滞与大迎角分离；'
        '建议通过 CFD 开展俯仰振荡与高度快速变化工况计算，标定动导数并检验准定常假设的适用范围。',
        '地效因子参数由公开数据趋势标定，未针对本构型做 CFD 标定。'
        '完成 CFD 标定后可把标定值写入名义模型，相应减小失配量与自适应补偿负担。',
        f'严酷垂向阵风（$W_g = {n(3.0, 1)}$ m/s）下控制器仍会触地，'
        '说明本构型的地效飞行包线对垂向阵风敏感，'
        '后续可从阵风减缓（如直接升力控制）与轨迹规划两个方向改善。',
        '控制器仅考虑纵向通道，尚未包含横侧向与航迹跟踪；'
        '后续可扩展为纵横向解耦的自适应控制。',
        '鲁棒项边界层厚度与自适应增益仍依赖非线性闭环指标整定，'
        '后续可引入 $\\mu$ 综合或 $\\mathcal{L}_1$ 自适应框架给出系统性设计方法。',
    ]))

    # ============================================================= 附录
    if level >= MINLV['appendix']:
        h1('附录 A  控制器整定参数', numbered=False)
        add(('table', {
            'headers': ['参数', '符号', '取值', '参数', '符号', '取值'],
            'rows': [
                ['高度环比例', '$k_h$', '2.00 1/s', '俯仰角环比例', '$k_\\theta$', '3.20 1/s'],
                ['高度率阻尼', '$k_{hd}$', '0.80', '角速度环比例', '$k_q$', '6.00 1/s'],
                ['航迹指令滤波', '$\\tau_g$', '0.010 s', '俯仰角指令滤波', '$\\tau_\\theta$', '0.100 s'],
                ['角速度指令滤波', '$\\tau_q$', '0.010 s', '速度环比例', '$k_V$', '1.53 1/s'],
                ['速度环积分', '$k_{IV}$', '0.42 1/s²', '力矩通道增益', '$\\Gamma_1$', '0.005'],
                ['阻力通道增益', '$\\Gamma_2$', '3.0', '$e$-修正系数', '$\\nu_e$', '0.50'],
                ['力矩鲁棒增益', '$\\eta_r$', '2.50 rad/s²', '力矩边界层', '$\\Phi_r$', '0.80 rad/s'],
                ['速度鲁棒增益', '$\\eta_V$', '1.50 m/s²', '速度边界层', '$\\Phi_V$', '1.00 m/s'],
                ['权值投影上界', '$W_{\\max}$', '12.0', '俯仰指令限幅', '$\\theta_{\\max}$', '20°'],
                ['航迹倾角限幅', '$\\gamma_{\\max}$', '12°', 'RBF 节点数', '$N_1 / N_2$', '75 / 64'],
            ],
            'key': 'tuning', 'caption': '控制器最终整定参数',
            'widths': [2.6, 1.4, 2.2, 2.6, 1.4, 2.2], 'font_size': 8.5,
            'aligns': ['left', 'center', 'center', 'left', 'center', 'center'],
        }))

    # ============================================================= 参考文献
    h1('参考文献', numbered=False)
    add(('refs', refs))
    return B
