function [u, ctrl, dbg] = wig_ctrl_update(xm, ref, ctrl, p)
%WIG_CTRL_UPDATE  地效飞行器 RBF 神经网络自适应飞控 —— 离散单步更新
%
%   [u, ctrl, dbg] = wig_ctrl_update(xm, ref, ctrl, p)
%
%   输入
%       xm   量测状态 x = [V; gam; alpha; q; h; T; de]
%       ref  参考指令 ref = [h_c; hd_c; V_c; Vd_c]
%       ctrl 控制器内部状态（由 wig_ctrl_init 生成，本函数返回更新值）；
%            其中 ctrl.gam_c 是【航迹倾角指令一阶滤波状态】，也是推力重力分量
%            前馈的唯一来源：
%                gff = p.m*p.g*sin(ctrl.gam_c)   （p.ctrl.use_grav_ff = true）
%                gff = 0                          （p.ctrl.use_grav_ff = false）
%            前馈刻意取自【指令】航迹角而非量测航迹角 gam：若用 sin(gam)，会形成
%            gam -> T_cmd -> T -> V -> L -> dgam/dt -> gam 的正反馈回路
%            （增益 m*g），把短周期/浮沉耦合模态推到右半平面。
%       p    参数结构体（必须为【名义】参数，控制器内部模型）
%   输出
%       u    [de_cmd; dt_cmd] 升降舵指令 [rad]、油门指令 [0,1]
%       dbg  调试结构体（误差、中间指令、网络输出、权值范数等）
%
%   ------------------------------------------------------------------
%   控制结构（三层，详见理论分析报告第 4 章）
%
%   ① 高度外环（运动学）：由高度误差与高度率误差生成航迹倾角指令
%         e_h    = hf - h_c                       （hf 为量测滤波高度）
%         hd_act = Vf*sin(gam)                    （高度率，直接合成，无需数值微分）
%         gam_d  = asin( sat( (hd_c - k_h*e_h - k_hd*(hd_act - hd_c))/max(Vf,3),
%                             sin(gam_max) ) )
%         经一阶指令滤波 tau_g * d(gam_c)/dt = sat(gam_d) - gam_c
%
%   ② 姿态内环（动态面 + 动态逆 + RBF + 鲁棒项）：
%         theta_d = gam_c + alpha
%         tau_th * d(theta_c)/dt = sat(theta_d) - theta_c
%         q_d     = d(theta_c)/dt - k_th*(theta - theta_c)
%         tau_q  * d(q_cf)/dt    = sat(q_d) - q_cf          （动态面滤波）
%         e_q     = q - q_cf
%         nu      = d(q_cf)/dt - k_q*e_q                    期望角加速度
%         名义模型： dq/dt = f0(x) + b*de,  f0 = M_nom(x,de=0)/Iyy, b = M_de/Iyy
%         de_cmd  = sat( ( nu - f0 - uM - u_r ) / b, de_max )
%         其中 uM = W1'*phi1 为 RBF 对力矩失配的在线估计（单位 rad/s^2），
%              u_r = eta_r*tanh(e_q/Phi_r) 为鲁棒补偿项。
%         自适应律： dW1/dt = Proj( Gam1*( phi1*e_q - nu_e*|e_q|*W1 ) )
%
%   ③ 速度回路（推力动态逆 + RBF + 鲁棒项 + 积分）：
%         e_V = Vf - V_c
%         T_cmd = [ m*(dV_des + uD - u_rV) + D_nom + gff ] / cos(alpha+i_T)
%                 gff = m*g*sin(ctrl.gam_c)（p.ctrl.use_grav_ff 为 true 时，否则 0）
%         dV_des = Vd_c - k_V*e_V - k_IV*IV,   dIV/dt = e_V（限幅）
%         自适应律： dW2/dt = Proj( -Gam2*( phi2*e_V + nu_e*|e_V|*W2 ) )
%
%   注：Proj(·) 即 wig_proj(·)，按权值范数上界 p.ctrl.nn.Wmax 做投影；
%       两通道自适应律符号相反，源于 uM 以减号、uD 以加号进入各自控制律
%       （推导见本文件第 5 节注释与理论分析报告 4.4 节）。
%
%   抗积分饱和：当升降舵（或油门）指令超出限幅时冻结对应通道的自适应更新，
%   避免执行器饱和期间权值被"错误误差"持续激励。
%   ------------------------------------------------------------------

Ts = p.sim.Ts;

V     = xm(1);
gam   = xm(2);
alpha = xm(3);
q     = xm(4);
h     = xm(5);
T     = xm(6);

Ts_ = max(Ts, 1e-6);

%% ================= 0. 量测一阶滤波 =================
if isempty(ctrl.xf)
    ctrl.xf = xm([1 3 4 5]);
end
tau_f = max(p.sens.tau_f, 1e-4);
ctrl.xf = ctrl.xf + (Ts_/tau_f) * (xm([1 3 4 5]) - ctrl.xf);
Vf = ctrl.xf(1);  alf = ctrl.xf(2);  qf = ctrl.xf(3);  hf = ctrl.xf(4);
theta = gam + alf;          % 与指令通道保持一致，使用滤波后迎角合成俯仰角

h_c  = ref(1);  hd_c = ref(2);  V_c = ref(3);  Vd_c = ref(4);

qbar = 0.5 * p.rho * Vf * Vf;

%% ================= 1. RBF 神经网络 =================
% --- 通道 1：力矩 ---
z1   = wig_norm([alf; qf; hf], ctrl.nn.rng1);
ph1r = wig_rbf_phi(z1, ctrl.nn.C1, ctrl.nn.sig1);
phi1 = ph1r * (qbar * p.S * p.c / p.Iyy);        % 单位: 1/s^2 per weight
uM   = ctrl.W1' * phi1;                           % [rad/s^2]

% --- 通道 2：阻力 ---
z2   = wig_norm([alf; Vf; hf], ctrl.nn.rng2);
ph2r = wig_rbf_phi(z2, ctrl.nn.C2, ctrl.nn.sig2);
phi2 = ph2r / p.m;                                % 单位: m/s^2 per weight
uD   = ctrl.W2' * phi2;                           % [m/s^2]

if ~p.ctrl.enable_nn
    uM = 0;  uD = 0;
end

%% ================= 2. 高度外环 =================
% 地效区纵向外形存在"浮沉-高度"耦合不稳定（见报告 3.4 节：真实对象在
% h≈0.2~0.5 m 处低频模态阻尼比约 -0.8），因此高度外环除比例项外必须引入
% 高度率阻尼项（用 hdot = V*sin(gam) 直接合成，无需数值微分）：
%     hdot_cmd = hdot_c - k_h*e_h - k_hd*(hdot - hdot_c)
%     gam_d    = asin( sat( hdot_cmd / V, sin(gam_max) ) )
e_h    = hf - h_c;
hd_act = Vf * sin(gam);
if p.ctrl.enable_alt
    arg   = (hd_c - p.ctrl.k_h * e_h - p.ctrl.k_hd * (hd_act - hd_c)) / max(Vf, 3.0);
    gam_d = asin(wig_sat(arg, sin(p.ctrl.gam_max)));
else
    gam_d = 0;                                    % 姿态保持模式（对比用）
end
gam_dot_c = (wig_sat(gam_d, p.ctrl.gam_max) - ctrl.gam_c) / p.ctrl.tau_g;

%% ================= 3. 姿态内环（动态面 DSC） =================
e_th = theta - ctrl.th_c;
theta_d   = wig_sat(ctrl.gam_c + alf, p.ctrl.th_max);   % 姿态限幅（包线保护）
th_dot_c  = (wig_sat(theta_d, 0.80) - ctrl.th_c) / p.ctrl.tau_th;

q_d  = th_dot_c - p.ctrl.k_th * e_th;
e_q  = qf - ctrl.q_cf;
q_dot_cf = (wig_sat(q_d, 6.0) - ctrl.q_cf) / p.ctrl.tau_q;

nu = q_dot_cf - p.ctrl.k_q * e_q;

% --- 名义模型：零舵偏力矩与操纵导数 ---
xtmp = [V; gam; alpha; q; h; T; 0];
Fnom = wig_aero(xtmp, p, 'nominal');
Mn0  = Fnom(3);
Dnom = Fnom(2);
f0   = Mn0 / p.Iyy;

kap_w   = wig_ge(h, p.b, p);
eps_t   = (p.eps0 + p.eps_a * alpha) * kap_w;
alpha_t = alpha + p.it - eps_t + q * p.lt / max(V, 0.5);
qt      = qbar * p.eta_t;
Mde     = -(p.lt * cos(alpha_t) + p.dz_t * sin(alpha_t)) * qt * p.St * p.a_de;
b       = Mde / p.Iyy;

if abs(b) < 1e-8
    b = -1e-8;                                    % 数值保护（极低速）
end

% --- 鲁棒项 ---
if p.ctrl.enable_rob
    ur = p.ctrl.eta_r * tanh(e_q / p.ctrl.Phi_r);
else
    ur = 0;
end

de_unsat = (nu - f0 - uM - ur) / b;
de_cmd   = wig_sat(de_unsat, p.de_max);
sat_e    = abs(de_unsat) >= p.de_max;

%% ================= 4. 速度回路 =================
% 推导（注意鲁棒项的符号）：
%     Vdot = dV_des + uD + u_rV - DeltaD/m
%   为使误差动态中出现 "-u_rV"（与力矩通道一致，从而 Lyapunov 交叉项对消），
%   控制律中必须以【减号】引入鲁棒项。若误写为加号，u_rV = eta_V*tanh(e_V/Phi_V)
%   将变成正反馈，等效增益 +eta_V/Phi_V 抵消速度环比例增益，导致推力-速度
%   回路失去阻尼。run_00_clp 的敏感性分析给出了直接证据：把鲁棒项关掉后，
%   闭环最大极点模由 0.99942 升到 1.00415，主导极点变为 s = +0.828 1/s
%   且由推力状态 T 主导。
e_V = Vf - V_c;

IV_new = wig_sat(ctrl.IV + Ts_ * e_V, p.ctrl.IV_max);
dV_des = Vd_c - p.ctrl.k_V * e_V - p.ctrl.k_IV * IV_new;

if p.ctrl.enable_rob
    urV = p.ctrl.eta_V * tanh(e_V / p.ctrl.Phi_V);
else
    urV = 0;
end

ca = cos(alpha + p.i_T);
if abs(ca) < 0.2
    ca = sign(ca) * 0.2;
end

% 重力分量前馈：必须取自【指令】航迹角而非量测航迹角。
% 若用 sin(gam_meas)，则形成 gam -> T_cmd -> T -> V -> L -> gamdot -> gam 的
% 正反馈回路（增益 mg = 117.7 N/rad），在发动机滞后（tau_T）作用下把
% 短周期/浮沉耦合模态推向不稳定（见 run_00_clp 的敏感性分析：
% 关闭速度环比例与积分时 max|z| 达到 1.00000，主导状态为 IV）。
if p.ctrl.use_grav_ff
    gff = p.m * p.g * sin(ctrl.gam_c);
else
    gff = 0;
end
T_cmd = (p.m * (dV_des + uD - urV) + Dnom + gff) / ca;

dt_unsat = (T_cmd - p.Tmin) / (p.Tmax - p.Tmin);
dt_cmd   = wig_sat(dt_unsat, 0.0, 1.0);
sat_t    = (dt_unsat <= 0.0) || (dt_unsat >= 1.0);

%% ================= 5. 自适应律（投影 + e-修正） =================
% 注意两个通道自适应律的符号相反，原因在于估计量在控制律中的位置不同：
%   力矩通道： de = (nu - f0 - uM ...)/b ，uM 以"减号"进入 =>  W1dot = +Gam1*phi1*e_q
%              qdot = nu + df - uM  =>  e_qdot = -kq*e_q + (df - uM)
%   阻力通道： T*cos = m*(dVdes + uD) + ... ，uD 以"加号"进入 =>  W2dot = -Gam2*phi2*e_V
%              Vdot = dVdes + uD - dD/m  =>  e_Vdot = ... + (uD - dD/m)
%   两者均使 Lyapunov 函数的交叉项严格对消（详见理论分析报告 4.4 节）。
nu_e = p.ctrl.nn.nu_e;
if p.ctrl.enable_nn
    if ~sat_e
        tau1 = p.ctrl.nn.Gam1 * (phi1 * e_q - nu_e * abs(e_q) * ctrl.W1);
        ctrl.W1 = wig_proj(ctrl.W1, tau1, p.ctrl.nn.Wmax, Ts_);
    end
    if ~sat_t
        tau2 = -p.ctrl.nn.Gam2 * (phi2 * e_V + nu_e * abs(e_V) * ctrl.W2);
        ctrl.W2 = wig_proj(ctrl.W2, tau2, p.ctrl.nn.Wmax, Ts_);
    end
end

%% ================= 6. 更新滤波器状态 =================
ctrl.gam_c = ctrl.gam_c + Ts_ * gam_dot_c;
ctrl.th_c  = ctrl.th_c  + Ts_ * th_dot_c;
ctrl.q_cf  = ctrl.q_cf  + Ts_ * q_dot_cf;
ctrl.IV    = IV_new;

%% ================= 7. 输出 =================
u = [de_cmd; dt_cmd];

dbg.e_h     = e_h;
dbg.hd_act  = hd_act;
dbg.e_th    = e_th;
dbg.e_q     = e_q;
dbg.e_V     = e_V;
dbg.gam_d   = gam_d;
dbg.gam_c   = ctrl.gam_c;
dbg.theta_d = theta_d;
dbg.th_c    = ctrl.th_c;
dbg.q_d     = q_d;
dbg.q_cf    = ctrl.q_cf;
dbg.nu      = nu;
dbg.uM      = uM;
dbg.uD      = uD;
dbg.ur      = ur;
dbg.urV     = urV;
dbg.de_unsat= de_unsat;
dbg.de_cmd  = de_cmd;
dbg.dt_cmd  = dt_cmd;
dbg.IV      = ctrl.IV;
dbg.W1norm  = norm(ctrl.W1);
dbg.W2norm  = norm(ctrl.W2);
dbg.sat_e   = sat_e;
dbg.f0      = f0;
dbg.b       = b;
dbg.Mn0     = Mn0;
dbg.Dnom    = Dnom;

end
