function run_00_lag_body()
%RUN_00_LAG_BODY

p  = wig_params();
pt = wig_truth_params(p);

% ---- 历史调试增益（早期优化器输出，非 wig_params.m 出厂值） ----
% 与 wig_params.m 的最终出厂值逐项对照：
%   k_h    2.151 -> 2.00      k_hd   0.944 -> 0.80
%   k_th   3.513 -> 3.20      k_q    5.277 -> 6.00
%   tau_g  0.0098 -> 0.010    tau_th 0.0846 -> 0.100    tau_q 0.0469 -> 0.010
%   k_V    1.527 -> 1.53      k_IV   0.422 -> 0.42
%   Phi_r  0.261 -> 0.80      Phi_V  0.523 -> 1.00
% 保留该组即可与历史 log_lag.txt 直接对比。
pc0 = p;
pc0.ctrl.k_h=2.151; pc0.ctrl.k_hd=0.944; pc0.ctrl.k_th=3.513; pc0.ctrl.k_q=5.277;
pc0.ctrl.tau_g=0.0098; pc0.ctrl.tau_th=0.0846; pc0.ctrl.tau_q=0.0469;
pc0.ctrl.k_V=1.527; pc0.ctrl.k_IV=0.422;
pc0.ctrl.Phi_r=0.261; pc0.ctrl.Phi_V=0.523;

fprintf('=========== 时滞敏感性分析 ===========\n\n');
fprintf('基准 max|z|: ');
for hh = [0.05 0.20 0.50]
    trm = wig_trim(p.V0, hh, pt, 'truth');
    [~, ev] = wig_closedloop_eig(trm, p, pc0, pt, 'truth', [hh;0;p.V0;0]);
    fprintf('h=%.2f:%.5f  ', hh, max(abs(ev)));
end
fprintf('\n\n');

% 注意：tau_e 是【被控对象】的舵机一阶时间常数，只在 wig_dynamics 中使用；
% 控制器 wig_ctrl_update 完全不引用 tau_e（其指令滤波时间常数为 ctrl.tau_th /
% ctrl.tau_q）。因此下表只改变对象舵机，控制器一侧始终保持 pc0 不变，
% 并非旧标题所写的"对象与控制器一致"。
fprintf('---- 舵机时间常数 tau_e（仅改变被控对象舵机；控制器不使用 tau_e） ----\n');
for te = [0.05 0.03 0.02 0.01]
    pn = pt; pn.tau_e = te;      % pn 为真实对象参数，仅舵机时间常数变化
    s = '';
    for hh = [0.05 0.20 0.50]
        trm = wig_trim(p.V0, hh, pn, 'truth');
        [~, ev] = wig_closedloop_eig(trm, p, pc0, pn, 'truth', [hh;0;p.V0;0]);
        s = [s, sprintf(' h=%.2f:%.5f', hh, max(abs(ev)))]; %#ok<AGROW>
    end
    fprintf('tau_e=%.3f %s\n', te, s);
end

fprintf('\n---- DSC 滤波时间常数 tau_th / tau_q ----\n');
for tth = [0.085 0.04 0.02 0.01]
    for tq = [0.047 0.02 0.01]
        pci = pc0; pci.ctrl.tau_th = tth; pci.ctrl.tau_q = tq;
        s = '';
        for hh = [0.05 0.20 0.50]
            trm = wig_trim(p.V0, hh, pt, 'truth');
            [~, ev] = wig_closedloop_eig(trm, p, pci, pt, 'truth', [hh;0;p.V0;0]);
            s = [s, sprintf(' h=%.2f:%.5f', hh, max(abs(ev)))]; %#ok<AGROW>
        end
        fprintf('tau_th=%.3f tau_q=%.3f %s\n', tth, tq, s);
    end
end

fprintf('\n---- 量测滤波 tau_f ----\n');
for tf = [0.02 0.01 0.005]
    pci = pc0; pci.sens.tau_f = tf;
    s = '';
    for hh = [0.05 0.20 0.50]
        trm = wig_trim(p.V0, hh, pt, 'truth');
        [~, ev] = wig_closedloop_eig(trm, p, pci, pt, 'truth', [hh;0;p.V0;0]);
        s = [s, sprintf(' h=%.2f:%.5f', hh, max(abs(ev)))]; %#ok<AGROW>
    end
    fprintf('tau_f=%.3f %s\n', tf, s);
end

fprintf('\n---- 采样周期 Ts ----\n');
for ts = [0.005 0.0025 0.00125]
    pci = pc0; pci.sim.Ts = ts;
    s = '';
    for hh = [0.05 0.20 0.50]
        trm = wig_trim(p.V0, hh, pt, 'truth');
        [~, ev] = wig_closedloop_eig(trm, p, pci, pt, 'truth', [hh;0;p.V0;0]);
        s = [s, sprintf(' h=%.2f:%.5f', hh, max(abs(ev)))]; %#ok<AGROW>
    end
    fprintf('Ts=%.5f %s\n', ts, s);
end

% ---- 线性化 vs 非线性验证 ----
fprintf('\n---- 线性化预测 vs 非线性仿真（h=0.20 m，初始高度扰动 +2 mm） ----\n');
trm = wig_trim(p.V0, p.h0, pt, 'truth');
[~, ev] = wig_closedloop_eig(trm, p, pc0, pt, 'truth', [p.h0;0;p.V0;0]);
[mx, id] = max(abs(ev));
lam = log(ev(id))/pc0.sim.Ts;
fprintf('预测主导极点 s = %+.4f %+.4fi   =>  增长率 %.4f 1/s, 频率 %.3f rad/s\n', ...
    real(lam), imag(lam), real(lam), abs(imag(lam)));

scn = struct(); scn.p = p; scn.pc = pc0; scn.pt = pt; scn.Tend = 10.0; scn.plant = 'truth';
scn.ref.h = [0 p.h0]; scn.ref.V = [0 p.V0];
scn.x0 = trm.x; scn.x0(5) = trm.x(5) + 0.002;
R = wig_simulate(scn);
fprintf('非线性仿真高度偏差（相对指令）:\n');
fprintf('   t:     ');
for tt = 0:1:10, fprintf('%8.1f', tt); end
fprintf('\n   e_h:   ');
for tt = 0:1:10
    k = round(tt/p.sim.dt)+1; k = min(k, numel(R.t));
    fprintf('%8.5f', R.h(k)-p.h0);
end
fprintf('\n');

fprintf('\n=========== 分析结束 ===========\n');

end
