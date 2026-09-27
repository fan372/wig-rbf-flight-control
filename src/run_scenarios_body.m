function run_scenarios_body()
%RUN_SCENARIOS_BODY  场景仿真主体

wig_plot_style();
p  = wig_params();
pt = wig_truth_params(p);

res = struct();

%% ============================================================
%  场景 1：地效区高度机动 + 速度机动（自适应 / 无自适应 / 无自适应无鲁棒）
%% ============================================================
fprintf('================ 场景仿真 ================\n\n');
fprintf('---- 场景 1：地效区高度机动 + 速度机动 ----\n');
fprintf('高度指令: 0.20 -> 0.35 -> 0.10 -> 0.25 m；速度指令: 18 -> 20 m/s\n\n');

scn = struct(); scn.p = p; scn.pt = pt; scn.Tend = 40.0; scn.plant = 'truth';
scn.ref.h = [0 0.20; 3 0.35; 12 0.10; 21 0.25];
scn.ref.V = [0 18; 6 20];

[Ra, ma] = runcase(scn, p, 'RBF自适应 + 鲁棒项          ');
pcn = p; pcn.ctrl.enable_nn = false;
[Rn, mn] = runcase(scn, pcn, '仅名义动态逆 + 鲁棒项       ');
pcb = p; pcb.ctrl.enable_nn = false; pcb.ctrl.enable_rob = false;
[Rb, mb] = runcase(scn, pcb, '纯名义动态逆（无自适应无鲁棒）');

fprintf('\n%-28s %9s %9s %9s %9s %9s %8s %8s\n', ...
    '工况', 'h_rms', 'h_err_max', 'h_min', 'V_rms', 'V_err_max', 'de_max', 'ok');
prt('RBF自适应 + 鲁棒项', ma);
prt('仅名义动态逆 + 鲁棒项', mn);
prt('纯名义动态逆', mb);

res.Ra = Ra; res.Rn = Rn; res.Rb = Rb;
res.ma = ma; res.mn = mn; res.mb = mb;

% ---- 图 4：高度与速度跟踪 ----
f4 = figure('Position',[100 100 900 660]);
subplot(3,1,1);
plot(Ra.t, Ra.h_c, 'k--', 'LineWidth',1.0); hold on;
plot(Ra.t, Ra.h, 'b-', Rn.t, Rn.h, 'r-.', Rb.t, Rb.h, 'Color',[0.5 0.5 0.5]);
ylabel(wig_lbl('离地高度 h [m]','Altitude h [m]')); ylim([-0.02 0.42]);
legend({wig_lbl('高度指令','Altitude command'), ...
        wig_lbl('RBF自适应+鲁棒','RBF adaptive + robust'), ...
        wig_lbl('仅动态逆+鲁棒','Dynamic inversion + robust'), ...
        wig_lbl('纯动态逆','Dynamic inversion only')}, 'Location','northeast');
title(wig_lbl('(a) 地效区高度跟踪（真实对象，含地效失配/RAM效应/升力非线性）', ...
              '(a) Altitude tracking in the ground-effect band (true plant: GE mismatch / RAM effect / lift nonlinearity)'));

subplot(3,1,2);
plot(Ra.t, Ra.V_c, 'k--', 'LineWidth',1.0); hold on;
plot(Ra.t, Ra.V, 'b-', Rn.t, Rn.V, 'r-.', Rb.t, Rb.V, 'Color',[0.5 0.5 0.5]);
ylabel(wig_lbl('空速 V [m/s]','Airspeed V [m/s]')); ylim([16 21.5]);
legend({wig_lbl('速度指令','Airspeed command'), ...
        wig_lbl('RBF自适应+鲁棒','RBF adaptive + robust'), ...
        wig_lbl('仅动态逆+鲁棒','Dynamic inversion + robust'), ...
        wig_lbl('纯动态逆','Dynamic inversion only')}, 'Location','southeast');
title(wig_lbl('(b) 空速跟踪','(b) Airspeed tracking'));

subplot(3,1,3);
plot(Ra.t, Ra.alpha*180/pi, 'b-'); hold on;
plot(Rn.t, Rn.alpha*180/pi, 'r-.', Rb.t, Rb.alpha*180/pi, 'Color',[0.5 0.5 0.5]);
ylabel(wig_lbl('迎角 \alpha [deg]','Angle of attack \alpha [deg]'));
xlabel(wig_lbl('时间 t [s]','Time t [s]'));
legend({wig_lbl('RBF自适应+鲁棒','RBF adaptive + robust'), ...
        wig_lbl('仅动态逆+鲁棒','Dynamic inversion + robust'), ...
        wig_lbl('纯动态逆','Dynamic inversion only')}, 'Location','northwest');
title(wig_lbl('(c) 迎角响应','(c) Angle-of-attack response'));
wig_savefig(f4, 'fig4_tracking');

% ---- 图 5：状态与控制量 ----
f5 = figure('Position',[100 100 900 700]);
subplot(4,1,1);
plot(Ra.t, Ra.theta*180/pi, 'b-', Ra.t, Ra.gam*180/pi, 'g-');
ylabel(wig_lbl('角度 [deg]','Angle [deg]'));
legend({wig_lbl('俯仰角 \theta','Pitch angle \theta'), ...
        wig_lbl('航迹倾角 \gamma','Flight-path angle \gamma')}, 'Location','northeast');
title(wig_lbl('(a) 俯仰角与航迹倾角（自适应）', ...
              '(a) Pitch angle and flight-path angle (adaptive)'));

subplot(4,1,2);
plot(Ra.t, Ra.q, 'b-');
ylabel(wig_lbl('俯仰角速度 q [rad/s]','Pitch rate q [rad/s]'));
title(wig_lbl('(b) 俯仰角速度','(b) Pitch rate'));

subplot(4,1,3);
plot(Ra.t, Ra.de*180/pi, 'b-'); hold on;
yline(p.de_max*180/pi,'r--'); yline(-p.de_max*180/pi,'r--');
ylabel(wig_lbl('升降舵 \delta_e [deg]','Elevator deflection \delta_e [deg]')); ylim([-28 28]);
legend({'\delta_e', wig_lbl('限幅 \pm25°','Limit \pm25°')}, 'Location','northeast');
title(wig_lbl('(c) 升降舵偏角','(c) Elevator deflection'));

subplot(4,1,4);
plot(Ra.t, Ra.T, 'b-');
ylabel(wig_lbl('推力 T [N]','Thrust T [N]'));
xlabel(wig_lbl('时间 t [s]','Time t [s]'));
title(wig_lbl('(d) 发动机推力','(d) Engine thrust'));
wig_savefig(f5, 'fig5_states');

% ---- 图 6：自适应量 ----
f6 = figure('Position',[100 100 900 660]);
subplot(4,1,1);
plot(Ra.t, Ra.DBG.uM, 'b-', Ra.t, Ra.DBG.uD, 'r-');
ylabel(wig_lbl('网络输出','Network output'));
legend({'u_M [rad/s^2]','u_D [m/s^2]'}, 'Location','northeast');
title(wig_lbl('(a) RBF 神经网络在线估计输出', ...
              '(a) Online RBF neural-network estimate'));

subplot(4,1,2);
plot(Ra.t, Ra.DBG.ur, 'b-', Ra.t, Ra.DBG.urV, 'r-');
ylabel(wig_lbl('鲁棒项','Robust term'));
legend({'u_r [rad/s^2]','u_{rV} [m/s^2]'}, 'Location','northeast');
title(wig_lbl('(b) 鲁棒补偿项','(b) Robust compensation term'));

subplot(4,1,3);
plot(Ra.t, Ra.DBG.W1norm, 'b-', Ra.t, Ra.DBG.W2norm, 'r-');
ylabel(wig_lbl('权值范数','Weight norm'));
legend({wig_lbl('||W_1||（力矩通道）','||W_1|| (moment channel)'), ...
        wig_lbl('||W_2||（阻力通道）','||W_2|| (drag channel)')}, 'Location','northeast');
title(wig_lbl('(c) 权值范数（投影算子保证有界）', ...
              '(c) Weight norms (bounded by the projection operator)'));

subplot(4,1,4);
plot(Ra.t, Ra.DBG.e_q, 'b-', Ra.t, Ra.DBG.e_V, 'r-');
ylabel(wig_lbl('跟踪误差','Tracking error'));
xlabel(wig_lbl('时间 t [s]','Time t [s]'));
legend({'e_q [rad/s]','e_V [m/s]'}, 'Location','northeast');
title(wig_lbl('(d) 内环跟踪误差','(d) Inner-loop tracking error'));
wig_savefig(f6, 'fig6_adaptive');

%% ============================================================
%  场景 2：参数摄动鲁棒性
%% ============================================================
fprintf('\n---- 场景 2：对象参数摄动 ----\n');
P = {};
P{end+1} = {'标称对象',            wig_truth_params(p)};
P{end+1} = {'质量 m ×1.25、Iyy ×1.26', wig_truth_params(p,'m',15.0,'Iyy',1.45)};
P{end+1} = {'质量 m ×0.85、Iyy ×0.826', wig_truth_params(p,'m',10.2,'Iyy',0.95)};
% 下述两条地效摄动的标签按【代码实际改动量】书写：A_nom = 0.0641，
% 0.020 = 0.312*A_nom（A 越小则 kappa 越小、地效越强），0.090 = 1.404*A_nom。
P{end+1} = {'地效形状参数 A ×0.312（地效增强）', wig_truth_params(p,'ge_A',0.020,'ge_n',1.15)};
P{end+1} = {'地效形状参数 A ×1.404（地效减弱）', wig_truth_params(p,'ge_A',0.090,'ge_n',1.75)};
% 标签一律按【代码实际改动量】书写：
%   CD0: 0.0250 -> 0.045（×1.80，即 +80%）；CD0t: 0.0100 -> 0.018（×1.80）
%   eps_a: 0.350 -> 0.68（×1.94，即 +94%）
%   a0: 5.90 -> 5.2（×0.881）；eta_t: 0.95 -> 0.80（×0.842）
%   ge_A: 0.0641 -> 0.020（×0.312，A 越小 kappa 越小、地效越强）/ 0.090（×1.404，地效减弱）
P{end+1} = {'废阻力 CD0/CD0t ×1.80（+80%）', wig_truth_params(p,'CD0',0.045,'CD0t',0.018)};
P{end+1} = {'下洗梯度 eps_a ×1.94（+94%）',  wig_truth_params(p,'eps_a',0.68)};
P{end+1} = {'升力线斜率 a0 ×0.881、尾翼效率 eta_t ×0.842', ...
            wig_truth_params(p,'a0',5.2,'eta_t',0.80)};

% P 的英文标签：与上面 8 个工况【顺序严格一一对应】，只用于英文图 fig7 的图例；
% 日志与控制台仍然使用上面的中文标签（P{i}{1}），保持 log_scenarios.txt 不变。
Pen = { ...
    'Nominal plant', ...
    'Mass m \times1.25, I_{yy} \times1.26', ...
    'Mass m \times0.85, I_{yy} \times0.826', ...
    'GE shape parameter A \times0.312 (stronger GE)', ...
    'GE shape parameter A \times1.404 (weaker GE)', ...
    'Parasite drag C_{D0}/C_{D0t} \times1.80 (+80%)', ...
    'Downwash gradient \epsilon_\alpha \times1.94 (+94%)', ...
    'Lift slope a_0 \times0.881, tail efficiency \eta_t \times0.842'};
if numel(Pen) ~= numel(P)
    error('run_scenarios_body:pertLabelCount', ...
        '英文摄动标签 %d 条与工况 %d 个不一致，请同步维护 Pen。', numel(Pen), numel(P));
end

f7 = figure('Position',[100 100 900 560]); hold on;
clr = lines(numel(P));
lbl = cell(numel(P),1);
for i = 1:numel(P)
    scn2 = scn; scn2.pt = P{i}{2};
    R = wig_simulate(scn2); m = R.metrics;
    lbl{i} = wig_lbl(P{i}{1}, Pen{i});
    fprintf('%-26s h_rms=%.4f h_err_max=%.4f h_min=%.4f V_rms=%.4f de_max=%5.1f° ok=%d\n', ...
        P{i}{1}, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.de_max*180/pi, m.ok);
    plot(R.t, R.h, '-', 'Color', clr(i,:));
    res.pert{i} = R;
end
plot(Ra.t, Ra.h_c, 'k--', 'LineWidth', 1.2);
xlabel(wig_lbl('时间 t [s]','Time t [s]'));
ylabel(wig_lbl('离地高度 h [m]','Altitude h [m]')); xlim([0 40]);
legend([lbl(:); {wig_lbl('高度指令','Altitude command')}], 'Location','northeast');
title(wig_lbl('参数摄动下的高度跟踪（RBF 自适应）', ...
              'Altitude tracking under parameter perturbation (RBF adaptive)'));
wig_savefig(f7, 'fig7_perturbation');

%% ============================================================
%  场景 3：大气扰动
%% ============================================================
fprintf('\n---- 场景 3：大气扰动（阵风/湍流） ----\n');
G = {};
g1 = p.gust; g1.enable = true; g1.type = '1-cos'; g1.Wg = 1.5; g1.t0 = 5.0; g1.tg = 2.0;
G{end+1} = {'离散 1-cos 阵风 1.5 m/s（中度）', g1};
g3 = p.gust; g3.enable = true; g3.type = '1-cos'; g3.Wg = 3.0; g3.t0 = 5.0; g3.tg = 2.0;
G{end+1} = {'离散 1-cos 阵风 3.0 m/s（严酷）', g3};
g2 = p.gust; g2.enable = true; g2.type = 'dryden'; g2.sig_u = 1.5; g2.seed = 20260912;
G{end+1} = {'Dryden 连续湍流 \sigma=1.5 m/s', g2};

% G 的英文标签：与上面 3 个工况【顺序严格一一对应】，只用于英文图 fig8 的分图标题；
% 日志仍使用中文标签（G{i}{1}）。
Gen = {'Discrete 1-cos gust, 1.5 m/s (moderate)', ...
       'Discrete 1-cos gust, 3.0 m/s (severe)', ...
       'Dryden continuous turbulence, \sigma = 1.5 m/s'};
if numel(Gen) ~= numel(G)
    error('run_scenarios_body:gustLabelCount', ...
        '英文阵风标签 %d 条与工况 %d 个不一致，请同步维护 Gen。', numel(Gen), numel(G));
end

f8 = figure('Position',[100 100 900 620]);
for i = 1:numel(G)
    scn3 = scn; scn3.gust = G{i}{2};
    R  = wig_simulate(scn3); m = R.metrics;
    scn3n = scn3; scn3n.pc = pcn;
    Rn2 = wig_simulate(scn3n); m2 = Rn2.metrics;
    fprintf('%-30s 自适应: h_rms=%.4f h_err_max=%.4f h_min=%.4f ok=%d\n', ...
        G{i}{1}, m.h_rms, m.h_err_max, m.h_min, m.ok);
    fprintf('%-30s 无自适应: h_rms=%.4f h_err_max=%.4f h_min=%.4f ok=%d\n', ...
        '', m2.h_rms, m2.h_err_max, m2.h_min, m2.ok);
    res.gust{i} = R; res.gustn{i} = Rn2;

    subplot(numel(G)+1,1,i);
    plot(R.t, R.h_c, 'k--', 'LineWidth',1.0); hold on;
    plot(R.t, R.h, 'b-', Rn2.t, Rn2.h, 'r-.');
    plot(R.t, R.gust(:,2)*0.02+0.02, 'Color',[0.6 0.6 0.6]);   % 阵风示意（缩放）
    ylabel('h [m]');
    legend({wig_lbl('指令','Command'), wig_lbl('自适应','Adaptive'), ...
            wig_lbl('无自适应','No adaptation'), ...
            wig_lbl('阵风(缩放)','Gust (scaled)')}, 'Location','northeast');
    title(['(' char('a'+i-1) ') ' wig_lbl(G{i}{1}, Gen{i})]);
end
subplot(numel(G)+1,1,numel(G)+1);
plot(res.gust{3}.t, res.gust{3}.theta*180/pi, 'b-');
ylabel('\theta [deg]'); xlabel(wig_lbl('时间 t [s]','Time t [s]'));
title(wig_lbl('(d) Dryden 湍流下的俯仰角响应（自适应）', ...
              '(d) Pitch response in Dryden turbulence (adaptive)'));
wig_savefig(f8, 'fig8_gust');

%% ============================================================
%  场景 4：量测噪声 + 执行器限制 + 极限低空
%% ============================================================
fprintf('\n---- 场景 4：量测噪声 + 执行器限制 + 极限低空掠飞 ----\n');
scn4 = scn; scn4.Tend = 45.0;
scn4.ref.h = [0 0.20; 3 0.08; 12 0.06; 22 0.45; 32 0.12];
scn4.ref.V = [0 18; 8 19];
s = p.sens; s.enable = true; scn4.sens = s;
scn4.seed = 20260912;
R4 = wig_simulate(scn4); m4 = R4.metrics;
fprintf('%-30s h_rms=%.4f h_err_max=%.4f h_min=%.4f V_rms=%.4f de_max=%5.1f° ok=%d\n', ...
    '噪声+极限低空', m4.h_rms, m4.h_err_max, m4.h_min, m4.V_rms, m4.de_max*180/pi, m4.ok);
res.R4 = R4;

scn4n = scn4; scn4n.pc = pcn;
R4n = wig_simulate(scn4n); m4n = R4n.metrics;
fprintf('%-30s h_rms=%.4f h_err_max=%.4f h_min=%.4f V_rms=%.4f de_max=%5.1f° ok=%d\n', ...
    '噪声+极限低空(无自适应)', m4n.h_rms, m4n.h_err_max, m4n.h_min, m4n.V_rms, m4n.de_max*180/pi, m4n.ok);

f9 = figure('Position',[100 100 900 700]);
subplot(4,1,1);
plot(R4.t, R4.h_c, 'k--', 'LineWidth',1.0); hold on;
plot(R4.t, R4.h, 'b-', R4n.t, R4n.h, 'r-.');
ylabel('h [m]');
legend({wig_lbl('指令','Command'), wig_lbl('自适应','Adaptive'), ...
        wig_lbl('无自适应','No adaptation')}, 'Location','northeast');
title(wig_lbl('(a) 极限低空掠飞（最低指令 0.06 m）+ 量测噪声', ...
              '(a) Extreme low-altitude flight (minimum command 0.06 m) + measurement noise'));

subplot(4,1,2);
plot(R4.t, R4.V_c, 'k--', 'LineWidth',1.0); hold on; plot(R4.t, R4.V, 'b-');
ylabel('V [m/s]');
legend({wig_lbl('指令','Command'), wig_lbl('实际','Actual')}, 'Location','southeast');
title(wig_lbl('(b) 空速','(b) Airspeed'));

subplot(4,1,3);
plot(R4.t, R4.alpha*180/pi, 'b-');
ylabel('\alpha [deg]'); title(wig_lbl('(c) 迎角','(c) Angle of attack'));

subplot(4,1,4);
plot(R4.t, R4.de*180/pi, 'b-'); hold on;
yline(p.de_max*180/pi,'r--'); yline(-p.de_max*180/pi,'r--');
ylabel('\delta_e [deg]'); xlabel(wig_lbl('时间 t [s]','Time t [s]')); ylim([-28 28]);
legend({'\delta_e', wig_lbl('限幅','Limit')}, 'Location','northeast');
title(wig_lbl('(d) 升降舵','(d) Elevator deflection'));
wig_savefig(f9, 'fig9_lowalt');

save(fullfile(fileparts(mfilename('fullpath')),'..','results','scenarios.mat'), ...
     'res','ma','mn','mb','-v7.3');

fprintf('\n================ 场景仿真结束 ================\n');

end

% =====================================================================
function [R, m] = runcase(scn, pc, tag)
scn.pc = pc;
R = wig_simulate(scn);
m = R.metrics;
fprintf('%-28s h_rms=%.4f h_err_max=%.4f h_min=%.4f V_rms=%.4f de_max=%5.1f° ok=%d\n', ...
    tag, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.de_max*180/pi, m.ok);
end

% =====================================================================
function prt(tag, m)
fprintf('%-28s %9.4f %9.4f %9.4f %9.4f %9.4f %8.1f %8d\n', ...
    tag, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.V_err_max, m.de_max*180/pi, m.ok);
end
