function [Acl, ev, names, info] = wig_closedloop_eig(trm, p, pc, pt, flag, ref, opts)
%WIG_CLOSEDLOOP_EIG  采样闭环系统（冻结自适应权值）的数值线性化与极点
%
%   [Acl, ev, names, info] = wig_closedloop_eig(trm, p, pc, pt, flag, ref, opts)
%
%   将"连续被控对象 + 200 Hz 离散控制器（零序保持）"视为一个采样周期映射
%       F : (x_k, z_k) -> (x_{k+1}, z_{k+1})
%   并在闭环平衡点处做数值线性化，得到 15 个闭环特征值。
%
%   状态：被控对象 x(7) + 控制器滤波器 z(8) = 15
%       [gam_c, th_c, q_cf, IV, xf(4)]
%   自适应权值 W1、W2 按【冻结参数分析】处理：取定常参考下闭环仿真收敛
%   得到的终值后保持常数（自适应律的时间尺度远慢于姿态/浮沉模态，属于标准
%   的冻结参数处理方法）。
%
%   与早期版本的区别（重要）：
%     1) 线性化点不再是"真实对象配平点 + 权值置零"，而是先用定常参考做闭环
%        仿真、再解出冻结参数系统的真实平衡点 x*；否则 eigh 结果会混入
%        "名义控制器 / 真实对象"配平失配造成的瞬态漂移。
%     2) 权值冻结在收敛值而非零，使 RBF 对力矩失配的补偿真正进入线性化。
%
%   输入：
%     trm   配平结构体（提供初始工作点与初值）
%     p     名义参数（控制器内部模型）
%     pc    控制器参数（缺省 = p）
%     pt    真实对象参数（缺省 = p）
%     flag  'nominal' | 'truth'
%     ref   参考指令 [h_c; hd_c; V_c; Vd_c]（缺省取平衡点）
%     opts  选项：
%            .Twarm   暖启动闭环仿真时长 [s]（缺省 60；定常参考下闭环约在
%                     50~60 s 才把权值收敛到位，暖启动不足会让平衡点求解
%                     跳到另一个定点分支）
%            .warm    直接给定暖启动点 struct('x',x_w,'ctrl',c_w)，跳过仿真
%            .solve   是否求解精确平衡点（缺省 true）
%            .W1 .W2  直接给定冻结权值（缺省取暖启动仿真终值）
%            .tol     平衡点残差容差（缺省 1e-9）
%            .verbose 打印平衡点求解信息（缺省 false）
%            .maxdev  允许平衡点相对暖启动点的最大偏移（缺省 0.05，
%                     用于检测"跳到其它定点分支"；超限给出警告）
%   输出：
%     Acl   15x15 闭环离散状态矩阵
%     ev    闭环极点（离散，|z|<1 为稳定）
%     names 状态名
%     info  诊断信息：.w_eq .x_eq .h_eq 平衡点 .res_eq 残差 .res_eq0 初值残差
%                     .iters 迭代次数 .W1 .W2 冻结权值 .warm 暖启动点

if nargin < 3 || isempty(pc),   pc = p;   end
if nargin < 4 || isempty(pt),   pt = p;   end
if nargin < 5 || isempty(flag), flag = 'truth'; end
if nargin < 7 || isempty(opts), opts = struct(); end

x0 = trm.x(:);

if nargin < 6 || isempty(ref)
    ref = [x0(5); 0; x0(1); 0];
end
ref = ref(:);

Twarm    = getdef(opts, 'Twarm',   60);
do_solve = getdef(opts, 'solve',   true);
tol      = getdef(opts, 'tol',     1e-9);
verbose  = getdef(opts, 'verbose', false);
maxdev   = getdef(opts, 'maxdev',  0.05);

nx = 7;
nz = 8;
n  = nx + nz;

names = {'V','gam','alpha','q','h','T','de', ...
         'gam_c','th_c','q_cf','IV','xf_V','xf_a','xf_q','xf_h'};

%% ---- 1. 暖启动：定常参考下的闭环仿真，取得收敛的权值与状态 ----
cbase = wig_ctrl_init(pc, x0);

if isfield(opts,'W1') && ~isempty(opts.W1), cbase.W1 = opts.W1(:); end
if isfield(opts,'W2') && ~isempty(opts.W2), cbase.W2 = opts.W2(:); end

have_warm = isfield(opts,'warm') && isstruct(opts.warm) && ...
            isfield(opts.warm,'x') && isfield(opts.warm,'ctrl');

if have_warm
    xT    = opts.warm.x(:);
    cbase = opts.warm.ctrl;
else
    scn = struct('p', p, 'pt', pt, 'pc', pc, 'Tend', Twarm, 'plant', flag, 'x0', x0, ...
                 'ref', struct('h', [0, ref(1)], 'V', [0, ref(3)]));
    Rw  = wig_simulate(scn);
    cw  = Rw.ctrl_end;
    cbase.W1 = cw.W1;   cbase.W2 = cw.W2;
    cbase.gam_c = cw.gam_c;  cbase.th_c = cw.th_c;
    cbase.q_cf  = cw.q_cf;   cbase.IV   = cw.IV;
    xT = Rw.x(end,:)';
end
if isempty(cbase.xf)
    cbase.xf = xT([1 3 4 5]);
end

wc = cbase;                     % 冻结权值与网络结构（滤波器状态由 w 提供）
w0 = [xT; pack_filters(cbase)];

%% ---- 2. 求解冻结参数系统的平衡点 ----
fun = @(w) one_step(w, ref, pc, pt, flag, wc) - w;

res_eq0 = norm(fun(w0), inf);
res_eq  = res_eq0;
iters   = 0;
w_eq    = w0;
jumped  = false;

if do_solve
    [ws, rs, iters] = solve_fixed_point(fun, w0, tol, 80, verbose);
    dev = max(abs(ws - w0) ./ max(1, abs(w0)));
    if dev > maxdev && res_eq0 <= rs
        % 求解结果远离暖启动点：判定为跳到了"另一个定点分支"。
        % 暖启动点本身就是收敛轨迹的终端，其残差已经足够小，回退使用它。
        jumped = true;
        w_eq = w0;  res_eq = res_eq0;  iters = 0;
        if verbose
            fprintf(['  [警告] 平衡点求解偏离暖启动点 %.3e（> %.3e），' ...
                     '判定为定点分支跳变，已回退到暖启动点。\n'], dev, maxdev);
        end
    else
        w_eq = ws;  res_eq = rs;  jumped = false;
    end
end

%% ---- 3. 数值雅可比（中心差分） ----
Acl = zeros(n, n);
for i = 1:n
    dw = 1e-7 * max(1, abs(w_eq(i)));
    wp = w_eq; wp(i) = wp(i) + dw;
    wm = w_eq; wm(i) = wm(i) - dw;
    Acl(:, i) = (one_step(wp, ref, pc, pt, flag, wc) - ...
                 one_step(wm, ref, pc, pt, flag, wc)) / (2*dw);
end

ev = eig(Acl);

% ---- 各极点的主导状态（按特征向量最大幅值分量判定） ----
[Vv, Dd] = eig(Acl);
dv = diag(Dd);
dom = cell(numel(ev),1);
for k = 1:numel(ev)
    [~, id] = min(abs(dv - ev(k)));
    v = Vv(:, id);
    [~, im] = max(abs(v));
    dom{k} = names{im};
end
info_dom = dom;

info = struct();
info.w_eq    = w_eq;
info.x_eq    = w_eq(1:nx);
info.h_eq    = w_eq(5);
info.res_eq  = res_eq;
info.res_eq0 = res_eq0;
info.iters   = iters;
info.jumped  = jumped;
info.maxdev  = maxdev;
info.W1      = cbase.W1;
info.W2      = cbase.W2;
info.ref     = ref;
info.flag    = flag;
info.Twarm   = Twarm;
info.solved  = do_solve;
info.maxabsz = max(abs(ev));
info.dom     = info_dom;
info.warm    = struct('x', xT, 'ctrl', cbase);

if verbose
    fprintf('  平衡点求解：初值残差 %.3e -> 终值残差 %.3e（迭代 %d 次）\n', ...
        res_eq0, res_eq, iters);
    fprintf('  平衡点高度 h_eq = %.5f m（指令 %.5f m，偏差 %+.2e m）\n', ...
        info.h_eq, ref(1), info.h_eq - ref(1));
    fprintf('  冻结权值范数：||W1||=%.4f  ||W2||=%.4f\n', ...
        norm(cbase.W1), norm(cbase.W2));
end

end

% =====================================================================
function [w, res, it] = solve_fixed_point(fun, w0, tol, maxit, verbose)
%SOLVE_FIXED_POINT  用 fsolve（若可用）或自研阻尼牛顿法求解 F(w) = w
w   = w0;
res = norm(fun(w), inf);

use_fsolve = (exist('fsolve','file') == 2) || (exist('fsolve','builtin') == 5);
if use_fsolve
    try
        opt = optimoptions('fsolve', 'Display', 'off', ...
            'FunctionTolerance', tol, 'StepTolerance', 1e-14, ...
            'OptimalityTolerance', tol, 'MaxIterations', maxit, ...
            'MaxFunctionEvaluations', 4000);
        [ws, ~, exitflag, out] = fsolve(fun, w0, opt);
        if exitflag > 0 || norm(fun(ws), inf) < res
            w = ws;  res = norm(fun(w), inf);
        end
        if isstruct(out) && isfield(out, 'iterations')
            it = out.iterations;        % 记录 fsolve 实际迭代次数
        else
            it = 0;
        end
        return;
    catch
        % 回退到自研牛顿法
    end
end

it = 0;
for k = 1:maxit
    F = fun(w);
    r = norm(F, inf);
    if r < tol, break; end

    % 数值雅可比
    n = numel(w);
    J = zeros(n, n);
    for i = 1:n
        dw = 1e-7 * max(1, abs(w(i)));
        wp = w; wp(i) = wp(i) + dw;
        wm = w; wm(i) = wm(i) - dw;
        J(:, i) = (fun(wp) - fun(wm)) / (2*dw);
    end
    J = J - eye(n);                       % F(w) - w 的雅可比

    if rcond(J) < 1e-14
        break;                            % 病态，停止
    end
    dw = -J \ F;

    lam = 1.0;
    for ls = 1:25
        wn = w + lam * dw;
        if norm(fun(wn), inf) < r, break; end
        lam = lam * 0.5;
    end
    w = w + lam * dw;
    it = k;
    if lam < 1e-6, break; end
end
res = norm(fun(w), inf);

if verbose && it >= maxit
    fprintf('  [警告] 牛顿法达到最大迭代次数，残差 %.3e\n', res);
end

end

% =====================================================================
function z = pack_filters(c)
%PACK_FILTERS  控制器"滤波器状态"打包（8 维；不含权值）
%   注意：与 wig_ctrl_pack（147 维，含权值）不同，此处只打包参与线性化的
%   8 个滤波器状态，避免同名函数布局歧义。
z = [c.gam_c; c.th_c; c.q_cf; c.IV; c.xf(:)];
end

% =====================================================================
function c = unpack_filters(z, cbase)
%UNPACK_FILTERS  由 8 维向量还原控制器滤波器状态（权值等取自 cbase）
c = cbase;                 % 保留 nn / W1 / W2 等非状态字段
c.gam_c = z(1);
c.th_c  = z(2);
c.q_cf  = z(3);
c.IV    = z(4);
c.xf    = z(5:8);
end

% =====================================================================
function wn = one_step(w, ref, pc, pt, flag, cbase)
%ONE_STEP  一个采样周期的闭环映射（自适应权值冻结在 cbase 上）
x = w(1:7);
c = unpack_filters(w(8:15), cbase);

[u, c2] = wig_ctrl_update(x, ref, c, pc);

% 零阶保持 + 定步长 RK4 积分一个采样周期
Ts   = pc.sim.Ts;
nsub = max(1, round(Ts / pc.sim.dt));
h    = Ts / nsub;
xx   = x;
for k = 1:nsub
    k1 = wig_dynamics(xx,        u, pt, flag);
    k2 = wig_dynamics(xx+h/2*k1, u, pt, flag);
    k3 = wig_dynamics(xx+h/2*k2, u, pt, flag);
    k4 = wig_dynamics(xx+h*k3,   u, pt, flag);
    xx = xx + (h/6)*(k1 + 2*k2 + 2*k3 + k4);
end
wn = [xx; pack_filters(c2)];
end

% =====================================================================
function v = getdef(s, name, def)
if isstruct(s) && isfield(s, name) && ~isempty(s.(name))
    v = s.(name);
else
    v = def;
end
end
