function [F, aux] = wig_aero(x, p, flag)
%WIG_AERO  地效飞行器纵向气动力与俯仰力矩（机翼 + 平尾 + 机体 + 推力）
%
%   [F, aux] = wig_aero(x, p, flag)
%
%   输入：
%       x    状态向量 x = [V; gam; alpha; q; h; T; de]
%       p    参数结构体（名义或真实）
%       flag 'nominal'（默认）或 'truth'
%               'nominal' —— 控制器内部使用的名义气动模型：
%                            线性升力 + 地效 Irodov 型修正
%               'truth'   —— 真实对象气动模型，额外包含：
%                            * 地效强度参数失配（p.ge_A / p.ge_n）
%                            * RAM 效应（翼下高压附加升力与附加低头力矩）
%                            * 升力非线性软化（tanh 失速）
%   输出：
%       F   = [L; D; M]
%               L  总升力 [N]（垂直速度方向，向上为正）
%               D  总阻力 [N]
%               M  绕 CG 的俯仰力矩 [N·m]（抬头为正）
%       aux 辅助量结构体（气动系数、地效因子、平尾迎角等），便于分析与绘图
%
%   机翼气动模型（详见理论分析报告第 2 章）：
%       kappa(h)  = 地效因子, 见 wig_ge.m
%       a_w(h)    = a0 / (1 + a0*kappa/(pi*AR*e))      有效升力线斜率
%       CL_w      = a_w*(alpha - aL0)
%       CDi_w     = CL_w^2 * kappa / (pi*AR*e)         诱导阻力（地效修正）
%       CD_w      = CD0 + CDi_w
%       eps(h)    = (eps0 + eps_a*alpha) * kappa       平尾处下洗角（地效修正）
%       alpha_t   = alpha + it - eps + q*lt/V          平尾当地迎角
%       CL_t      = a_t*(alpha_t - aL0t) + a_de*de     平尾升力系数（含升降舵）
%   力矩计算统一采用 M = z*Fx - x*Fz（x 向前为正、z 向下为正的机体轴）。

if nargin < 3
    flag = 'nominal';
end
truth = p.is_truth || strcmpi(flag, 'truth');

V     = max(x(1), 0.5);     % 防止除零
alpha = x(3);
q     = x(4);
h     = max(x(5), 0.0);
T     = x(6);
de    = x(7);

qbar = 0.5 * p.rho * V * V;

%% ---------------- 地效因子 ----------------
kap_w = wig_ge(h,           p.b,  p);   % 机翼处
h_t   = h + p.dz_t;                     % 平尾离地高度（尾翼抬高）
kap_t = wig_ge(h_t,         p.bt, p);   % 平尾处

%% ---------------- 有效升力线斜率 ----------------
aw = p.a0  / (1 + p.a0  * kap_w / (pi * p.AR  * p.e));
at = p.a0t / (1 + p.a0t * kap_t / (pi * p.ARt * p.et));

%% ---------------- 机翼 ----------------
CLw_lin = aw * (alpha - p.aL0);

CLram = 0;  dCLnl = 0;      % 仅真实对象含 RAM 与失速软化
if truth
    CLram = p.k_ram / (1 + (h / p.h_ram)^2);
    CLtot = p.CLmax * tanh((CLw_lin + CLram) / p.CLmax);
    dCLnl = CLtot - CLw_lin - CLram;
end

CDi_w = CLw_lin^2 * kap_w / (pi * p.AR * p.e);
CDw   = p.CD0 + CDi_w;

Lw   = qbar * p.S * CLw_lin;
Dw   = qbar * p.S * CDw;
Lram = qbar * p.S * CLram;
Lnl  = qbar * p.S * dCLnl;

%% ---------------- 平尾 ----------------
eps_t   = (p.eps0 + p.eps_a * alpha) * kap_w;
alpha_t = alpha + p.it - eps_t + q * p.lt / V;

CLt = at * (alpha_t - p.aL0t) + p.a_de * de;
CDt = p.CD0t + CLt^2 / (pi * p.ARt * p.et);

qt = qbar * p.eta_t;
Lt = qt * p.St * CLt;
Dt = qt * p.St * CDt;

%% ---------------- 合力 ----------------
L = Lw + Lram + Lnl + Lt;
D = Dw + Dt;

%% ---------------- 俯仰力矩（M = z*Fx - x*Fz） ----------------
Fx_w = Lw * sin(alpha) - Dw * cos(alpha);
Fz_w = -Lw * cos(alpha) - Dw * sin(alpha);
M_w  = p.z_acw * Fx_w - p.x_acw * Fz_w + qbar * p.S * p.c * p.Cmac;

Fx_ram = Lram * sin(alpha);
Fz_ram = -Lram * cos(alpha);
M_ram  = p.z_acw * Fx_ram - p.x_ram * Fz_ram;

Fx_nl = Lnl * sin(alpha);
Fz_nl = -Lnl * cos(alpha);
M_nl  = p.z_acw * Fx_nl - p.x_acw * Fz_nl;

Fx_t = Lt * sin(alpha_t) - Dt * cos(alpha_t);
Fz_t = -Lt * cos(alpha_t) - Dt * sin(alpha_t);
M_t  = (-p.dz_t) * Fx_t - (-p.lt) * Fz_t;

M_T = p.z_T * (T * cos(p.i_T));

M_fus = qbar * p.S * p.c * (p.Cm0f + p.Cmaf * alpha);

M = M_w + M_ram + M_nl + M_t + M_T + M_fus;

%% ---------------- 输出 ----------------
F = [L; D; M];

if nargout > 1
    aux.qbar    = qbar;
    aux.kap_w   = kap_w;
    aux.kap_t   = kap_t;
    aux.aw      = aw;
    aux.at      = at;
    aux.CLw     = CLw_lin;
    aux.CLt     = CLt;
    aux.CDw     = CDw;
    aux.CDt     = CDt;
    aux.CLram   = CLram;
    aux.eps_t   = eps_t;
    aux.alpha_t = alpha_t;
    aux.Lw      = Lw;
    aux.Lt      = Lt;
    aux.Dw      = Dw;
    aux.Dt      = Dt;
    aux.M_w     = M_w;
    aux.M_t     = M_t;
    aux.M_ram   = M_ram;
    aux.M_nl    = M_nl;
    aux.M_T     = M_T;
    aux.M_fus   = M_fus;
    aux.Lnl     = Lnl;
    aux.Lram    = Lram;
    aux.truth   = truth;
end

end
