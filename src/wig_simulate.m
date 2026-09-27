function R = wig_simulate(scn)
%WIG_SIMULATE  地效飞行器闭环仿真引擎（定步长 RK4 + 200 Hz 离散飞控）
%
%   R = wig_simulate(scn)
%
%   scn 结构体字段：
%     .p        名义参数（控制器内部模型）
%     .pt       真实对象参数（缺省 = p）
%     .pc       控制器参数（缺省 = p，可单独覆盖控制增益/开关）
%     .Tend     仿真时长 [s]
%     .x0       初始状态（缺省：在 pt 下按 .V0/.h0 配平）
%     .V0 .h0   初始配平点（缺省取 p.V0, p.h0）
%     .ref.h    参考高度时间序列 [t, h_c]（缺省恒定）
%     .ref.V    参考速度时间序列 [t, V_c]
%     .ref.wn_h .ref.wn_V  参考指令二阶滤波器带宽（缺省 2.0 / 1.0）
%     .plant    'truth' | 'nominal'（缺省 'truth'）
%     .gust     阵风设置（缺省取 p.gust，且 enable=false）
%     .sens     量测噪声设置（缺省取 p.sens）
%     .seed     随机数种子
%
%   R 输出：
%     .t .x .u .ref .dbg .aux  时间历程（结构体数组/矩阵）
%     .scn                     回填的场景信息
%     .metrics                 跟踪性能指标（由 wig_metrics 计算）
%
%   时间推进：被控对象用定步长四阶 Runge-Kutta（dt = p.sim.dt）积分；
%   飞控计算机以 Ts = p.sim.Ts 零阶保持采样运行，与 Simulink 模型一致。

p  = scn.p;
if ~isfield(scn,'pt') || isempty(scn.pt),  pt = p;  else, pt = scn.pt; end
if ~isfield(scn,'pc') || isempty(scn.pc),  pc = p;  else, pc = scn.pc; end
if ~isfield(scn,'plant') || isempty(scn.plant), plant = 'truth'; else, plant = scn.plant; end
if ~isfield(scn,'V0') || isempty(scn.V0), V0 = p.V0; else, V0 = scn.V0; end
if ~isfield(scn,'h0') || isempty(scn.h0), h0 = p.h0; else, h0 = scn.h0; end

dt   = p.sim.dt;
Ts   = p.sim.Ts;
Tend = scn.Tend;
Nt   = round(Tend/dt) + 1;
tvec = (0:Nt-1)' * dt;

%% ================= 初始状态（按真实对象配平） =================
if isfield(scn,'x0') && ~isempty(scn.x0)
    x = scn.x0(:);
else
    trm = wig_trim(V0, h0, pt, plant);
    x = trm.x;
end
x = x(:);

%% ================= 参考指令时间序列 =================
ref_h = get_profile(scn, 'h', tvec, h0);
ref_V = get_profile(scn, 'V', tvec, V0);
wn_h  = getfield_def(scn.ref, 'wn_h', 1.2);
wn_V  = getfield_def(scn.ref, 'wn_V', 1.2);

% 二阶指令滤波器状态（临界阻尼 zeta = 1）
zh = [ref_h(1); 0];
zv = [ref_V(1); 0];

%% ================= 阵风 =================
gust = getfield_def(scn, 'gust', p.gust);
[ug, wg] = make_gust(gust, tvec, V0, getfield_def(scn,'seed',1));

%% ================= 量测噪声 =================
sens = getfield_def(scn, 'sens', p.sens);
rng_state = rng;                                  %#ok<RNG>
rng(getfield_def(scn,'seed',1) + 977);
nV = sens.sig_V  * randn(Nt,1);
na = sens.sig_a  * randn(Nt,1);
nq = sens.sig_q  * randn(Nt,1);
nh = sens.sig_h  * randn(Nt,1);
rng(rng_state);                                   %#ok<RNG>

%% ================= 控制器初始化 =================
ctrl = wig_ctrl_init(pc, x);

%% ================= 预分配 =================
nx = 7;
X    = zeros(Nt, nx);
U    = zeros(Nt, 2);
REF  = zeros(Nt, 4);
KAP  = zeros(Nt, 4);      % kap_w, kap_t, CL, CD
DBG  = zeros(Nt, 18);
GUST = [ug, wg];
auxrec = zeros(Nt, 8);    % L, D, M, Lw, Lt, Dw, Dt, qbar

%% ================= 主循环 =================
u = [0;0];
next_u = 0.0;
ref = [zh(1); zh(2); zv(1); zv(2)];

for k = 1:Nt
    t = tvec(k);

    %% --- 参考指令二阶滤波（欧拉，dt 很小精度足够） ---
    zh = zh + dt * [zh(2); wn_h^2*(ref_h(k) - zh(1)) - 2*wn_h*zh(2)];
    zv = zv + dt * [zv(2); wn_V^2*(ref_V(k) - zv(1)) - 2*wn_V*zv(2)];
    ref = [zh(1); zh(2); zv(1); zv(2)];

    %% --- 飞控计算机采样（零阶保持） ---
    if t >= next_u - 1e-12
        xm = x;
        if sens.enable
            xm(1) = xm(1) + nV(k);
            xm(3) = xm(3) + na(k);
            xm(4) = xm(4) + nq(k);
            xm(5) = max(xm(5) + nh(k), 0.0);
        end
        [u, ctrl, dbg] = wig_ctrl_update(xm, ref, ctrl, pc);
        next_u = next_u + Ts;

        DBG(k,:) = [dbg.e_h, dbg.e_th, dbg.e_q, dbg.e_V, dbg.gam_d, ...
                    dbg.theta_d, dbg.th_c, dbg.q_cf, dbg.uM, dbg.uD, ...
                    dbg.ur, dbg.urV, dbg.W1norm, dbg.W2norm, ...
                    double(dbg.sat_e), dbg.IV, dbg.de_unsat, dbg.dt_cmd];
    else
        DBG(k,:) = DBG(max(k-1,1), :);
    end

    %% --- 记录 ---
    X(k,:) = x';
    U(k,:) = u';
    REF(k,:) = ref';
    GUST(k,:) = [ug(k), wg(k)];

    F  = wig_aero(x, pt, plant);
    [~, ax] = wig_aero(x, pt, plant);
    auxrec(k,:) = [F(1), F(2), F(3), ax.Lw, ax.Lt, ax.Dw, ax.Dt, ax.qbar];
    KAP(k,:) = [ax.kap_w, ax.kap_t, ax.CLw, ax.CDw];

    %% --- RK4 积分（控制量保持） ---
    if k < Nt
        g = [ug(k); wg(k)];
        k1 = wig_dynamics(x,              u, pt, plant, g);
        k2 = wig_dynamics(x + 0.5*dt*k1,  u, pt, plant, g);
        k3 = wig_dynamics(x + 0.5*dt*k2,  u, pt, plant, g);
        k4 = wig_dynamics(x + dt*k3,      u, pt, plant, g);
        x  = x + (dt/6)*(k1 + 2*k2 + 2*k3 + k4);
        x(1) = max(x(1), 1.0);
        x(5) = max(x(5), 0.0);
    end
end

%% ================= 输出组装 =================
R.t    = tvec;
R.x    = X;
R.u    = U;
R.ref  = REF;
R.dbg  = DBG;
R.gust = GUST;
R.kap  = KAP;
R.aux  = auxrec;
R.V    = X(:,1);
R.gam  = X(:,2);
R.alpha= X(:,3);
R.q    = X(:,4);
R.h    = X(:,5);
R.T    = X(:,6);
R.de   = X(:,7);
R.theta= X(:,2) + X(:,3);
R.h_c  = REF(:,1);
R.V_c  = REF(:,3);
R.DBG  = struct('e_h',DBG(:,1),'e_th',DBG(:,2),'e_q',DBG(:,3),'e_V',DBG(:,4), ...
                'gam_d',DBG(:,5),'theta_d',DBG(:,6),'th_c',DBG(:,7),'q_cf',DBG(:,8), ...
                'uM',DBG(:,9),'uD',DBG(:,10),'ur',DBG(:,11),'urV',DBG(:,12), ...
                'W1norm',DBG(:,13),'W2norm',DBG(:,14),'sat_e',DBG(:,15),'IV',DBG(:,16), ...
                'de_unsat',DBG(:,17),'dt_cmd',DBG(:,18));
R.scn  = scn;
R.plant= plant;
R.p    = p;
R.pt   = pt;
R.pc   = pc;
R.ctrl_end = ctrl;      % 末拍控制器内部状态（滤波器 + 权值），供闭环平衡点分析使用
R.metrics = wig_metrics(R);

end

% =====================================================================
function v = getfield_def(s, name, def)
if isstruct(s) && isfield(s, name) && ~isempty(s.(name))
    v = s.(name);
else
    v = def;
end
end

% =====================================================================
function prof = get_profile(scn, name, tvec, def)
if isfield(scn,'ref') && isfield(scn.ref, name) && ~isempty(scn.ref.(name))
    tbl = reshape(scn.ref.(name), [], 2);
    if size(tbl,1) < 2
        prof = tbl(1,2) * ones(numel(tvec),1);
    else
        prof = interp1(tbl(:,1), tbl(:,2), tvec, 'previous', tbl(end,2));
    end
else
    prof = def * ones(numel(tvec),1);
end
prof = prof(:);
end

% =====================================================================
function [ug, wg] = make_gust(gs, tvec, V, seed)
Nt = numel(tvec);
ug = zeros(Nt,1);
wg = zeros(Nt,1);
if ~isstruct(gs) || ~isfield(gs,'enable') || ~gs.enable
    return;
end
dt = tvec(2) - tvec(1);
switch lower(gs.type)
    case '1-cos'
        idx = (tvec >= gs.t0) & (tvec <= gs.t0 + gs.tg);
        tt  = tvec(idx) - gs.t0;
        wg(idx) = 0.5 * gs.Wg * (1 - cos(2*pi*tt/gs.tg));
        ug(idx) = 0.30 * wg(idx);
    case 'dryden'
        % 竖向 Dryden 连续湍流模型（二阶成形滤波器）：
        %   H_w(s) = sig_w*sqrt(2*Lw/(pi*V)) * (1+sqrt(3)*tau*s)/(1+tau*s)^2,  tau = Lw/V
        tau = gs.Lu / max(V, 1);
        K   = gs.sig_u * sqrt(2*gs.Lu/(pi*max(V,1)));
        rng(seed + 31);
        n = randn(Nt,1);
        x1 = 0; x2 = 0;
        for i = 1:Nt
            x2 = x2 + dt * (n(i) - 2*tau*x2 - x1)/(tau^2);
            x1 = x1 + dt * x2;
            wg(i) = K * (x1 + sqrt(3)*tau*x2);
        end
        ug = 0.5 * wg;
    otherwise
        error('wig_simulate:badGust', '未知阵风类型：%s', gs.type);
end
end
