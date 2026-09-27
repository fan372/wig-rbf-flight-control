# WIG-RBF-Flight-Control

**小型地效飞行器（WIG UAV）纵向 RBF 神经网络自适应飞行控制 —— 建模、稳定性机理与仿真验证**

*RBF neural-network adaptive longitudinal flight control for a wing-in-ground-effect UAV:
modelling, height-instability mechanism and simulation validation.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MATLAB](https://img.shields.io/badge/MATLAB-R2025b-orange.svg)](https://www.mathworks.com)
[![Python](https://img.shields.io/badge/Python-3.8%2B%20(stdlib%20only)-blue.svg)](tools)
[![Docs](https://img.shields.io/badge/docs-中文%20%7C%20English-green.svg)](#english)

---

## 这个仓库是什么

一架翼展 2.40 m、质量 12 kg、巡航高度只有 0.05 ~ 0.50 m 的小型地效无人机，
它的**整个使用包线都在强地效区里**。地效给了它高得多的升阻比，同时也带来两个
常规飞机没有的稳定性问题：

| 问题 | 本仓库的定量结论 |
|---|---|
| **地效高度静稳定性为负** | 全包线内 $\partial M/\partial h = +1.06 \sim +14.90\ \mathrm{N\cdot m/m}$ 恒为正。分量分解表明**平尾下洗项是主因**（占总量的 95% ~ 106%），机翼项反而是稳定因素 |
| **浮沉-高度耦合模态失稳** | 有地效时低频模态实部 $+0.14 \sim +0.49\ \mathrm{s^{-1}}$、最低阻尼比 $-0.93$；**等效关闭地效后回到临界稳定**，证明失稳完全由地效引起 |

本仓库给出完整的**建模 → 机理分析 → 控制器设计 → 仿真验证**链路，并且：

* 每一张图、每一个日志都能由 `run_all` 从零复现；
* 论文与文档中的**每一个数字都取自 `results/log_*.txt`**，不存在"手工填进去的数"；
* 附带一个 **MATLAB 单元测试套件**（`tests/run_tests.m`），校验的是理论所依赖的
  **不变量**（配平残差、$\partial M/\partial h$ 分解闭合性、投影算子有界性、
  采样闭环极点等），而不是"跑一遍不报错"。

---

## 一分钟上手

```matlab
cd src
addpath(pwd)

run_00_smoke     % 自检：参数、地效因子、配平、8 s 闭环        （~4 s）
run_all          % 全部算例：分析 + 场景 + 蒙特卡洛 + Simulink + 诊断（~5~10 min）
```

> `run_all` 的耗时主要来自 60 组蒙特卡洛（约 3 min）与闭环极点分析中每个工况
> 60 s 的暖启动仿真；实际时长随机器性能变化。

输出：

| 产物 | 位置 |
|---|---|
| UTF-8 文本日志（15 份） | `results/log_*.txt` |
| 仿真图（12 张，200 dpi） | `figures/fig*.png`（中文标注）、`figures_en/fig*.png`（英文标注） |
| Simulink 模型 | `models/wig_adaptive_fcs.slx`（由脚本生成，不纳入版本控制） |

单独运行：

| 命令 | 内容 | 产物 |
|---|---|---|
| `run_00_smoke` | 自检冒烟测试 | `log_smoke.txt` |
| `run_analysis` | 地效特性 / 配平 / 纵向模态 | `fig1~fig3` |
| `run_00_mdh` | **$\partial M/\partial h$ 分量分解**（本文机理分析的核心） | `log_mdh.txt`、`fig12_mdh` |
| `run_scenarios` | 场景仿真与消融对比 | `fig4~fig9` |
| `run_montecarlo` | 60 组随机摄动统计 | `fig10` |
| `run_simulink` | 构建 Simulink 模型并与脚本交叉验证 | `wig_adaptive_fcs.slx`、`fig11` |
| `run_00_stab` | 稳定性导数与地效影响诊断 | `log_stab.txt` |
| `run_00_clp` | 采样闭环极点谱（出厂增益 + 历史增益对照） | `log_clp.txt` |
| `run_00_cfdfit` | ANSYS CFD 数据接口往返自检 | `log_cfdfit.txt` |

> `run_00_chk`、`run_00_chk2`、`run_00_dbg`、`run_00_opt`、`run_00_lag`、`run_00_tune`
> 是调试期诊断脚本，需单独运行（较慢）；它们对应的日志同样随仓库提供。

> **Simulink 模型说明**：`.slx` 的被控对象与控制器以基础工作区变量
> `p_nom` / `p_obj` / `x0_sim` / `refdata` 为参数，这些变量由
> `build_simulink_model.m` 写入。**直接双击打开 `.slx` 前请先运行一次 `run_simulink`**，
> 否则会提示变量未定义。

---

## 对象与控制器

**对象**：翼展 $b = 2.40$ m、弦长 $c = 0.40$ m、面积 $S = 0.96\ \mathrm{m^2}$、
质量 $m = 12$ kg、俯仰惯量 $I_{yy} = 1.15\ \mathrm{kg\cdot m^2}$、
巡航 $V_0 = 18$ m/s、地效飞行高度 $h = 0.05 \sim 0.50$ m（$h/b = 0.021 \sim 0.208$）。

**地效气动模型**：以"诱导下洗保留系数" $\kappa(h)$ 表征地效强度，

$$\kappa(h) = \frac{x^{n}}{A + x^{n}}, \qquad x = \frac{h}{b}, \qquad A = 0.0641,\ n = 1.4622$$

由此修正诱导阻力 $C_{Di} = C_L^2\kappa/(\pi AR e)$ 与有效升力线斜率
$a_w = a_0/[1 + a_0\kappa/(\pi AR e)]$。$h = 0.05$ m 处诱导阻力降至自由空气的 5.2%、
升力线斜率提高 34.3%；$h = 0.50$ m 处升力线斜率仍提高 11.7%。

**不确定性**：控制器使用"名义模型"，被控对象为"真实对象"，二者之间人为设置
地效强度失配（$A$: 0.0641 → 0.045，$n$: 1.4622 → 1.300）、RAM 效应（翼下高压区
附加升力与附加低头力矩）、升力非线性软化与气动系数摄动，用来模拟
"工程估算式未经 CFD 标定"的典型情形。配平点失配量为 $|\Delta M| \le 0.87\ \mathrm{N\cdot m}$、
$|\Delta L|$ 最大 13.89 N（占重量 11.8%）。

**控制器架构**（三层串级）：

```
  h_c ──►┌──────────────┐ γ_c ┌──────────────┐ δ_ec ┌────────────┐
         │ 高度外环      │────►│ 姿态内环      │─────►│ 舵机 + 对象 │──► h
         │ PD(高度+高度率)│     │ 动态面 DSC    │      │ 7 阶纵向    │
         └──────────────┘     │ + 动态逆      │      └────────────┘
                              │ + RBF 网络 uM │             │
                              │ + 鲁棒项 u_r  │             │
                              └──────────────┘             │
  V_c ──►┌──────────────┐ δ_t ┌──────────────┐             │
         │ 速度回路      │────►│ 发动机 + 对象 │◄────────────┘
         │ PI + 动态逆   │     └──────────────┘
         │ + RBF uD + 鲁棒│
         └──────────────┘
```

* **RBF 网络 1（力矩通道）**：输入 $[\alpha, q, h]$，$5\times3\times5 = 75$ 节点
* **RBF 网络 2（阻力通道）**：输入 $[\alpha, V, h]$，$4\times4\times4 = 64$ 节点
* **升力通道不需要网络**：由 $\theta_d = \gamma_c + \alpha$ 中的迎角反馈自然补偿
  （因为 $\gamma = \theta - \alpha$ 是运动学恒等式，与模型无关）
* **权值自适应律**：投影算子保证 $\|W\| \le W_{\max}$，$e$-修正防止漂移
* **稳定性**：Lyapunov 方法证明闭环**一致最终有界（UUB）**，给出显式残差界

### 本文给出的离散实现判据

自适应律按 200 Hz 前向欧拉离散。把误差通道与权值通道联立线性化
（其余动力学冻结），由 Jury 判据得

$$T_s\,\Gamma_i\left\|\phi_i\right\|^{2} < k_i$$

| 通道 | 量纲因子 $g_i$ | $\|\phi_{i,rbf}\|^2$ | $T_s\Gamma_i\|\phi_i\|^2$ | 通道增益 $k_i$ | 裕度比 |
|---|---|---|---|---|---|
| 力矩 | $66.265\ \mathrm{s^{-2}}$ | 5.3943 | 0.5922 | $k_q = 6.00$ | 10.1 |
| 阻力 | $0.083333\ \mathrm{kg^{-1}}$ | 5.3744 | $5.598\times10^{-4}$ | $k_V = 1.53$ | 2733 |

这条判据解释了为什么力矩通道的自适应增益（$\Gamma_1 = 0.005$）比阻力通道
（$\Gamma_2 = 3.0$）小三个数量级——两个回归向量的量纲因子相差约 795 倍，
**直接比较增益数值大小会得出完全错误的结论**。

---

## 主要结果

| 指标 | RBF 自适应 | 仅动态逆+鲁棒 | 纯动态逆 |
|---|---|---|---|
| 高度跟踪误差 RMS / m | **0.0100** | 0.1938 | 0.2119 |
| 最低离地高度 / m | **0.1000（未触地）** | 0（触地） | 0（触地） |
| 速度跟踪误差 RMS / (m/s) | **0.0126** | 0.0605 | 0.1301 |
| 蒙特卡洛通过率（60 组） | **86.7 %** | — | 40.0 % |
| 高度误差 RMS 中位数 / m | **0.01040** | — | 0.22322 |

* 高度跟踪误差改善 **19.4 倍**，蒙特卡洛中位数改善 **21.5 倍**；
* 全部 8 组参数摄动工况均未触地（高度 RMS 0.0048 ~ 0.0425 m）；
* 中度阵风（1.5 m/s）与 Dryden 湍流下均安全；**严酷阵风（3.0 m/s）下会触地**——
  这一失败边界在文档中如实给出，不做回避；
* 最终整定参数下采样闭环最大极点模 $\max|z| = 0.99942 < 1$（平衡点残差 $6.6\times10^{-17}$）；
* Simulink 模型与纯 MATLAB 脚本的最大轨迹偏差为高度 $1.3\times10^{-3}$ m。

---

## 目录结构

```
wig-rbf-flight-control/
├── src/                         MATLAB 源码（61 个 .m）
│   ├── 【建模层】wig_params / wig_truth_params / wig_ge / wig_aero
│   │             wig_dynamics / wig_trim / wig_linearize
│   ├── 【机理分析】wig_mdh_decomp.m          ★ dM/dh 分量分解
│   ├── 【控制层】wig_rbf_init / wig_rbf_phi / wig_proj / wig_ctrl_init
│   │             wig_ctrl_update.m           ★ RBF 自适应控制器核心
│   │             wig_ctrl_pack / wig_ctrl_unpack
│   ├── 【仿真层】wig_simulate / wig_metrics / wig_closedloop_eig
│   ├── 【Simulink】msfcn_wig_plant / msfcn_wig_ctrl / build_simulink_model
│   ├── 【算例入口】run_all + run_analysis / run_scenarios / run_montecarlo
│   │               run_simulink / run_00_mdh / run_00_stab / run_00_clp ...
│   └── 【CFD 接口】wig_ge_fit_cfd.m
├── tests/run_tests.m            ★ 不变量单元测试（fast 模式 68 项）
├── models/                      Simulink 模型（由 run_simulink 生成）
├── figures/                     仿真图 12 张（中文标注）
├── figures_en/                  同一批图的英文标注版（由 run_figs_en 生成，供英文论文使用）
├── results/                     全部 UTF-8 文本日志
├── docs/
│   ├── paper/                   论文（完整版：中文 Word/PDF + 英文 IEEE LaTeX/PDF）
│   │                            ⚠ 公开版已去掉作者署名，只保留正文与图表
│   ├── report/                  技术报告（Word + PDF）
│   └── tutorial/                零基础详解（PDF + Markdown 源）
├── tools/word/                  .docx 生成工具链（纯 Python 标准库 + OMML）
├── tools/pdf/                   PDF 排版引擎（纯 Python 标准库，字体内嵌 + 书签）
└── ansys/                       CFD 工作说明与数据接口模板
```

---

## 环境要求

| 组件 | 版本 / 说明 |
|---|---|
| MATLAB | R2025b（全部代码在此版本下运行通过） |
| Simulink | 仅 `run_simulink` 需要 |
| Optimization Toolbox | `fsolve`（缺失时 `wig_trim` 自动回退到自研阻尼牛顿法） |
| Statistics and Machine Learning Toolbox | `prctile`（仅 `run_montecarlo` 需要） |
| 字体 | 绘图中文标签依赖系统字体 `Microsoft YaHei` |
| Python | 3.8+，**仅标准库**（`tools/word`、`tools/pdf` 均不依赖 python-docx / reportlab） |

`tools/pdf` 的排版引擎通过 `C:\Windows\Fonts` 读取字体，因此文档工具链为 **Windows 专用**；
`src/` 下的仿真代码不含任何硬编码绝对路径，可在任意平台运行。

---

## 单元测试

```matlab
cd tests
run_tests            % 全部（含闭环极点分析与 20 s 闭环仿真）
run_tests('fast', true)   % 跳过慢测试
```

测试校验的不变量包括：地效因子值域/单调性/导数、几何与质量一致性、
名义与真实对象的配平残差、$\partial M/\partial h$ 分量分解的闭合性、
RBF 节点数与基函数性质、投影算子的权值有界性、
控制器状态 pack/unpack 的 147 维往返一致性、
数值线性化与有限差分的一致性、经典浮沉阻尼公式的量纲正确性，
以及采样闭环极点 $\max|z| < 1$。

---

## 引用

见 [`CITATION.cff`](CITATION.cff)。若在研究中使用了本仓库的模型或代码，
请同时引用配套论文（[`docs/paper/`](docs/paper/)，英文版 12 页 / 中文版 21 页，均为完整版）。
公开仓库中的论文副本已隐去作者署名与联系方式，正文、公式、图表与参考文献与投稿版一致。

## 许可证

[MIT](LICENSE)。`tools/pdf` 中的排版引擎在本仓库作者早期的私有工具基础上迭代而来，
同样以 MIT 许可发布。

## 贡献

见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。核心原则：**文档里的每个数字都必须能由
`results/log_*.txt` 复现**，改模型就同步改文档并重新生成日志。

---

<a name="english"></a>

## English

**What this repository is.** A complete, reproducible study of the longitudinal flight dynamics
and control of a small wing-in-ground-effect (WIG) UAV with a 2.40 m span, 12 kg mass and a
cruising height of only 0.05–0.50 m, so that its whole envelope lies inside the strong
ground-effect regime.

**Two stability problems, quantified here.**

1. *Negative height static stability.* The pitch-moment height derivative
   $\partial M/\partial h$ is strictly positive over the entire envelope
   ($+1.06$ to $+14.90\ \mathrm{N\cdot m/m}$). A component-wise decomposition shows that the
   **tail downwash term dominates** (95–106 % of the total) while the wing term is
   *stabilising* — so height stability should be improved through the tail layout, not by
   reshaping the wing.
2. *Unstable phugoid-height coupled mode.* With ground effect the low-frequency mode has a
   real part of $+0.14$ to $+0.49\ \mathrm{s^{-1}}$ and a damping ratio as low as $-0.93$;
   switching the ground effect off returns the mode to neutral stability, proving that the
   instability is of ground-effect origin.

**Controller.** A three-loop cascade: a proportional altitude outer loop with height-rate
damping, a dynamic-surface attitude inner loop with dynamic inversion, and an airspeed loop.
Two RBF networks (75 nodes on $[\alpha,q,h]$ for the moment channel; 64 nodes on $[\alpha,V,h]$
for the drag channel) estimate the mismatch online, backed by tanh robust terms and a
projection operator. **No lift-channel network is needed**: the kinematic identity
$\gamma=\theta-\alpha$ makes $\theta_d=\gamma_c+\alpha$ compensate lift errors automatically.
Closed-loop uniform ultimate boundedness is proved by a Lyapunov argument.

**Discrete-time design rule derived here.** For the 200 Hz forward-Euler adaptation law,
linearising the error/weight two-state system gives
$T_s\Gamma_i\|\phi_i\|^2 < k_i$. This explains why the moment-channel gain (0.005) is three
orders of magnitude smaller than the drag-channel gain (3.0): the dimensional factors of the
two regression vectors differ by about 795.

**Key results.** Height-tracking RMS error reduced from 0.1938 m to 0.0100 m (a factor of 19.4);
Monte-Carlo pass rate raised from 40.0 % to 86.7 % over 60 random parameter samples; safe flight
at 0.06 m under measurement noise and in moderate gusts. The failure boundary is reported
honestly: in a severe 3.0 m/s vertical gust the vehicle still touches down.

**Quick start.**

```matlab
cd src; addpath(pwd)
run_00_smoke     % fast self-check            (~4 s)
run_all          % full suite                 (~5-10 min)
run_tests        % invariant unit tests       (cd ../tests)
```

All documentation numbers are extracted from `results/log_*.txt`; every figure and log is
reproducible from scratch with `run_all`. See [`docs/paper/`](docs/paper/) for the paper:
the extended version in both languages (English IEEE two-column, 12 pages; Chinese
single-column, 21 pages). The copy shipped in this repository has the author block removed;
the body text, equations, tables, figures and references are identical to the submitted
manuscript.
