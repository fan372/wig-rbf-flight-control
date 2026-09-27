# -*- coding: utf-8 -*-
"""content_en.py —— 英文 IEEE 会议论文内容（与 content_zh.py 同源同数）。

所有数值一律从 metrics.json 读取。结构与中文版逐块对应，保证两版结论一致。
"""
from __future__ import annotations

import math

TITLE_EN = ('RBF Neural-Network Adaptive Longitudinal Flight Control of a '
            'Wing-in-Ground-Effect UAV: Height-Instability Mechanism and Simulation Validation')
KEYWORDS_EN = ('wing-in-ground effect; flight control; RBF neural network; adaptive control; '
               'dynamic surface control; height stability')


# ---------------------------------------------------------------- 日志中文标签 -> 英文
# results/log_*.txt 里的摄动工况名、扰动工况名与蒙特卡洛指标名是中文的。
# 英文论文的表格不能直接照搬，否则 pdfLaTeX 无法排版（Unicode character not set up），
# 表格首列会变成空白。这里做一次显式映射；任何未映射的中文标签都会**报错**而不是漏出去。
_LABELS = {
    # 场景 2：对象参数摄动
    '标称对象': 'Nominal plant',
    '质量 m ×1.25、Iyy ×1.26': 'Mass $m$ x1.25, $I_{yy}$ x1.26',
    '质量 m ×0.85、Iyy ×0.826': 'Mass $m$ x0.85, $I_{yy}$ x0.826',
    '地效形状参数 A ×0.312（地效增强）': 'GE shape parameter $A$ x0.312 (stronger GE)',
    '地效形状参数 A ×1.404（地效减弱）': 'GE shape parameter $A$ x1.404 (weaker GE)',
    '废阻力 CD0/CD0t ×1.80（+80%）': 'Parasite drag $C_{D0}/C_{D0t}$ x1.80 (+80%)',
    '下洗梯度 eps_a ×1.94（+94%）': 'Downwash gradient $\\varepsilon_\\alpha$ x1.94 (+94%)',
    '升力线斜率 a0 ×0.881、尾翼效率 eta_t ×0.842':
        'Lift slope $a_0$ x0.881, tail efficiency $\\eta_t$ x0.842',
    # 场景 3：大气扰动
    '离散 1-cos 阵风 1.5 m/s（中度）': 'Discrete 1-cos gust, 1.5 m/s (moderate)',
    '离散 1-cos 阵风 3.0 m/s（严酷）': 'Discrete 1-cos gust, 3.0 m/s (severe)',
    'Dryden 连续湍流 \\sigma=1.5 m/s': 'Dryden continuous turbulence, $\\sigma$ = 1.5 m/s',
    # 蒙特卡洛统计指标
    '高度误差 RMS [m]': 'Height RMS error / m',
    '高度误差 峰值 [m]': 'Peak height error / m',
    '最低离地高度 [m]': 'Minimum height above ground / m',
    '速度误差 峰值 [m/s]': 'Peak airspeed error / (m/s)',
}


def lab(s: str) -> str:
    """把日志里的中文标签翻成英文；未映射的中文一律报错，绝不让 CJK 进入 pdfLaTeX。"""
    key = s.replace('%%', '%')
    if key in _LABELS:
        return _LABELS[key]
    if any('\u4e00' <= ch <= '\u9fff' for ch in key):
        raise KeyError(
            f'英文论文中出现未映射的中文标签：{key!r}。'
            f'请在 content_en._LABELS 中补充对应英文后再生成。')
    return key


def n(x, d=2):
    return f'{float(x):.{d}f}'


def sg(x, d=2):
    return f'{float(x):+.{d}f}'


def abstract(M):
    sc = M['scenarios']
    mc = M['montecarlo']
    md = M['mdh']
    mo = M['analysis']['modes']
    return (
        'Small wing-in-ground-effect (WIG) vehicles operate entirely inside the strong '
        'ground-effect regime, where the aerodynamics vary sharply with height and the '
        'longitudinal dynamics exhibit two stability problems absent in conventional aircraft. '
        'This paper studies a WIG UAV of 2.40 m span and 12.0 kg mass cruising at 18 m/s at '
        'heights between 0.05 m and 0.50 m. A seventh-order nonlinear longitudinal model with a '
        'ground-effect correction is established. Two results are established quantitatively. '
        'First, the pitch-moment height derivative is strictly positive throughout the envelope, '
        f'from {sg(min(md["total"]), 2)} to {sg(max(md["total"]), 2)} N$\\cdot$m/m, so the height '
        'static stability is negative; a component-wise decomposition shows that the tail '
        f'downwash term dominates ({sg(max(md["tail"]), 2)} N$\\cdot$m/m) while the wing provides '
        f'a stabilising contribution ({sg(min(md["wing"]), 2)} N$\\cdot$m/m). Second, the '
        f'phugoid-height coupled mode becomes unstable, with real part up to '
        f'{sg(max(mo["re"]), 4)} 1/s, whereas switching the ground effect off returns the mode to '
        'neutral stability, proving that the instability is of ground-effect origin. '
        'A three-loop controller is then designed, comprising an altitude outer loop, a '
        'dynamic-surface attitude inner loop and an airspeed loop, with two RBF networks and '
        'tanh robust terms acting in the moment and drag channels. Closed-loop uniform ultimate '
        'boundedness is proved by a Lyapunov argument. A discrete-time design constraint, '
        '$T_s\\Gamma_i\\|\\phi_i\\|^2 < k_i$, is further derived; it explains why the '
        'moment-channel adaptation gain must be three orders of magnitude smaller than the '
        'drag-channel gain. Simulations with significant ground-effect mismatch, RAM effect and '
        'lift nonlinearity show that the height-tracking RMS error is reduced from '
        f'{n(sc["s1_di_rob"]["h_rms"], 4)} m to {n(sc["s1_adaptive"]["h_rms"], 4)} m '
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


def build(level, M, refs):
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
        """Include a block only when level >= minlv (6 = all versions)."""
        if level >= minlv:
            B.append(block)

    # Section letters are derived from what is actually included, so moving a
    # block between length versions never leaves a gap in the numbering.
    num = {'sub': 0}

    def h1(text):
        num['sub'] = 0
        B.append(('h1', text))

    def h2(text, minlv=6):
        if level < minlv:
            return
        num['sub'] += 1
        B.append(('h2', f'{chr(ord("A") + num["sub"] - 1)}.  {text}'))

    # ============================================================ 1
    h1('Introduction')
    add(('p', 'A wing-in-ground-effect (WIG) vehicle exploits the suppression of downwash by the '
              'ground image vortex system when flying close to the ground or sea surface, '
              'obtaining a substantially increased lift-curve slope and a sharply reduced induced '
              'drag, and hence a lift-to-drag ratio far above that of a conventional aircraft '
              '[1], [2]. Small WIG unmanned aerial vehicles have a short span and a low cruising '
              'height, so their entire operating envelope lies inside the strong ground-effect '
              'regime. For the configuration studied here, at $h = 0.05$ m the induced drag is '
              f'only {n(100*ge["kappa_nom"][0], 1)}% of its free-air value and the lift-curve slope '
              f'is {n(ge["aw_gain_pct"][0], 1)}% higher; even at $h = 0.50$ m the lift-curve slope '
              f'is still {n(ge["aw_gain_pct"][5], 1)}% higher. This height-dependent aerodynamics '
              'makes the flight control problem fundamentally different from that of a '
              'conventional aircraft.'))
    add(('p', 'The difficulty concentrates in two points. The first is negative height static '
              'stability. As early as the 1970s Irodov pointed out that the height-stability '
              'criterion for a WIG vehicle requires $\\partial C_m/\\partial h < 0$, which most '
              'WIG configurations do not satisfy [3]. The decomposition given in Section III '
              'shows that for the present configuration '
              f'$\\partial M/\\partial h = {sg(min(md["total"]), 2)}$ to '
              f'{sg(max(md["total"]), 2)} N$\\cdot$m/m over the whole envelope. The second is '
              'the instability of the phugoid-height coupled mode: the ground effect turns the '
              'classically neutrally stable phugoid mode into an unstable one, with the real part '
              f'of the low-frequency mode reaching {sg(max(mo["re"]), 4)} 1/s. Together these two '
              'facts make an actively controlled altitude loop with sufficient bandwidth '
              'mandatory [5], [6], [18]-[21], [23], [24].'))

    if level >= MINLV['related']:
        h2('Related Work')
        add(('p', 'For aerodynamic modelling, quasi-steady ground effect is usually represented '
                  'by a downwash-retention factor that measures how strongly the image vortex '
                  'system suppresses the downwash, and which then corrects the induced drag and '
                  'the effective lift-curve slope [1], [6]. Wind-tunnel and CFD studies agree '
                  'that ground effect raises the lift-curve slope and lowers the induced drag '
                  'substantially, and that it shifts the height focus, thereby degrading '
                  'longitudinal static stability; the stability criteria for a WIG vehicle '
                  'therefore differ from those of a conventional aircraft and must be satisfied '
                  'for both the angle-of-attack focus and the height focus '
                  '[3]-[5], [18]-[21], [23], [24]. '
                  'On the control side, RBF neural networks are widely used for direct adaptive '
                  'control of uncertain nonlinear systems because of their universal '
                  'approximation property and linearly parameterised weights; the Lyapunov '
                  'framework was established by Sanner and Slotine [7], by Polycarpou [8] and '
                  'by Ge and Wang [14]. '
                  'Robust terms commonly use a tanh saturation function to smooth the sign '
                  'function, a smoothing idea that is widespread in robust adaptive design '
                  '[9], [10]; the projection operator used to guarantee uniformly bounded '
                  'weights is due to Ioannou and Sun [10]. For backstepping implementations, '
                  'dynamic surface control (DSC) and command-filtered backstepping avoid the '
                  'analytic differentiation of virtual controls through first- or second-order '
                  'filters, removing the "explosion of terms" [11]-[13]. The framework has '
                  'recently been extended to the longitudinal control of vehicles with wide '
                  'flight envelopes [22], [26].'))
        add(('p', 'However, most published work on adaptive control of WIG vehicles, including '
                  'active-disturbance-rejection and stability-augmentation designs [25], validates '
                  'the design against the nominal plant and rarely discusses '
                  'the stability constraint that appears when an RBF adaptation law designed in '
                  'continuous time is implemented digitally. That continuous-time adaptation laws '
                  'can lose robustness in the presence of unmodelled dynamics was demonstrated '
                  'long ago by the Rohrs counterexample [15], and discrete-time adaptive control '
                  'has its own Lyapunov synthesis [16], [17]. The present work addresses exactly '
                  'these two points.'))

    h2('Contributions', MINLV['contrib'])
    g(('p', 'Taking a small WIG UAV as the plant, this paper makes the following contributions:'), MINLV['contrib'])
    g(('num', [
        'a seventh-order nonlinear longitudinal model with ground-effect correction is '
        'established, in which the nominal/true mismatch (ground-effect strength, RAM effect and '
        'lift nonlinearity) is constructed explicitly so that the quantity the adaptive '
        'controller must compensate is measurable;',
        'a component-wise decomposition of the pitch-moment height derivative '
        '$\\partial M/\\partial h$ is given, proving quantitatively that the tail downwash term '
        'dominates the height instability while the wing term is stabilising, together with the '
        'height dependence of every term;',
        'it is proved quantitatively that the phugoid-height coupled mode instability originates '
        'entirely from the ground effect: switching the ground effect off returns the mode to '
        'neutral stability;',
        'a three-loop adaptive controller is designed with RBF networks and tanh robust terms in '
        'the moment and drag channels, and closed-loop uniform ultimate boundedness (UUB) is '
        'proved by a Lyapunov argument;',
        'the discrete-time stability criterion $T_s\\Gamma_i\\|\\phi_i\\|^2 < k_i$ is derived, '
        'which explains, from both dimensional scaling and sampling, why the two channel gains '
        'differ by three orders of magnitude;',
        'the design is validated by ablation, parameter perturbation, atmospheric disturbance, '
        'extreme low-altitude flight and Monte-Carlo statistics, and cross-checked between a '
        'Simulink model and a pure MATLAB script.',
    ]), MINLV['contrib'])

    h2('Principal Results')
    add(('table', {
        'headers': ['Metric', 'RBF adaptive', 'DI + robust', 'Pure DI'],
        'rows': [
            ['Height-tracking RMS error / m',
             n(sc['s1_adaptive']['h_rms'], 4), n(sc['s1_di_rob']['h_rms'], 4), n(sc['s1_di']['h_rms'], 4)],
            ['Peak height error / m',
             n(sc['s1_adaptive']['h_err_max'], 4), n(sc['s1_di_rob']['h_err_max'], 4), n(sc['s1_di']['h_err_max'], 4)],
            ['Minimum height above ground / m',
             n(sc['s1_adaptive']['h_min'], 4), n(sc['s1_di_rob']['h_min'], 4), n(sc['s1_di']['h_min'], 4)],
            ['Airspeed-tracking RMS error / (m/s)',
             n(sc['s1_adaptive']['V_rms'], 4), n(sc['s1_di_rob']['V_rms'], 4), n(sc['s1_di']['V_rms'], 4)],
            ['Monte-Carlo pass rate / %',
             n(mc['pass_ad_pct'], 1), '--', n(mc['pass_no_pct'], 1)],
            ['Median height RMS error / m',
             n(mc['med_ad'], 5), '--', n(mc['med_no'], 5)],
        ],
        'key': 'perf', 'caption': 'Performance of the three control schemes (true plant with '
                   'ground-effect mismatch, RAM effect and lift nonlinearity)',
        'widths': [4.9, 3.2, 3.5, 3.3], 'font_size': 8.5,
        'aligns': ['left', 'center', 'center', 'center'],
    }))

    # ============================================================ 2
    h1('Vehicle Model and Ground-Effect Aerodynamics')
    h2('Configuration and Coordinate Frame', MINLV['conf'])
    g(('p', 'A body-fixed frame is used ($x_b$ forward, $y_b$ to the right wing, $z_b$ towards '
              'the belly). The pitch rate $q$ and the pitch moment $M$ are positive nose-up. '
              'The main parameters are listed in Table @tab:params@. The ground-effect flight band is '
              '$h = 0.05$ to $0.50$ m, corresponding to $h/b = 0.021$ to $0.208$. The following '
              'assumptions are made: (i) lateral-directional motion is neglected and the '
              'longitudinal motion is decoupled; (ii) the ground is a rigid plane and waves and '
              'roughness are ignored; (iii) the aerodynamics are quasi-steady and unsteady '
              'hysteresis is neglected; (iv) gusts are accounted for through the relative flow '
              'direction only, neglecting inertia terms due to the gust gradient.'), MINLV['conf'])
    g(('table', {
        'headers': ['Parameter', 'Symbol', 'Value', 'Parameter', 'Symbol', 'Value'],
        'rows': [
            ['Wing span', '$b$', '2.40 m', 'Mass', '$m$', '12.0 kg'],
            ['Chord', '$c$', '0.40 m', 'Pitch inertia', '$I_{yy}$', '1.15 kg$\\cdot$m$^2$'],
            ['Wing area', '$S$', '0.96 m$^2$', 'Max. thrust', '$T_{\\max}$', '35 N'],
            ['Aspect ratio', '$AR$', '6.0', 'Cruise speed', '$V_0$', '18 m/s'],
            ['Zero-lift angle', '$\\alpha_{L0}$', '$-3.0^{\\circ}$', 'Cruise height', '$h_0$', '0.20 m'],
            ['Tail area', '$S_t$', '0.18 m$^2$', 'Tail arm', '$l_t$', '0.95 m'],
            ['Tail incidence', '$i_t$', '$-2.0^{\\circ}$', 'Tail height offset', '$\\Delta z_t$', '0.30 m'],
            ['Elevator time const.', '$\\tau_e$', '0.05 s', 'Engine time const.', '$\\tau_T$', '0.15 s'],
        ],
        'key': 'params', 'caption': 'Main parameters of the reference configuration',
        'widths': [2.4, 1.3, 2.0, 2.4, 1.3, 2.0], 'font_size': 8.5,
        'aligns': ['left', 'center', 'center', 'left', 'center', 'center'],
    }), MINLV['conf'])

    h2('Ground-Effect Aerodynamic Model')
    add(('p', 'Let the ground-effect factor $\\kappa(h)$ be the retention coefficient of the '
              'induced downwash: $\\kappa = 1$ corresponds to free air and $\\kappa \\to 0$ to '
              'full ground contact. The following one-parameter family is adopted:'))
    add(('eq', (r'\kappa(h) = \frac{x^{n}}{A + x^{n}}, \qquad x = \frac{h}{b}', 'kappa')))
    add(('p', f'The shape parameters are $A = {n(0.0641, 4)}$ and $n = {n(1.4622, 4)}$. '
              f'The expression is a physically motivated one-parameter family: it tends to zero '
              f'as $h \\to 0$ and to unity as $h \\to \\infty$, and the parameters were chosen so '
              f'that the height dependence follows the monotonically increasing, saturating trend '
              f'reported in the literature [1], [3], [4]. **It should be stated explicitly** that '
              f'this paper does **not** claim the model has been quantitatively calibrated '
              f'against wind-tunnel or CFD data for this configuration; such a calibration is '
              f'future work (Section VI-A). What is studied here is whether the controller '
              f'remains safe under a mismatch of this kind. Under ground effect the induced drag '
              f'and the effective lift-curve slope become'))
    add(('eq', (r'C_{Di}(h) = \frac{C_L^{2}\,\kappa(h)}{\pi\, AR\, e}, \qquad '
                r'a_w(h) = \frac{a_0}{1 + a_0\,\kappa(h)/(\pi\, AR\, e)}', 'awdrag')))
    add(('p', 'The downwash angle at the tail is attenuated by the same factor, '
              '$\\varepsilon(h,\\alpha) = (\\varepsilon_0 + \\varepsilon_\\alpha \\alpha)'
              '\\,\\kappa(h)$. Fig. @fig:ge@ shows the ground-effect factor, the lift-curve-slope gain '
              'and the induced drag as functions of height.'))
    add(('figure', {'name': 'fig1_ge', 'width_cm': 9.0,
                    'key': 'ge', 'caption': 'Ground-effect factor and the resulting lift-curve-slope '
                               'gain and induced drag versus height above ground.'}))

    if level >= MINLV['getab']:
        add(('table', {
            'headers': ['$h$ / m', '$h/b$', '$\\kappa_{nom}$', '$\\kappa_{true}$',
                        '$a_{w,nom}$', '$a_{w,true}$', '$a_w$ gain / %'],
            'rows': [[n(ge['h'][i], 2), n(ge['hb'][i], 4), n(ge['kappa_nom'][i], 4),
                      n(ge['kappa_true'][i], 4), n(ge['aw_nom'][i], 4),
                      n(ge['aw_true'][i], 4), n(ge['aw_gain_pct'][i], 2)]
                     for i in [0, 1, 2, 3, 5, 7]],
            'key': 'getab', 'caption': 'Ground-effect factor and effective lift-curve slope '
                       '(nominal model and true plant)',
            'widths': [1.7, 1.7, 2.0, 2.1, 2.1, 2.1, 2.4], 'font_size': 8.5,
            'aligns': ['center'] * 7,
        }))

    h2('Seventh-Order Nonlinear Longitudinal Model')
    add(('p', 'The state vector is $x = [V,\\ \\gamma,\\ \\alpha,\\ q,\\ h,\\ T,\\ \\delta_e]^{T}$ '
              'and the control vector is $u = [\\delta_{e,c},\\ \\delta_t]^{T}$. The longitudinal '
              'equations of motion are'))
    add(('eq', (r'm\dot{V} = T\cos(\alpha + i_T) - D - mg\sin\gamma', 'eomv')))
    add(('eq', (r'mV\dot{\gamma} = L + T\sin(\alpha + i_T) - mg\cos\gamma', 'eomgam')))
    add(('eq', (r'\dot{\alpha} = q - \dot{\gamma}, \qquad I_{yy}\,\dot{q} = M, '
                r'\qquad \dot{h} = V\sin\gamma', 'eomkin')))
    add(('eq', (r'\tau_T \dot{T} = T_{cmd} - T, \qquad '
                r'\tau_e \dot{\delta}_e = \sat(\delta_{e,c}) - \delta_e', 'actdyn')))
    add(('p', 'The pitch angle follows from $\\theta = \\gamma + \\alpha$. The wing lift '
              'coefficient is $C_{L,w} = a_w(h)(\\alpha - \\alpha_{L0})$ and the wing drag is '
              '$C_{D,w} = C_{D0} + C_{Di}$. The local angle of attack of the tail is'))
    add(('eq', (r'\alpha_t = \alpha + i_t - \varepsilon(h,\alpha) + \frac{q\, l_t}{V}', 'alphat')))
    g(('p', 'and its lift coefficient is '
              '$C_{L,t} = a_t(h_t)(\\alpha_t - \\alpha_{L0,t}) + a_{\\delta_e}\\delta_e$, where '
              'the effective tail lift-curve slope is computed from (@eq:awdrag@) using the tail height '
              '$h_t = h + \\Delta z_t$ and the tail span. All moments are evaluated as '
              '$M = z F_x - x F_z$ and include the wing, the tail, the thrust-line offset and the '
              'fuselage. A fixed-step fourth-order Runge-Kutta integrator with a 1 ms step is '
              'used, and the flight-control computer runs at 200 Hz with a zero-order hold.'), MINLV['eom_tail'])

    h2('Uncertainty Between the Nominal Model and the True Plant', MINLV['mismatch'])
    g(('p', 'The controller uses a nominal model while the plant is the true vehicle; the '
              'difference is the uncertainty the adaptation law must compensate online. Four '
              'classes of mismatch are introduced, namely ground-effect strength mismatch, the '
              'RAM effect (extra lift and nose-down moment from the high-pressure region beneath '
              'the wing), lift nonlinearity and aerodynamic parameter perturbation; see Table @tab:mismatch@.'), MINLV['mismatch'])
    g(('table', {
        'headers': ['Mismatch', 'Nominal', 'True', 'Physical meaning'],
        'rows': [
            ['Ground-effect shape $A$', n(0.0641, 4), n(0.045, 3), 'ground-effect strength underestimated'],
            ['Ground-effect exponent $n$', n(1.4622, 4), n(1.300, 3), 'different height decay law'],
            ['RAM extra lift', 'none', '$k_{ram} = 0.09$', 'extra lift from high-pressure region'],
            ['RAM extra moment', 'none', 'acting point shifted 5 cm aft', 'centre of pressure moves aft'],
            ['Lift nonlinearity', 'linear', '$C_{L,\\max} = 1.3$ softening', 'stall softening at high $\\alpha$'],
            ['Parasite drag $C_{D0}$', n(0.0250, 4), n(0.0320, 4), 'drag coefficient +28%'],
            ['Downwash gradient $\\varepsilon_\\alpha$', n(0.350, 3), n(0.450, 3), 'tail downwash +29%'],
        ],
        'key': 'mismatch', 'caption': 'Mismatch between the nominal model and the true plant',
        'widths': [3.6, 2.4, 3.4, 5.0], 'font_size': 8.5,
        'aligns': ['left', 'center', 'center', 'left'],
    }), MINLV['mismatch'])
    g(('p', f'At the trim points the mismatch of the true plant relative to the nominal model '
              f'is: pitch-moment mismatch $|\\Delta M| \\le {n(sm["dM_max_abs"], 4)}$ '
              f'N$\\cdot$m, peak lift mismatch $|\\Delta L| \\approx {n(sm["dL_max_abs"], 2)}$ N '
              f'({n(sm["dL_max_pct_W"], 1)}% of weight), and drag mismatch about '
              f'{n(abs(sm["dD_max"]), 2)} to {n(abs(sm["dD_min"]), 2)} N. This level of mismatch '
              f'represents a typical situation in which an engineering estimate has not been '
              f'calibrated against CFD.'), MINLV['mismatch'])

    # ============================================================ 3
    h1('Mechanism of Ground-Effect Height Instability')
    h2('Trim Characteristics')
    add(('p', 'For steady level flight ($\\gamma = 0$, $q = 0$) the trim conditions are'))
    add(('eq', (r'T\cos(\alpha + i_T) - D = 0, \quad L + T\sin(\alpha + i_T) - mg = 0, '
                r'\quad M = 0', 'trimc')))
    add(('p', 'which are solved for $\\alpha$, $\\delta_e$ and $T$. Table @tab:trimtab@ lists the trim '
              'results and the ground-effect height derivative at $V = 18$ m/s.'))
    add(('table', {
        'headers': ['$h$ / m', '$\\alpha_{nom}$ / deg', '$\\alpha_{true}$ / deg',
                    '$\\delta_{e,nom}$ / deg', '$\\delta_{e,true}$ / deg',
                    '$(L/D)_{nom}$', '$(L/D)_{true}$', '$\\partial M/\\partial h$'],
        'rows': [[n(tr['h'][i], 2), n(tr['alpha_nom'][i], 3), n(tr['alpha_true'][i], 3),
                  n(tr['de_nom'][i], 3), n(tr['de_true'][i], 3), n(tr['LD_nom'][i], 2),
                  n(tr['LD_true'][i], 2), sg(tr['dMdh'][i], 3)]
                 for i in range(len(tr['h']))],
        'key': 'trimtab', 'caption': 'Trim results and ground-effect height derivative versus height '
                   '($\\partial M/\\partial h$ in N$\\cdot$m/m)',
        'widths': [1.5, 2.0, 2.0, 2.2, 2.2, 1.8, 1.8, 2.4], 'font_size': 8.5,
        'aligns': ['center'] * 8,
    }))
    g(('p', f'As height increases the ground effect weakens: the trim angle of attack rises '
              f'from {n(tr["alpha_nom"][0], 3)} to {n(tr["alpha_nom"][-1], 3)} deg and the '
              f'lift-to-drag ratio falls from {n(tr["LD_nom"][0], 2)} to {n(tr["LD_nom"][-1], 2)}. '
              f'Because of the ground-effect mismatch and the RAM effect, the trim elevator of '
              f'the true plant differs from the nominal value by '
              f'{n(min(abs(tr["de_true"][i]-tr["de_nom"][i]) for i in range(len(tr["h"]))), 2)} to '
              f'{n(max(abs(tr["de_true"][i]-tr["de_nom"][i]) for i in range(len(tr["h"]))), 2)} deg, '
              f'which is exactly the steady-state mismatch the controller has to compensate.'), MINLV['trim_disc'])
    g(('figure', {'name': 'fig2_trim', 'width_cm': 9.0,
                    'key': 'trim', 'caption': 'Trim characteristics and ground-effect height derivative '
                               'versus height above ground.'}), MINLV['fig_trim'])

    h2('Component-Wise Decomposition of $\\partial M/\\partial h$')
    add(('p', f'The last column of Table @tab:trimtab@ shows that over the whole envelope '
              f'$\\partial M/\\partial h = {sg(min(tr["dMdh"]), 2)}$ to '
              f'{sg(max(tr["dMdh"]), 2)} N$\\cdot$m/m, always positive: a reduction in height '
              f'produces an additional nose-down moment, closing a positive height-pitch '
              f'feedback loop, i.e. the classical ground-effect height instability. To locate its '
              f'physical origin the pitch moment is differentiated component by component at the '
              f'trim point (central differences in $h$, all other states frozen):'))
    add(('eq', (r'\frac{\partial M}{\partial h} = \frac{\partial M_w}{\partial h} + '
                r'\frac{\partial M_t}{\partial h} + \frac{\partial M_{ram}}{\partial h} + '
                r'\frac{\partial M_{nl}}{\partial h}', 'dissurf')))
    add(('p', 'where the subscripts $w$, $t$, $ram$ and $nl$ denote the wing, the tail, the RAM '
              'force and the lift-softening residual respectively. The fuselage and thrust-line '
              'terms are independent of $h$ and vanish identically. Table @tab:decomp@ gives the '
              'decomposition.'))
    add(('table', {
        'headers': ['$h$ / m', '$\\partial M/\\partial h$', 'Wing', 'Tail', 'RAM',
                    'Nonlinear', 'Tail share / %'],
        'rows': [[n(md['h'][i], 2), sg(md['total'][i], 2), sg(md['wing'][i], 2),
                  sg(md['tail'][i], 2), sg(md['ram'][i], 2), sg(md['nl'][i], 2),
                  n(100 * md['tail'][i] / md['total'][i], 1)] for i in range(len(md['h']))],
        'key': 'decomp', 'caption': 'Component-wise decomposition of the pitch-moment height derivative '
                   '(all values in N$\\cdot$m/m)',
        'widths': [1.6, 2.5, 2.0, 2.0, 1.9, 2.0, 2.4], 'font_size': 8.5,
        'aligns': ['center'] * 7,
    }))
    add(('p', f'The decomposition is unambiguous. The tail term is the largest positive '
              f'contribution at every height ({sg(min(md["tail"]), 2)} to '
              f'{sg(max(md["tail"]), 2)} N$\\cdot$m/m, i.e. '
              f'{n(min(100*md["tail"][i]/md["total"][i] for i in range(len(md["h"]))), 1)}% to '
              f'{n(max(100*md["tail"][i]/md["total"][i] for i in range(len(md["h"]))), 1)}% of the '
              f'total), whereas the wing term is always negative '
              f'({sg(min(md["wing"]), 2)} to {sg(max(md["wing"]), 2)} N$\\cdot$m/m) and therefore '
              f'stabilising. The physical mechanisms are as follows.'))
    g(('bullet', [
        '**Tail (destabilising).** Flying close to the ground reduces the downwash at the tail, '
        'which increases the local tail incidence. In trim the tail carries a negative lift '
        '(downwash load), so an increased incidence weakens that negative lift and produces an '
        'additional nose-down moment.',
        '**Wing (stabilising).** Ground effect increases lift '
        '($\\partial L_w/\\partial h < 0$) while the wing aerodynamic centre lies 2 cm ahead of '
        'the centre of gravity, so the extra lift produces a nose-up moment.',
        '**RAM (destabilising).** The high-pressure region beneath the wing acts aft of the '
        'aerodynamic centre and strengthens as height decreases, producing a nose-down moment.',
        '**Lift nonlinearity (destabilising).** Stall softening is stronger at low height, which '
        'is equivalent to losing part of the lift; its point of action is ahead of the '
        'aerodynamic centre, so it also produces a nose-down moment.',
    ]), MINLV['mech'])
    add(('p', f'The sum of the four components matches the total derivative to within '
              f'{md["resid_max"]:.1e} N$\\cdot$m/m, which verifies the consistency of the '
              f'decomposition. The practical implication is that height stability should be '
              f'improved primarily through the tail layout (for example a larger tail height '
              f'offset, downwash shielding, or an all-moving tail) rather than by reshaping the '
              f'wing planform.'))
    if level >= MINLV['fig_mdh']:
        add(('figure', {'name': 'fig12_mdh', 'width_cm': 9.0,
                        'key': 'mdh', 'caption': 'Stacked components and shares of '
                                   '$\\partial M/\\partial h$, and the lift height stiffness.'}))

    h2('Instability of the Phugoid-Height Coupled Mode')
    add(('p', 'Numerical linearisation of (@eq:eomv@)-(@eq:alphat@) at the trim points gives the longitudinal '
              'modes. To isolate the role of the ground effect, the modes are also computed with '
              'the ground effect effectively switched off ($A \\to 0$, i.e. $\\kappa \\equiv 1$).'))
    g(('table', {
        'headers': ['$h$ / m', 'With GE, real / (1/s)', 'imag / (1/s)', 'damping',
                    'No GE, real / (1/s)', 'imag / (1/s)'],
        'rows': [[n(mo['h'][i], 2), sg(mo['re'][i], 4), n(mo['im'][i], 4), n(mo['zeta'][i], 3),
                  sg(mo['re_noge'][i], 4), n(mo['im_noge'][i], 4)]
                 for i in range(len(mo['h']))],
        'key': 'modes', 'caption': 'Low-frequency (phugoid-height coupled) mode versus height',
        'widths': [1.6, 2.7, 2.1, 1.8, 2.7, 2.1], 'font_size': 8.5,
        'aligns': ['center'] * 6,
    }), MINLV['tab_modes'])
    g(('p', 'The conclusion is clear:'), MINLV['modes_lead'])
    g(('bullet', [
        f'With the ground effect switched off, the real part of the low-frequency mode is '
        f'{sg(min(mo["re_noge"]), 4)} to {sg(max(mo["re_noge"]), 4)} 1/s, i.e. neutral stability, '
        f'of the same order as the classical phugoid estimate '
        f'($\\omega_p = \\sqrt{{2}}g/V = {n(st["phugoid_wn"], 4)}$ rad/s and the Lanchester '
        f'approximation $\\zeta_p = 1/(\\sqrt{{2}}(L/D)) = '
        f'{n(min(a["phugoid"]["zeta_p"]), 4)}$ to ${n(max(a["phugoid"]["zeta_p"]), 4)}$).',
        f'With the ground effect active the real part becomes {sg(min(mo["re"]), 4)} to '
        f'{sg(max(mo["re"]), 4)} 1/s and the damping ratio drops to {n(min(mo["zeta"]), 3)}, so '
        f'the instability is caused entirely by the ground effect.',
        f'The largest real part occurs at $h \\approx '
        f'{n(mo["h"][mo["re"].index(max(mo["re"]))], 2)}$ m '
        f'({sg(max(mo["re"]), 4)} 1/s, a time constant of about {n(1/max(mo["re"]), 2)} s) with an '
        f'oscillation frequency of {n(min(mo["im"]), 3)} to {n(max(mo["im"]), 3)} rad/s, which is '
        f'a typical phugoid-height coupled oscillation.',
    ]), MINLV['modes_bullet'])
    g(('figure', {'name': 'fig3_modes', 'width_cm': 9.0,
                    'key': 'modes', 'caption': 'Longitudinal pole map and the real part of the '
                               'phugoid-height coupled mode versus height.'}), MINLV['fig_modes'])
    g(('p', 'This result is consistent with the moment decomposition of Section III-B: the '
              'height variation of the tail downwash both supplies most of '
              '$\\partial M/\\partial h > 0$ and pushes the otherwise neutrally stable phugoid '
              'mode into the right half-plane through the height-normal-force coupling. A WIG '
              'vehicle must therefore rely on active height control whose bandwidth covers this '
              'mode frequency with adequate phase margin.'), MINLV['modes_close'])

    # ============================================================ 4
    h1('RBF Neural-Network Adaptive Controller Design')
    h2('Control Architecture')
    add(('p', 'The controller has a three-layer cascade structure:'))
    add(('bullet', [
        '**Altitude outer loop** (kinematic): the height error and height rate generate the '
        'flight-path angle command $\\gamma_c$;',
        '**attitude inner loop** (dynamic surface + dynamic inversion + RBF + robust term): '
        '$\\gamma_c$ generates the pitch-angle command $\\theta_c$, and the pitch-rate loop then '
        'solves for the elevator command $\\delta_{e,c}$;',
        '**airspeed loop** (thrust dynamic inversion + RBF + robust term + integral): the speed '
        'error generates the throttle command $\\delta_t$.',
    ]))
    add(('p', 'Two RBF networks are used [7], [8], [14]: a moment channel with inputs '
              '$[\\alpha, q, h]$ and '
              '$5 \\times 3 \\times 5 = 75$ nodes, estimating the pitch-moment mismatch, and a '
              'drag channel with inputs $[\\alpha, V, h]$ and $4 \\times 4 \\times 4 = 64$ nodes, '
              'estimating the drag mismatch. **No separate lift channel is required**, because '
              'the angle-of-attack feedback in $\\theta_d = \\gamma_c + \\alpha$ of (@eq:dsc@) '
              'compensates it automatically. The reason deserves emphasis: if the pitch loop '
              'tracks $\\theta = \\theta_d$, then the kinematic identity $\\gamma = \\theta - '
              '\\alpha$ immediately gives $\\gamma = \\gamma_c$. Since this derivation uses only '
              '$\\gamma = \\theta - \\alpha$ and is independent of both the control law and the '
              'model, the flight-path angle still tracks its command accurately even when the '
              'lift model is in error (the angle of attack simply changes), which removes an '
              'entire network.'))

    h2('Altitude Outer Loop and Dynamic-Surface Attitude Inner Loop')
    add(('p', 'The altitude loop is a proportional guidance law with height-rate damping; the '
              'height rate is synthesised directly from $\\dot{h} = V\\sin\\gamma$ so that no '
              'numerical differentiation is needed:'))
    add(('eq', (r'\gamma_d = \arcsin\!\left[\sat\!\left('
                r'\frac{\dot{h}_c - k_h e_h - k_{hd}(\dot{h} - \dot{h}_c)}{V},'
                r'\ \sin\gamma_{\max}\right)\right], \qquad e_h = h - h_c', 'gammaloop')))
    add(('p', 'The attitude loop uses dynamic surface control (DSC) [11]-[13] so that the '
              'virtual control need not be differentiated analytically:'))
    add(('eq', (r'\theta_d = \sat\!\left(\gamma_c + \alpha,\ \theta_{\max}\right), \qquad '
                r'\tau_{th}\dot{\theta}_c = \theta_d - \theta_c', 'dsc')))
    add(('eq', (r'q_d = \dot{\theta}_c - k_\theta(\theta - \theta_c), \qquad '
                r'\tau_q \dot{q}_{cf} = \sat(q_d) - q_{cf}', 'qd')))
    add(('eq', (r'e_q = q - q_{cf}, \qquad \nu = \dot{q}_{cf} - k_q e_q', 'eqerr')))
    g(('p', f'Since $\\gamma = \\theta - \\alpha$, (@eq:dsc@) implies '
              f'$\\dot{{\\theta}} = k_\\theta(\\gamma_c - \\gamma)$: the pitch loop is '
              f'equivalent to a flight-path-angle tracking loop with natural frequency and '
              f'damping $\\omega_n = \\sqrt{{\\dot{{\\gamma}}_\\alpha k_\\theta}}$ and '
              f'$\\zeta = \\dot{{\\gamma}}_\\alpha/(2\\omega_n)$, where '
              f'$\\dot{{\\gamma}}_\\alpha = \\partial\\dot{{\\gamma}}/\\partial\\alpha = '
              f'{n(st["dgamdot_dalpha"], 4)}$ 1/s is obtained from the numerical linearisation. '
              f'With $k_\\theta = 3.20$ 1/s this gives $\\omega_n = '
              f'{n((st["dgamdot_dalpha"]*3.20)**0.5, 3)}$ rad/s and $\\zeta = '
              f'{n(st["dgamdot_dalpha"]/(2*(st["dgamdot_dalpha"]*3.20)**0.5), 3)}$; tuning '
              f'requires $\\zeta \\geq 1$ so that this loop does not resonate (Section IV-E).'), MINLV['dsc_tune'])

    h2('Dynamic-Inversion Control Law and Adaptation Law')
    add(('p', 'Let $M_0(x)$ be the nominal zero-elevator pitch moment and $M_{\\delta_e}$ the '
              'control derivative, and define $f_0 = M_0/I_{yy}$ and '
              '$b = M_{\\delta_e}/I_{yy}$. The elevator command is'))
    add(('eq', (r'\delta_{e,c} = \frac{1}{b}\left(\nu - f_0 - u_M - u_r\right)', 'deltac')))
    add(('p', 'where $u_M = W_1^{T}\\phi_1$ is the online estimate of the moment mismatch and '
              '$u_r$ is the robust term. The basis functions and the regression vector are'))
    add(('eq', (r'\phi_j(z) = \exp\!\left(-\frac{1}{2}\sum_{i=1}^{3}'
                r'\frac{(z_i - c_{ij})^{2}}{\sigma_i^{2}}\right), \qquad '
                r'\phi_1 = \phi(z_1)\,\frac{\bar{q}Sc}{I_{yy}}', 'phi')))
    add(('p', 'The centres $c_j$ are placed on a uniform grid in the normalised cube '
              '$[-1,1]^3$ and the widths are set to the grid spacing, so that neighbouring basis '
              'functions overlap by $e^{-1/2} \\approx 0.61$ at their centres. Including '
              '$\\bar{q}Sc$ in the regression vector is a physical dimensionality reduction: '
              'since the aerodynamic moment is proportional to dynamic pressure, factoring it '
              'out leaves the network to learn only the non-dimensional moment-coefficient '
              'mismatch, which keeps the weight magnitudes stable across speed and reduces the '
              'moment-channel input dimension from four to three, cutting the node count by an '
              'order of magnitude. The weights are kept bounded by a projection operator [9], [10]:'))
    add(('eq', (r'\dot{W}_1 = \Proj\!\left[\Gamma_1\left(\phi_1 e_q - \nu_e|e_q| W_1\right)\right],'
                r'\qquad \dot{W}_2 = -\Gamma_2\left(\phi_2 e_V + \nu_e|e_V| W_2\right)', 'adap')))
    add(('eq', (r'\Proj(\tau) = \begin{cases} \tau, & \left\|W\right\| < W_{\max}\ '
                r'\text{or}\ W^{T}\tau \leq 0 \\ '
                r'\tau - \dfrac{W W^{T}}{\left\|W\right\|^{2}}\tau, & \text{otherwise} '
                r'\end{cases}', 'proj')))
    add(('p', 'Note that the signs of the two adaptation laws are opposite, because the estimates '
              'enter the control laws in different positions: $u_M$ enters (@eq:deltac@) with a minus sign '
              'while $u_D$ enters (@eq:tcmd@) with a plus sign. If a sign is wrong the estimate becomes '
              'positive feedback and the closed loop diverges.'))

    h2('Airspeed Loop')
    add(('p', 'The airspeed control law and error dynamics are'))
    add(('eq', (r'T_{cmd} = \frac{m\left(\dot{V}_d + u_D - u_{rV}\right) + D_0 + mg\sin\gamma_c}'
                r'{\cos(\alpha + i_T)}', 'tcmd')))
    add(('eq', (r'\dot{V}_d = \dot{V}_c - k_V e_V - k_{IV} I_V, \qquad \dot{I}_V = e_V', 'vdot')))
    add(('p', 'Two details of (@eq:tcmd@) are essential. First, the gravity feedforward must be taken '
              'from the commanded flight-path angle $\\gamma_c$, not from the measured $\\gamma$: '
              'using the measurement closes a positive feedback loop '
              '$\\gamma \\to T_{cmd} \\to T \\to V \\to L \\to \\dot{\\gamma} \\to \\gamma$ with a '
              'loop gain of $mg = 117.7$ N/rad, which, together with the engine lag, pushes the '
              'short-period/phugoid coupled mode into the right half-plane. Second, the robust '
              'term must enter with a minus sign so that $-u_{rV}$ appears in the error dynamics, '
              'matching the moment channel and making the Lyapunov cross-terms cancel exactly.'))

    h2('Lyapunov Stability Analysis')
    add(('p', 'Let the moment mismatch between the true plant and the nominal model be '
              '$\\Delta f = \\Delta M/I_{yy}$ and the drag mismatch be $\\Delta D/m$, and write '
              'the ideal approximation as $\\Delta f = W_1^{*T}\\phi_1 + \\varepsilon_1$ and '
              '$\\Delta D/m = W_2^{*T}\\phi_2 + \\varepsilon_2$, with weight error '
              '$\\tilde{W}_i = W_i - W_i^{*}$. Substituting into (@eq:deltac@) and (@eq:tcmd@) gives the error '
              'dynamics'))
    add(('eq', (r'\dot{e}_q = -k_q e_q - \tilde{W}_1^{T}\phi_1 + \varepsilon_1 - u_r', 'errdq')))
    add(('eq', (r'\dot{e}_V = -k_V e_V - k_{IV} I_V + \tilde{W}_2^{T}\phi_2 '
                r'- \varepsilon_2 - u_{rV}', 'errdv')))
    add(('p', 'Consider the Lyapunov function'))
    add(('eq', (r'V_L = \frac{1}{2}e_q^{2} + \frac{1}{2}\tilde{W}_1^{T}\Gamma_1^{-1}'
                r'\tilde{W}_1 + \frac{1}{2}e_V^{2} + \frac{1}{2}\tilde{W}_2^{T}'
                r'\Gamma_2^{-1}\tilde{W}_2 + \frac{1}{2}k_{IV} I_V^{2}', 'lyap')))
    add(('p', 'Differentiating along the closed-loop trajectories and substituting (@eq:adap@), the '
              'cross-terms cancel exactly:'))
    add(('eq', (r'e_q\left(-\tilde{W}_1^{T}\phi_1\right) + \tilde{W}_1^{T}\Gamma_1^{-1}'
                r'\Gamma_1\phi_1 e_q = 0', 'cancel1')))
    add(('eq', (r'e_V\left(\tilde{W}_2^{T}\phi_2\right) + \tilde{W}_2^{T}\Gamma_2^{-1}'
                r'\left(-\Gamma_2\phi_2 e_V\right) = 0', 'cancel2')))
    add(('p', 'Equations (@eq:cancel1@) and (@eq:cancel2@) are exactly why the signs of the two adaptation laws must '
              'be opposite. The $e$-modification gives '
              '$\\tilde{W}_i^{T}W_i \\geq \\frac{1}{2}\\|\\tilde{W}_i\\|^2 - '
              '\\frac{1}{2}\\|W_i^{*}\\|^2$. In addition the standard inequality '
              '$|z| - z\\tanh(z/\\Phi) \\leq 0.2785\\,\\Phi$ is used, for which a self-contained '
              'proof is as follows: with $u = z/\\Phi \\geq 0$ the left-hand side equals '
              '$\\Phi\\,g(u)$ where $g(u) = u(1 - \\tanh u)$; setting '
              '$g\'(u) = 1 - \\tanh u - u\\,\\mathrm{sech}^{2}u = 0$ gives '
              '$u^{*} = 1/(1 + \\tanh u^{*}) \\approx 0.6392$ and $g(u^{*}) \\approx 0.278465$, '
              'so $0.2785$ is the exact bound. Provided the robust gains satisfy '
              '$\\eta_r \\geq \\varepsilon_N + d_M$ and $\\eta_V \\geq \\varepsilon_N + d_V$, one '
              'obtains'))
    add(('eq', (r'\dot{V}_L \leq -2\lambda_{\min} V_L + c_0, \qquad '
                r'c_0 = 0.2785\left(\eta_r\Phi_r + \eta_V\Phi_V\right) + '
                r'\nu_e\left(\left\|W_1^{*}\right\|^{2} + \left\|W_2^{*}\right\|^{2}\right)', 'vdotl')))
    add(('p', 'where $\\lambda_{\\min} = \\min\\{k_q, k_V, k_{IV}, \\nu_e\\}/2$ is a lower bound '
              'on the decay rate. Hence the uniform ultimate boundedness (UUB) result'))
    add(('eq', (r'\left\|e(t)\right\| \leq \sqrt{\frac{2V_L(0)}{\lambda_{\min}}'
                r'e^{-2\lambda_{\min} t} + \frac{c_0}{\lambda_{\min}}}', 'uub')))
    add(('p', 'that is, the tracking error converges exponentially to a residual set of radius '
              '$\\sqrt{c_0/\\lambda_{\\min}}$. The projection operator (@eq:proj@) guarantees '
              '$\\|W(t)\\| \\leq W_{\\max}$ for all $t \\geq 0$, and its geometric property of '
              'removing only the radial component does not destroy the negative definiteness of '
              '$\\dot{V}_L$. The altitude loop is a cascade: from '
              '$\\dot{e}_h = -k_h e_h + V(\\sin\\gamma - \\sin\\gamma_c)$ the height error is '
              'ultimately bounded by the inner-loop flight-path tracking error, so the UUB '
              'property of the inner loop carries over to the whole closed loop.'))
    if level >= MINLV['nu_e']:
        add(('p', 'The $\\nu_e$ term in (@eq:vdotl@) makes $c_0$ depend on the ideal weight norms, which '
                  'gives a design hint: the $e$-modification coefficient should not be too large, '
                  'otherwise the residual radius is dominated by '
                  '$\\nu_e\\|W^{*}\\|^2/\\lambda_{\\min}$. Here $\\nu_e = 0.50$ and the measured '
                  'weight norms settle at $\\|W_1\\| \\approx 0.044$ and '
                  '$\\|W_2\\| \\approx 0.150$, far below the projection bound $W_{\\max} = 12.0$, '
                  'so the residual radius is governed mainly by the robust-term contribution '
                  '$0.2785(\\eta_r\\Phi_r + \\eta_V\\Phi_V)$.'))

    h2('Discrete-Time Stability Constraint')
    add(('p', 'The adaptation law is implemented digitally at 200 Hz with forward Euler. This is '
              'the step most easily overlooked when moving an RBF adaptive design from continuous '
              'time to a digital implementation, and it has the most severe consequences '
              '[15]-[17]. '
              'Combining the error and weight channels and linearising (all other dynamics '
              'frozen, leakage and projection neglected) gives the two-state system'))
    add(('eq', (r'\begin{bmatrix} e(k+1) \\ \tilde{W}(k+1) \end{bmatrix} = '
                r'\begin{bmatrix} 1 - T_s k & -T_s\phi^{T} \\ '
                r'T_s\Gamma\phi & 1 \end{bmatrix}'
                r'\begin{bmatrix} e(k) \\ \tilde{W}(k) \end{bmatrix}', 'disc')))
    add(('p', 'whose characteristic polynomial is '
              '$\\lambda^2 - (1-T_sk)\\lambda + (1 - T_sk + T_s^2\\Gamma\\|\\phi\\|^2)$. The Jury '
              'criterion, through $\\det < 1$, yields the governing constraint'))
    add(('eq', (r'T_s\,\Gamma_i\left\|\phi_i\right\|^{2} < k_i', 'crit')))
    add(('p', 'where $k_1 = k_q$ and $k_2 = k_V$ are the proportional gains of the corresponding '
              'channels. Writing each regression vector as a dimensional factor times the basis '
              'vector, $\\phi_1 = \\phi_{rbf}\\,\\bar{q}Sc/I_{yy}$ and '
              '$\\phi_2 = \\phi_{rbf}/m$, and substituting the parameters used here:'))
    g(('table', {
        'headers': ['Channel', 'Factor $g_i$', '$\\|\\phi_{i,rbf}\\|^2$',
                    '$T_s\\Gamma_i\\|\\phi_i\\|^2$', 'Gain $k_i$', 'Margin ratio'],
        'rows': [
            ['Moment', n(66.265, 3) + ' s$^{-2}$', n(5.3943, 4), n(0.5922, 4),
             n(6.00, 2), n(6.00 / 0.5922, 1)],
            ['Drag', n(0.083333, 6) + ' kg$^{-1}$', n(5.3744, 4), n(0.0005598, 7),
             n(1.53, 2), n(1.53 / 0.0005598, 1)],
        ],
        'key': 'disc', 'caption': 'Stability margins of the discrete adaptation law at the trim '
                   'point ($T_s = 5$ ms)',
        'widths': [1.8, 3.0, 2.6, 3.0, 2.4, 2.0], 'font_size': 8.5,
        'aligns': ['center'] * 6,
    }), MINLV['tab_disc'])
    add(('p', f'Table @tab:disc@ explains quantitatively why the two channel gains differ by three '
              f'orders of magnitude ($\\Gamma_1 = {n(0.005, 3)}$ and $\\Gamma_2 = {n(3.0, 1)}$). '
              f'The moment-channel regression vector is amplified by '
              f'$\\bar{{q}}Sc/I_{{yy}} \\approx {n(66.265, 1)}$ whereas the drag-channel one is '
              f'attenuated by $1/m \\approx {n(1/12, 4)}$, a ratio of about 795. Comparing the '
              f'gain values directly would wrongly suggest that the moment channel learns too '
              f'slowly, and increasing $\\Gamma_1$ accordingly drives the weights into '
              f'saturation within a few sampling periods. Exactly this behaviour was observed '
              f'during tuning: the weights hit the projection bound and the elevator saturated. '
              f'Equation (@eq:crit@) provides a directly usable design criterion.'))

    if level >= MINLV['tuning']:
        h2('Gain Tuning via Sampled Closed-Loop Poles')
        add(('p', 'For objective assessment of the controller, a sampled-data linearisation of the '
                  'loop "continuous plant + 200 Hz discrete controller (zero-order hold)" is '
                  'constructed: a closed-loop simulation with a constant reference is first run '
                  'until the weights converge, the true equilibrium of the frozen-parameter system '
                  'is then solved for, and finally the Jacobian of the map '
                  '$F:(x_k,z_k) \\to (x_{k+1},z_{k+1})$ is obtained by central differences and the '
                  'eigenvalues of the $15 \\times 15$ closed-loop matrix are computed. The tuning '
                  'procedure is:'))
        add(('num', [
            'Locate the source of instability by switching terms on and off: a pair of unstable '
            'poles dominated by the thrust state was found, and the eigenvector confirmed that it '
            'was caused by the $mg\\sin\\gamma$ gravity feedforward in the thrust command closing '
            'a positive feedback loop; feeding forward the commanded flight-path angle '
            '$\\gamma_c$ instead breaks the loop.',
            'Correct the sign of the robust term in the airspeed channel: the robust term must '
            'enter the thrust command with a minus sign; written with a plus sign its '
            'zero-crossing equivalent gain $\\eta_V/\\Phi_V$ cancels the airspeed proportional '
            'gain and creates positive feedback.',
            'Sweep the nonlinear performance indices over the envelope and select the gains from '
            'the height RMS error together with the minimum height above ground.',
            'Set the boundary-layer thicknesses from the rule that the zero-crossing equivalent '
            f'gain of the robust term must not exceed the proportional gain of that loop: '
            f'$\\Phi_r = {n(0.80, 2)}$ rad/s and $\\Phi_V = {n(1.00, 2)}$ m/s, giving equivalent '
            f'gains of {n(2.50/0.80, 2)} and {n(1.50/1.00, 2)}.',
        ]))
        add(('p', f'With the final gains the largest modulus of the 15 sampled closed-loop poles is '
                  f'$\\max|z| = {n(M["clp"]["final_maxabsz"], 5)} < 1$, so all poles lie inside '
                  f'the unit circle; the slowest mode is dominated by the airspeed integral state '
                  f'($s = {n(M["clp"]["slow_s_real"], 3)}$ 1/s, a time constant of about '
                  f'{n(1/abs(M["clp"]["slow_s_real"]), 1)} s). The equilibrium residual is '
                  f'{M["clp"]["res_eq"]:.1e} and the equilibrium height differs from its command '
                  f'by {n(1000*(M["clp"]["h_eq"]-0.20), 2)} mm. A term-by-term sensitivity study '
                  f'further shows that **switching the robust term off raises $\\max|z|$ to '
                  f'{n(M["clp"]["robust_off_maxabsz"], 5)}**, with the dominant pole moving to '
                  f'$s = {sg(M["clp"]["robust_off_s"], 3)}$ 1/s and being dominated by the thrust '
                  f'state $T$. The robust term is therefore what keeps this loop stable, which '
                  f'corroborates the conclusion of Section IV-D that the airspeed-channel robust '
                  f'term must enter with a minus sign: if the sign is reversed, its zero-crossing '
                  f'equivalent gain $\\eta_V/\\Phi_V$ cancels the airspeed proportional gain and '
                  f'the thrust-speed loop loses its damping.'))
        add(('p', 'It is worth noting that the closed-loop pole analysis gives different verdicts '
                  'on the two baselines: the shipped gains give $\\max|z| < 1$ (stable), whereas '
                  'the intermediate tuning gains ($k_h = 3.0$, $\\tau_g = 0.05$ s) give '
                  '$\\max|z| = 0.99982$ — still inside the unit circle but only '
                  '$1.8\\times10^{-4}$ from the boundary, i.e. marginal. This motivated reducing '
                  '$k_h$ from 3.0 to 2.0 and $\\tau_g$ from 0.05 s to 0.010 s, which moves the '
                  'slowest pole from $s = -0.036$ 1/s to $-0.116$ 1/s and markedly improves the '
                  'margin.'))

    # ============================================================ 5
    h1('Simulation Validation')
    h2('Simulation Setup', MINLV['setup'])
    g(('p', 'Unless stated otherwise the simulations use the "true plant with nominal '
              'controller" mismatch configuration: the plant includes ground-effect strength '
              'mismatch, the RAM effect and lift nonlinearity, while the controller uses the '
              'nominal model. The integration step is 1 ms and the controller samples at 200 Hz. '
              'The reference case is a height command of 0.20, 0.35, 0.10 and 0.25 m (spanning '
              'the whole ground-effect band) with a speed command of 18 to 20 m/s.'), MINLV['setup'])

    h2('Ablation Study')
    add(('p', f'Table @tab:perf@ compares the three control schemes [22], [25], [26]. '
              'With the nominal dynamic inversion '
              f'alone the lift and moment errors caused by the ground-effect mismatch cannot be '
              f'compensated, and the vehicle loses height in the descent segment and touches the '
              f'ground. Adding the robust term reduces the error slightly but the vehicle still '
              f'touches down. With the RBF adaptation the height RMS error falls to '
              f'{n(sc["s1_adaptive"]["h_rms"], 4)} m and the minimum height above ground, '
              f'{n(sc["s1_adaptive"]["h_min"], 4)} m, coincides exactly with the lowest commanded '
              f'height, so no ground contact occurs. The improvement factors are '
              f'{n(sc["s1_improve"], 2)} in height and {n(sc["s1_improve_v"], 2)} in airspeed.'))
    add(('figure', {'name': 'fig4_tracking', 'width_cm': 9.0,
                    'key': 'tracking', 'caption': 'Height and airspeed tracking in the ground-effect band '
                               '(adaptive versus ablated schemes).'}))
    if level >= MINLV['fig_states']:
        add(('figure', {'name': 'fig5_states', 'width_cm': 9.0,
                        'key': 'states', 'caption': 'Pitch angle, flight-path angle, pitch rate, elevator '
                                   'and thrust under adaptive control.'}))
    g(('p', f'Fig. @fig:adaptive@ shows the adaptive signals. The moment-channel output $u_M$ adjusts '
              f'continuously during the height manoeuvre to compensate the ground-effect mismatch '
              f'and the RAM moment; the weight norm remains bounded by the projection operator and '
              f'settles at $\\|W_1\\| \\approx {n(0.044, 3)}$ under steady conditions. The '
              f'drag-channel output $u_D$ compensates a drag mismatch of about '
              f'{n(abs(sm["dD_max"]), 1)} N, keeping the airspeed RMS error at only '
              f'{n(sc["s1_adaptive"]["V_rms"], 4)} m/s.'), MINLV['adaptive'])
    g(('figure', {'name': 'fig6_adaptive', 'width_cm': 9.0,
                    'key': 'adaptive', 'caption': 'RBF network outputs, robust terms, weight norms and '
                               'tracking errors versus time.'}), MINLV['adaptive'])

    if level >= MINLV['extra_trials']:
        h2('Parameter Perturbation')
        add(('p', f'{len(sc["s2_pert"])-1} extreme perturbation cases are added to the nominal '
                  f'plant, covering mass, ground-effect strength, drag coefficient, downwash '
                  f'gradient and lift-curve slope. In all {len(sc["s2_pert"])} cases the vehicle '
                  f'does not touch the ground and the height RMS error stays between '
                  f'{n(sc["s2_h_rms_min"], 4)} and {n(sc["s2_h_rms_max"], 4)} m.'))
        add(('table', {
            'headers': ['Case', '$h_{rms}$ / m', 'Peak height error / m', '$h_{\\min}$ / m',
                        'Peak $\\delta_e$ / deg', 'Safe'],
            'rows': [[lab(p['label']), n(p['h_rms'], 4), n(p['h_err_max'], 4),
                      n(p['h_min'], 4), n(p['de_max'], 1), 'yes' if p['ok'] else 'no']
                     for p in sc['s2_pert']],
            'key': 'pert', 'caption': 'Performance under parameter perturbation (RBF adaptive '
                       'controller)',
            'widths': [5.0, 2.0, 2.4, 2.0, 2.2, 1.6], 'font_size': 8.5,
            'aligns': ['left'] + ['center'] * 5,
        }))
        add(('figure', {'name': 'fig7_perturbation', 'width_cm': 9.0,
                        'key': 'pert', 'caption': 'Height tracking under parameter perturbation.'}))

        h2('Atmospheric Disturbance')
        add(('p', 'Discrete 1-cos gusts and Dryden continuous turbulence are simulated; the '
                  'results are given in Table @tab:gust@.'))
        add(('table', {
            'headers': ['Disturbance', 'Adaptive $h_{rms}$ / m', 'Adaptive $h_{\\min}$ / m',
                        'Safe', 'No adaptation $h_{rms}$ / m', 'Safe'],
            'rows': [[lab(g['label']), n(g['ad_h_rms'], 4), n(g['ad_h_min'], 4),
                      'yes' if g['ad_ok'] else 'no', n(g['no_h_rms'], 4),
                      'yes' if g['no_ok'] else 'no'] for g in sc['s3_gust']],
            'key': 'gust', 'caption': 'Performance under atmospheric disturbance',
            'widths': [4.8, 2.6, 2.4, 1.4, 2.6, 1.4], 'font_size': 8.5,
            'aligns': ['left'] + ['center'] * 5,
        }))
        g1 = sc['s3_gust'][0]
        g2 = sc['s3_gust'][2]
        add(('p', f'In a moderate gust (1.5 m/s) and in continuous turbulence '
                  f'($\\sigma = 1.5$ m/s) the adaptive controller gives height RMS errors of '
                  f'{n(g1["ad_h_rms"], 4)} m and {n(g2["ad_h_rms"], 4)} m respectively, without '
                  f'ground contact, whereas switching the adaptation off causes ground contact in '
                  f'both cases.'))
        add(('p', f'It must be stated honestly that in a severe gust ($W_g = 3.0$ m/s) the '
                  f'adaptive controller also touches the ground '
                  f'($h_{{rms}} = {n(sc["s3_gust"][1]["ad_h_rms"], 4)}$ m). The reason is that a '
                  f'3.0 m/s vertical gust produces an equivalent angle-of-attack step of about '
                  f'{n(math.degrees(math.atan(3.0/18.0)), 2)} deg for this vehicle, corresponding '
                  f'to a lift disturbance of about 141.7% of weight, which exceeds the physical '
                  f'capability of the actuators and the available height margin. This result shows '
                  f'that the ground-effect flight envelope of the present configuration is '
                  f'relatively sensitive to vertical gusts, and that operational weather limits or '
                  f'a larger height margin are required in practice.'))
        add(('figure', {'name': 'fig8_gust', 'width_cm': 9.0,
                        'key': 'gust', 'caption': 'Height response under gust and turbulence.'}))

        h2('Extreme Low-Altitude Flight and Measurement Noise')
        low = sc['s4_low']
        add(('p', f'The controller is assessed in the most demanding case: the height command '
                  f'drops to 0.06 m ($h/c = 0.15$, deep inside the ground-effect region) while '
                  f'measurement noise is added (airspeed 0.15 m/s, angle of attack 0.15 deg, '
                  f'pitch rate 0.3 deg/s, height 0.01 m) and actuator limits are active. The '
                  f'adaptive controller gives a height RMS error of {n(low["ad"]["h_rms"], 4)} m '
                  f'and a minimum height above ground of {n(low["ad"]["h_min"], 4)} m with no '
                  f'ground contact and a peak elevator deflection of only '
                  f'{n(low["ad"]["de_max"], 1)} deg; with the adaptation switched off the height '
                  f'RMS error rises to {n(low["no"]["h_rms"], 4)} m and the vehicle touches down.'))
        add(('figure', {'name': 'fig9_lowalt', 'width_cm': 9.0,
                        'key': 'lowalt', 'caption': 'Extreme low-altitude flight (minimum command 0.06 m) '
                                   'with measurement noise.'}))

    h2('Monte-Carlo Robustness Statistics')
    g(('p', f'{mc["N"]} samples are drawn independently and uniformly within the ranges: mass '
              f'$\\pm 25$%, inertia $\\pm 25$%, parasite drag $\\pm 40$%, lift-curve slope '
              f'$\\pm 10$%, pitch-moment coefficient $\\pm 30$%, ground-effect strength parameter '
              f'$\\pm 60$%, downwash gradient $\\pm 40$%, tail efficiency $\\pm 15$%, initial '
              f'height offset $\\pm 0.03$ m and initial speed offset $\\pm 1.0$ m/s.'), MINLV['mc_setup'])
    add(('table', {
        'headers': ['Metric', 'Mean', 'Std', 'Median', '95th pct', 'Max'],
        'rows': [[lab(k), n(v['mean'], 5), n(v['std'], 5), n(v['median'], 5), n(v['p95'], 5),
                  n(v['max'], 5)] for k, v in mc['stat'].items()],
        'key': 'mc', 'caption': f'Monte-Carlo statistics ({mc["N"]} random parameter samples)',
        'widths': [5.2, 2.2, 2.2, 2.2, 2.2, 2.2], 'font_size': 8.5,
        'aligns': ['left'] + ['center'] * 5,
    }))
    add(('p', f'The pass rate (no ground contact and convergent) of the adaptive controller is '
              f'{mc["pass_ad_n"]}/{mc["pass_ad_N"]} = {n(mc["pass_ad_pct"], 1)}%, against '
              f'{mc["pass_no_n"]}/{mc["pass_no_N"]} = {n(mc["pass_no_pct"], 1)}% without '
              f'adaptation; the median height RMS error falls from {n(mc["med_no"], 5)} m to '
              f'{n(mc["med_ad"], 5)} m, an improvement of {n(mc["med_improve"], 1)} times. The '
              f'final weight norms have mean {n(mc["W1_mean"], 3)} and maximum '
              f'{n(mc["W1_max"], 3)} for $\\|W_1\\|$, both far below the projection bound '
              f'$W_{{\\max}} = 12.0$, confirming that the adaptation law operates well inside the '
              f'safe region.'))
    if level >= MINLV['fig_mc']:
        add(('figure', {'name': 'fig10_montecarlo', 'width_cm': 9.0,
                        'key': 'mc', 'caption': 'Monte-Carlo height envelope and distribution of the peak '
                                   'height error.'}))

    h2('Simulink Cross-Validation', MINLV['simulink'])
    g(('p', 'The same case is simulated both with a Simulink model and with the pure MATLAB '
              'script. Both share the same plant and controller code; only the integrator and the '
              'scheduling are provided by Simulink. The comparison must respect consistent signal '
              'definitions: the Simulink $u$ channel records the controller **command**, whereas '
              'the script records the actuator **state**, and the two differ by a first-order lag '
              'of $\\tau_e = 0.05$ s (up to about $6^{\\circ}$ under the 120 deg/s rate limit). '
              'Table @tab:simtab@ therefore reports both state-versus-state and command-versus-command '
              'comparisons.'), MINLV['simulink'])
    g(('table', {
        'headers': ['Metric', 'Simulink', 'MATLAB script', 'Deviation'],
        'rows': [
            ['Height RMS error / m', n(sI['h_rms']['sl'], 6), n(sI['h_rms']['ml'], 6), f"{sI['h_rms']['dev']:.2e}"],
            ['Peak height error / m', n(sI['h_err_max']['sl'], 6), n(sI['h_err_max']['ml'], 6), f"{sI['h_err_max']['dev']:.2e}"],
            ['Minimum height / m', n(sI['h_min']['sl'], 6), n(sI['h_min']['ml'], 6), f"{sI['h_min']['dev']:.2e}"],
            ['Airspeed RMS error / (m/s)', n(sI['V_rms']['sl'], 6), n(sI['V_rms']['ml'], 6), f"{sI['V_rms']['dev']:.2e}"],
            ['Peak elevator (state) / deg', n(sI['de_state']['sl'], 4), n(sI['de_state']['ml'], 4), f"{sI['de_state']['dev']:.2e}"],
            ['Peak elevator (command) / deg', n(sI['de_cmd']['sl'], 4), n(sI['de_cmd']['ml'], 4), f"{sI['de_cmd']['dev']:.2e}"],
        ],
        'key': 'simtab', 'caption': 'Simulink model versus pure MATLAB script',
        'widths': [4.8, 3.2, 3.2, 3.0], 'font_size': 8.5,
        'aligns': ['left', 'center', 'center', 'center'],
    }), MINLV['simulink'])
    g(('p', f'The largest trajectory deviations (state versus state) are '
              f'{sI["traj_h"]:.3e} m in height, {sI["traj_V"]:.3e} m/s in airspeed and '
              f'{sI["traj_de"]:.3e} deg in elevator deflection; the largest command deviation '
              f'(command versus command) is {sI["traj_de_cmd"]:.3e} deg. All are at the level of '
              f'sampling and interpolation error, showing that the Simulink model and the script '
              f'simulation are numerically equivalent and that the model can serve as a basis for '
              f'hardware-in-the-loop testing and code generation.'), MINLV['simulink'])
    g(('figure', {'name': 'fig11_simulink', 'width_cm': 9.0,
                    'key': 'simulink', 'caption': 'Consistency check between the Simulink model and the '
                               'pure MATLAB script.'}), MINLV['simulink'])

    # ============================================================ 6
    h1('Conclusions')
    add(('p', 'This paper has studied the mechanism of ground-effect height instability and the '
              'design of an RBF neural-network adaptive longitudinal controller for a small WIG '
              'UAV. The main conclusions are as follows.'))
    add(('num', [
        f'A seventh-order nonlinear longitudinal model with ground-effect correction was '
        f'established. Over $h/b = 0.02$ to $0.5$ the ground-effect factor reproduces the trends '
        f'of published wind-tunnel and CFD data: at $h = 0.05$ m the induced drag falls to '
        f'{n(100*ge["kappa_nom"][0], 1)}% of its free-air value and the lift-curve slope rises by '
        f'{n(ge["aw_gain_pct"][0], 1)}%, while at $h = 0.50$ m the lift-curve slope is still '
        f'{n(ge["aw_gain_pct"][5], 1)}% higher.',

        f'The component-wise decomposition of $\\partial M/\\partial h$ revealed the height '
        f'instability mechanism quantitatively: over the whole envelope '
        f'$\\partial M/\\partial h = {sg(min(md["total"]), 2)}$ to {sg(max(md["total"]), 2)} '
        f'N$\\cdot$m/m, positive everywhere, of which the tail downwash term contributes '
        f'{sg(max(md["tail"]), 2)} N$\\cdot$m/m (the dominant destabilising term), the wing term '
        f'{sg(min(md["wing"]), 2)} N$\\cdot$m/m (stabilising), and the RAM and lift-nonlinearity '
        f'terms about {sg(md["ram"][3], 2)} and {sg(md["nl"][3], 2)} N$\\cdot$m/m respectively '
        f'(destabilising). The four terms sum to the numerical total to within '
        f'{md["resid_max"]:.1e}.',

        f'The phugoid-height coupled mode instability was shown to originate entirely from the '
        f'ground effect: with ground effect the real part is {sg(min(mo["re"]), 4)} to '
        f'{sg(max(mo["re"]), 4)} 1/s and the lowest damping ratio is {n(min(mo["zeta"]), 3)}, '
        f'whereas switching the ground effect off returns the mode to neutral stability '
        f'(real part {sg(min(mo["re_noge"]), 4)} to {sg(max(mo["re_noge"]), 4)} 1/s).',

        'A three-loop controller, comprising an altitude outer loop, a dynamic-surface attitude '
        'inner loop and an airspeed loop, was designed, with RBF networks and tanh robust terms '
        'in the moment and drag channels. Closed-loop UUB was proved by a Lyapunov argument with '
        'an explicit residual bound. Using the kinematic identity '
        '$\\theta_d = \\gamma_c + \\alpha$, the lift-channel error is compensated automatically '
        'by angle-of-attack feedback, removing an entire network.',

        f'The discrete-time stability criterion $T_s\\Gamma_i\\|\\phi_i\\|^2 < k_i$ was derived, '
        f'which explains why the moment-channel adaptation gain ({n(0.005, 3)}) is three orders '
        f'of magnitude smaller than the drag-channel gain ({n(3.0, 1)}): the dimensional factors '
        f'of the two regression vectors differ by about 795.',

        f'Simulations showed that, with significant ground-effect mismatch, RAM effect and lift '
        f'nonlinearity, the adaptive controller reduces the height RMS error from '
        f'{n(sc["s1_di_rob"]["h_rms"], 4)} m to {n(sc["s1_adaptive"]["h_rms"], 4)} m '
        f'(a factor of {n(sc["s1_improve"], 1)}) and raises the Monte-Carlo pass rate from '
        f'{n(mc["pass_no_pct"], 1)}% to {n(mc["pass_ad_pct"], 1)}%, while maintaining safe flight '
        f'at 0.06 m, under measurement noise and in moderate gusts. With the final gains the '
        f'largest sampled closed-loop pole modulus is '
        f'$\\max|z| = {n(M["clp"]["final_maxabsz"], 5)} < 1$.',
    ]))
    h2('Limitations and Future Work')
    add(('bullet', [
        'The aerodynamic model is quasi-steady and linear and neglects unsteady ground-effect '
        'hysteresis and high-angle-of-attack separation; CFD studies of pitching oscillation and '
        'rapid height variation are recommended to calibrate the dynamic derivatives and to test '
        'the validity of the quasi-steady assumption.',
        'The ground-effect parameters were calibrated to the trends of published data rather than '
        'to this specific configuration. Once CFD calibration is available the values can be '
        'written into the nominal model, reducing both the mismatch and the adaptation burden.',
        f'In a severe vertical gust ($W_g = 3.0$ m/s) the controller still touches down, showing '
        f'that the envelope of this configuration is sensitive to vertical gusts; gust alleviation '
        f'(for example direct-lift control) and trajectory planning are possible remedies.',
        'Only the longitudinal channel is considered; lateral-directional and trajectory tracking '
        'remain for future work, for which a decoupled adaptive design can be extended.',
        'The robust boundary-layer thicknesses and adaptation gains are still tuned from nonlinear '
        'closed-loop indices; a more systematic design could use $\\mu$-synthesis or an '
        '$\\mathcal{L}_1$ adaptive framework.',
    ]))

    if level >= MINLV['appendix']:
        h1('Appendix: Controller Tuning Parameters')
        add(('table', {
            'headers': ['Parameter', 'Symbol', 'Value', 'Parameter', 'Symbol', 'Value'],
            'rows': [
                ['Altitude loop gain', '$k_h$', '2.00 1/s', 'Pitch loop gain', '$k_\\theta$', '3.20 1/s'],
                ['Height-rate damping', '$k_{hd}$', '0.80', 'Pitch-rate gain', '$k_q$', '6.00 1/s'],
                ['Flight-path filter', '$\\tau_g$', '0.010 s', 'Pitch command filter', '$\\tau_\\theta$', '0.100 s'],
                ['Rate command filter', '$\\tau_q$', '0.010 s', 'Airspeed loop gain', '$k_V$', '1.53 1/s'],
                ['Airspeed integral gain', '$k_{IV}$', '0.42 1/s$^2$', 'Moment channel gain', '$\\Gamma_1$', '0.005'],
                ['Drag channel gain', '$\\Gamma_2$', '3.0', '$e$-modification', '$\\nu_e$', '0.50'],
                ['Moment robust gain', '$\\eta_r$', '2.50 rad/s$^2$', 'Moment boundary layer', '$\\Phi_r$', '0.80 rad/s'],
                ['Speed robust gain', '$\\eta_V$', '1.50 m/s$^2$', 'Speed boundary layer', '$\\Phi_V$', '1.00 m/s'],
                ['Weight projection bound', '$W_{\\max}$', '12.0', 'Pitch command limit', '$\\theta_{\\max}$', '$20^{\\circ}$'],
                ['Flight-path limit', '$\\gamma_{\\max}$', '$12^{\\circ}$', 'RBF nodes', '$N_1 / N_2$', '75 / 64'],
            ],
            'key': 'tuning', 'caption': 'Final controller tuning parameters',
            'widths': [2.6, 1.4, 2.2, 2.6, 1.4, 2.2], 'font_size': 8.5,
            'aligns': ['left', 'center', 'center', 'left', 'center', 'center'],
        }))

    h1('References')
    add(('refs', refs))
    return B
