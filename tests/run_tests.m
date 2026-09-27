function run_tests(varargin)
%RUN_TESTS  地效飞行器 RBF 自适应飞控 —— 单元测试与不变量校验
%
%   run_tests                 % 运行全部测试
%   run_tests('fast', true)   % 跳过耗时的闭环/Simulink 相关测试
%
%   本套件校验的是【理论所依赖的不变量】，而不是"跑一遍不报错"：
%     1. 地效因子 kappa(h) 的值域、单调性与导数正确性
%     2. 几何/质量的内部一致性（S = b*c、AR = b^2/S、W = m*g）
%     3. 配平残差（名义模型与真实对象、多个高度）
%     4. dM/dh 分量分解的闭合性（分量之和 == 数值总量）
%     5. RBF 网络的节点数、归一化映射与基函数性质
%     6. 投影算子的权值有界性（长序列随机更新后仍 <= Wmax）
%     7. 控制器状态 pack/unpack 的往返一致性（147 维）
%     8. 饱和函数语义
%     9. 数值线性化与有限差分的一致性
%    10. 采样闭环极点分析：平衡点残差与 max|z| < 1
%    11. 闭环非线性仿真：短时仿真不触地、状态不发散
%    12. 经典浮沉阻尼公式的数值自洽性
%
%   全部通过时打印 TESTS PASS 并以 0 退出；任一失败则打印明细并以非零退出。

here = fileparts(mfilename('fullpath'));
src  = fullfile(here, '..', 'src');
addpath(src);

fast = false;
for k = 1:2:numel(varargin)
    if strcmpi(varargin{k}, 'fast'), fast = logical(varargin{k+1}); end
end

T = testbook();
fprintf('================ WIG 单元测试 ================\n');
fprintf('MATLAB %s\n\n', version);

p  = wig_params();
pt = wig_truth_params(p);

%% ---------- 1. 地效因子 ----------
T.section('1. 地效因子 kappa(h)');
ks = zeros(1, 20);
hs = linspace(0.005, 2.0, 20);
for i = 1:numel(hs), ks(i) = wig_ge(hs(i), p.b, p); end
T.ok('kappa 值域 (0,1)', all(ks > 0) && all(ks < 1));
T.ok('kappa 随高度单调不减', all(diff(ks) > 0));
T.near('kappa(0) = 0', wig_ge(0, p.b, p), 0, 0);
T.ok('kappa -> 1 (远离地面)', wig_ge(50, p.b, p) > 0.995);
T.ok('kappa 对 span 归一化', abs(wig_ge(0.24, 2.40, p) - wig_ge(0.12, 1.20, p)) < 1e-12);
T.near('解析导数 == 中心差分', wig_ge_deriv_num(0.20, p), 0, 1e-6);

%% ---------- 2. 几何/质量一致性 ----------
T.section('2. 几何与质量一致性');
T.near('名义 S = b*c', p.S, p.b * p.c, 0);
T.near('名义 AR = b^2/S', p.AR, p.b^2 / p.S, 0);
T.near('平尾 ARt = bt^2/St', p.ARt, p.bt^2 / p.St, 0);
T.near('真实对象 S 与名义一致', pt.S, p.S, 0);
T.ok('推力范围合法', p.Tmin < p.Tmax && p.Tmin >= 0);
T.ok('状态维数 7、控制维数 2', numel(p.sim.dt) == 1);

%% ---------- 3. 配平残差 ----------
T.section('3. 配平残差');
for h = [0.05 0.20 0.50]
    trn = wig_trim(p.V0, h, p, 'nominal');
    T.ok(sprintf('名义配平残差 h=%.2f', h), trn.res < 1e-9);
    trt = wig_trim(p.V0, h, pt, 'truth');
    T.ok(sprintf('真实配平残差 h=%.2f', h), trt.res < 1e-9);
end
trm = wig_trim(p.V0, 0.20, pt, 'truth');
dxT = wig_dynamics(trm.x, [trm.de; trm.dt], pt, 'truth');
T.ok('真实配平点导数为零 (<1e-9)', norm(dxT(1:7)) < 1e-9);

%% ---------- 4. dM/dh 分量分解闭合 ----------
T.section('4. dM/dh 分量分解');
for h = [0.05 0.20 0.50]
    tk = wig_trim(p.V0, h, pt, 'truth');
    D = wig_mdh_decomp(tk.x, pt);
    T.ok(sprintf('分解闭合 h=%.2f (残差 %.1e)', h, abs(D.resid)), abs(D.resid) < 1e-9);
    T.near(sprintf('分量之和 == 总量 h=%.2f', h), D.sum_parts, D.total, 1e-9);
    T.ok(sprintf('平尾为主导不稳定项 h=%.2f', h), strcmp(D.dom_name, 'tail'));
    T.ok(sprintf('机体/推力线项为零 h=%.2f', h), ...
        abs(D.fuse) < 1e-12 && abs(D.thrust) < 1e-12);
    T.ok(sprintf('dM/dh > 0（高度静不稳定）h=%.2f', h), D.total > 0);
    T.ok(sprintf('机翼项为负（稳定）h=%.2f', h), D.wing < 0);
end
tk = wig_trim(p.V0, 0.20, pt, 'truth');
D0 = wig_mdh_decomp(tk.x, pt);
% 与 wig_aero 直接中心差分对照（独立实现）
dhh = 1e-5;
Fp = wig_aero([tk.x(1:4); tk.x(5)+dhh; tk.x(6:7)], pt, 'truth');
Fm = wig_aero([tk.x(1:4); tk.x(5)-dhh; tk.x(6:7)], pt, 'truth');
T.near('分解总量 == 独立中心差分', D0.total, (Fp(3)-Fm(3))/(2*dhh), 1e-6);

%% ---------- 5. RBF 网络 ----------
T.section('5. RBF 网络');
nn = wig_rbf_init(p);
T.eq('力矩通道节点数 N1 = 75', nn.N1, 75);
T.eq('阻力通道节点数 N2 = 64', nn.N2, 64);
T.ok('中心矩阵维数 3xN1', isequal(size(nn.C1), [3, nn.N1]));
T.ok('中心位于 [-1,1]^3', all(nn.C1(:) >= -1-1e-12) && all(nn.C1(:) <= 1+1e-12));
T.eq('宽度正定', sum(nn.sig1 > 0) + sum(nn.sig2 > 0), 6);
z = wig_norm([p.h0; 0; p.V0], [0 1; -1 1; 10 30]);
T.ok('wig_norm 映射到 [-1,1]', all(abs(z) <= 1 + 1e-12));
zc = nn.C1(:, 1);
ph = wig_rbf_phi(zc, nn.C1, nn.sig1);
T.ok('中心处基函数 = 1', abs(ph(1) - 1) < 1e-12);
T.ok('基函数非负且 <= 1', all(ph >= 0) && all(ph <= 1 + 1e-12));
T.ok('相邻基函数重叠度 in (0.5,0.7)', ...
    abs(exp(-0.5) - 0.6065) < 1e-3);
far = wig_rbf_phi(10*ones(3,1), nn.C1, nn.sig1);
T.ok('远离中心时基函数 -> 0', max(far) < 1e-6);

%% ---------- 6. 投影算子 ----------
T.section('6. 投影算子');
Wmax = p.ctrl.nn.Wmax;
Ts   = p.sim.Ts;
rng(7);
W = zeros(75, 1);
for k = 1:20000
    tau = 50 * randn(75, 1);
    W = wig_proj(W, tau, Wmax, Ts);
end
T.ok(sprintf('长序列随机更新后 ||W|| <= Wmax (%.6f)', norm(W)), norm(W) <= Wmax * 1.0000001);
W2 = Wmax * [1; zeros(74,1)];
W3 = wig_proj(W2, [1; zeros(74,1)], Wmax, Ts);   % 沿径向向外
T.ok('边界外向更新被投影回球内', norm(W3) <= Wmax * 1.0000001);
W4 = wig_proj(W2, [-1; zeros(74,1)], Wmax, Ts);  % 沿径向向内
T.ok('边界内向更新被允许', norm(W4) < Wmax);

%% ---------- 7. pack / unpack ----------
T.section('7. 控制器状态打包');
x0  = trm.x;
c0  = wig_ctrl_init(p, x0);
c0.W1 = 0.01 * (1:nn.N1)';
c0.W2 = 0.02 * (1:nn.N2)';
z0  = wig_ctrl_pack(c0);
T.eq('打包长度 = 8 + N1 + N2 = 147', numel(z0), 147);
c1  = wig_ctrl_unpack(z0, nn);
T.near('W1 往返一致', norm(c1.W1 - c0.W1), 0, 0);
T.near('W2 往返一致', norm(c1.W2 - c0.W2), 0, 0);
T.near('xf 往返一致', norm(c1.xf(:) - c0.xf(:)), 0, 0);
T.near('gam_c 往返一致', c1.gam_c, c0.gam_c, 0);
T.ok('长度不符时报错', throws(@() wig_ctrl_unpack(z0(1:100), nn)));
c_bad = c0;  c_bad.xf = [];
T.ok('xf 为空时报错', throws(@() wig_ctrl_pack(c_bad)));

%% ---------- 8. 饱和函数 ----------
T.section('8. 饱和函数');
T.near('对称限幅上界', wig_sat(5, 2), 2, 0);
T.near('对称限幅下界', wig_sat(-5, 2), -2, 0);
T.near('非对称限幅', wig_sat(5, 0, 1), 1, 0);
T.near('限幅内不变', wig_sat(0.3, 1), 0.3, 0);

%% ---------- 9. 数值线性化 ----------
T.section('9. 数值线性化');
lin = wig_linearize(trm, pt, 'truth');
A = lin.A;
d  = 1e-6;
x1 = trm.x;  x1(3) = x1(3) + d;
x2 = trm.x;  x2(3) = x2(3) - d;
f1 = wig_dynamics(x1, [trm.de; trm.dt], pt, 'truth');
f2 = wig_dynamics(x2, [trm.de; trm.dt], pt, 'truth');
T.near('A(4,3) == d(qdot)/d(alpha)', A(4,3), (f1(4)-f2(4))/(2*d), 1e-4);
T.near('A(5,2) == V (dh/dt = V sin gam)', A(5,2), trm.x(1), 1e-6);
T.eq('特征值个数 = 7', numel(lin.eig), 7);

%% ---------- 10. 经典浮沉阻尼 ----------
T.section('10. 经典浮沉阻尼公式');
F = wig_aero(trm.x, pt, 'truth');
L = F(1);  Dg = F(2);
wn_p = sqrt(2)*pt.g/p.V0;
T.near('wn_p = sqrt(2)g/V', wn_p, 0.7705, 1e-3);
T.near('zeta_p = 1/(sqrt(2)(L/D))', Dg/(sqrt(2)*L), 0.0527, 1e-3);
T.ok('zeta_p 与 D/(m*V^2*wn_p) 不同（量纲检查）', ...
    abs(Dg/(sqrt(2)*L) - Dg/(pt.m*p.V0^2*wn_p)) > 0.04);

%% ---------- 11/12. 慢测试 ----------
if ~fast
    T.section('11. 采样闭环极点分析');
    ref = [p.h0; 0; p.V0; 0];
    [~, ev, ~, info] = wig_closedloop_eig(trm, p, p, pt, 'truth', ref, ...
        struct('Twarm', 60, 'verbose', false));
    T.ok(sprintf('平衡点残差 < 1e-9 (%.1e)', info.res_eq), info.res_eq < 1e-9);
    T.eq('闭环阶数 = 15', numel(ev), 15);
    T.ok(sprintf('max|z| < 1 (%.5f)', info.maxabsz), info.maxabsz < 1);
    T.ok('平衡点高度接近指令 (<2cm)', abs(info.h_eq - ref(1)) < 0.02);
    T.ok('冻结权值有界', norm(info.W1) <= p.ctrl.nn.Wmax && norm(info.W2) <= p.ctrl.nn.Wmax);

    T.section('12. 闭环非线性仿真');
    scn = struct('p', p, 'pt', pt, 'pc', p, 'Tend', 20, 'plant', 'truth', ...
                 'ref', struct('h', [0 0.20; 5 0.30], 'V', [0 18]));
    R = wig_simulate(scn);
    T.ok('高度全程高于地面', R.metrics.h_min > 0);
    T.ok('状态有限', all(isfinite(R.x(:))));
    T.ok('高度误差 RMS < 0.05 m', R.metrics.h_rms < 0.05);
    T.ok('权值范数有界', max(R.DBG.W1norm) <= p.ctrl.nn.Wmax + 1e-9);
    T.ok('升降舵未持续饱和', max(abs(R.de)) <= p.de_max + 1e-9);
end

%% ---------- 汇总 ----------
code = T.summary();
if code ~= 0
    error('run_tests:failed', '%d 项测试未通过。', T.nfail);
end
end

% =====================================================================
function d = wig_ge_deriv_num(h, p)
%WIG_GE_DERIV_NUM  地效因子解析导数与中心差分的一致性检查
[~, dk] = wig_ge(h, p.b, p);
dh = 1e-7;
k1 = wig_ge(h+dh, p.b, p);
k2 = wig_ge(h-dh, p.b, p);
d  = dk - (k1-k2)/(2*dh);
end

% =====================================================================
function tf = throws(fn)
%THROWS  断言调用会抛出异常
tf = false;
try
    fn();
catch
    tf = true;
end
end

% =====================================================================
function T = testbook()
%TESTBOOK  极简测试簿
T.npass = 0;  T.nfail = 0;  T.fails = {};
T.section = @(s) fprintf('\n---- %s ----\n', s);
    function ok(name, cond)
        if cond
            T.npass = T.npass + 1;
            fprintf('  [PASS] %s\n', name);
        else
            T.nfail = T.nfail + 1;
            T.fails{end+1} = name; %#ok<AGROW>
            fprintf('  [FAIL] %s\n', name);
        end
    end
    function eq(name, a, b)
        ok(sprintf('%s (%g == %g)', name, a, b), abs(double(a) - double(b)) < 1e-12);
    end
    function near(name, a, b, tol)
        ok(sprintf('%s (%.10g vs %.10g, tol %.1e)', name, a, b, tol), abs(a - b) <= tol);
    end
    function code = summary()
        fprintf('\n================ 测试汇总 ================\n');
        fprintf('通过 %d 项，失败 %d 项\n', T.npass, T.nfail);
        if T.nfail > 0
            fprintf('失败清单：\n');
            for i = 1:numel(T.fails)
                fprintf('  - %s\n', T.fails{i});
            end
            code = 1;
            fprintf('TESTS FAIL\n');
        else
            code = 0;
            fprintf('TESTS PASS\n');
        end
    end
T.ok = @ok;  T.eq = @eq;  T.near = @near;  T.summary = @summary;
end
