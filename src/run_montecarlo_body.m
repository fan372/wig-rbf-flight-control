function run_montecarlo_body()
%RUN_MONTECARLO_BODY  蒙特卡洛主体

wig_plot_style();
p  = wig_params();
N  = 60;

fprintf('================ 蒙特卡洛鲁棒性统计 ================\n');
fprintf('样本数 N = %d，随机摄动：质量 ±25%%、惯量 ±25%%、C_D0 ±40%%、a0 ±10%%、\n', N);
fprintf('C_mac ±30%%、地效强度参数 ±60%%/±20%%、下洗梯度 ±40%%、尾翼效率 ±15%%、\n');
fprintf('初始高度偏差 ±0.03 m、初始速度偏差 ±1.0 m/s\n\n');

rng(20260912);

scn0 = struct(); scn0.p = p; scn0.Tend = 30.0; scn0.plant = 'truth';
scn0.ref.h = [0 0.20; 3 0.35; 11 0.10; 19 0.25];
scn0.ref.V = [0 18; 6 20];

Hs   = cell(N,1);
ts   = [];
rms  = zeros(N,1); emax = zeros(N,1); hmin = zeros(N,1);
okv  = false(N,1); vmax = zeros(N,1);
rmsn = zeros(N,1); emaxn = zeros(N,1); okn = false(N,1);
W1n  = zeros(N,1); W2n = zeros(N,1);

for i = 1:N
    % ---- 随机摄动 ----
    pt = wig_truth_params(p, ...
        'm',     p.m    *(1 + 0.25*(2*rand-1)), ...
        'Iyy',   p.Iyy  *(1 + 0.25*(2*rand-1)), ...
        'CD0',   p.CD0  *(1 + 0.40*(2*rand-1)), ...
        'CD0t',  p.CD0t *(1 + 0.40*(2*rand-1)), ...
        'a0',    p.a0   *(1 + 0.10*(2*rand-1)), ...
        'Cmac',  p.Cmac *(1 + 0.30*(2*rand-1)), ...
        'ge_A',  p.ge_A *(1 + 0.60*(2*rand-1)), ...
        'ge_n',  p.ge_n *(1 + 0.20*(2*rand-1)), ...
        'eps_a', p.eps_a*(1 + 0.40*(2*rand-1)), ...
        'eta_t', 0.95   *(1 + 0.15*(2*rand-1)));

    scn = scn0; scn.pt = pt;
    trm = wig_trim(p.V0, p.h0, pt, 'truth');
    x0 = trm.x;
    x0(5) = max(p.h0 + 0.03*(2*rand-1), 0.02);
    x0(1) = p.V0 + 1.0*(2*rand-1);
    scn.x0 = x0;

    R = wig_simulate(scn);
    m = R.metrics;
    Hs{i} = R.h;  ts = R.t;
    rms(i)=m.h_rms; emax(i)=m.h_err_max; hmin(i)=m.h_min; okv(i)=m.ok;
    vmax(i)=m.V_err_max; W1n(i)=R.DBG.W1norm(end); W2n(i)=R.DBG.W2norm(end);

    pcn = p; pcn.ctrl.enable_nn = false;
    scn2 = scn; scn2.pc = pcn;
    R2 = wig_simulate(scn2);
    m2 = R2.metrics;
    rmsn(i)=m2.h_rms; emaxn(i)=m2.h_err_max; okn(i)=m2.ok;
end

Hm = zeros(numel(ts), N);
for i = 1:N, Hm(:,i) = Hs{i}; end

fprintf('---- 统计结果 ----\n');
fprintf('%-22s %10s %10s %10s %10s %10s\n','指标','均值','标准差','中位数','95分位','最大值');
stat('高度误差 RMS [m]',   rms,  '%.5f');
stat('高度误差 峰值 [m]',  emax, '%.5f');
stat('最低离地高度 [m]',   hmin, '%.5f');
stat('速度误差 峰值 [m/s]',vmax, '%.5f');
fprintf('\n通过率（未触地且收敛）: 自适应 %d/%d = %.1f%%   无自适应 %d/%d = %.1f%%\n', ...
    sum(okv), N, 100*sum(okv)/N, sum(okn), N, 100*sum(okn)/N);
fprintf('高度误差 RMS 中位数:  自适应 %.5f m   无自适应 %.5f m   （改善 %.1f 倍）\n', ...
    median(rms), median(rmsn), median(rmsn)/max(median(rms),1e-9));
fprintf('高度误差 峰值 中位数: 自适应 %.5f m   无自适应 %.5f m\n', median(emax), median(emaxn));
fprintf('权值范数终值: ||W1|| 均值 %.3f (max %.3f), ||W2|| 均值 %.3f (max %.3f)\n', ...
    mean(W1n), max(W1n), mean(W2n), max(W2n));

env_lo = min(Hm, [], 2);
env_hi = max(Hm, [], 2);
env_p5 = prctile(Hm, 5, 2);
env_p95= prctile(Hm, 95, 2);

f10 = figure('Position',[100 100 950 620]);
subplot(2,2,[1 2]);
hold on;
plot(ts, Hm, '-', 'Color', [0.75 0.82 0.92]);
plot(ts, env_p5, 'b-', 'LineWidth', 1.6);
plot(ts, env_p95,'b-', 'LineWidth', 1.6);
plot(ts, env_hi, 'b:', 'LineWidth', 1.0);
plot(ts, env_lo, 'b:', 'LineWidth', 1.0);
plot(ts, scn0.ref.h(1,2)*ones(size(ts)), 'k--');
stairs([scn0.ref.h(:,1); scn0.Tend], [scn0.ref.h(:,2); scn0.ref.h(end,2)], 'k--', 'LineWidth',1.2);
xlabel(wig_lbl('时间 t [s]','Time t [s]'));
ylabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
title(sprintf(wig_lbl(['(a) %d 次随机参数摄动的高度响应包络' ...
                       '（蓝实线：5%%/95%% 分位）'], ...
                      ['(a) Altitude response envelope over %d random ' ...
                       'parameter perturbations (blue solid: 5%%/95%% percentiles)']), N));
% 图例逐项对应上面 7 个绘图对象，顺序一致（旧版本只有 6 项，且标签写成 %%
% 导致图例显示成 "5%%分位"；此处为普通 cell 字符串，百分号必须写单个 %）：
%   1 样本（灰色细线） 2 5% 分位 3 95% 分位 4 上极值包络 5 下极值包络
%   6 常值指令 0.20 m  7 高度指令（阶梯）
legend({wig_lbl('样本','Samples'), ...
        wig_lbl('5%分位','5th percentile'), ...
        wig_lbl('95%分位','95th percentile'), ...
        wig_lbl('极值包络（上）','Extreme envelope (upper)'), ...
        wig_lbl('极值包络（下）','Extreme envelope (lower)'), ...
        wig_lbl('指令基准 0.20 m','Command baseline 0.20 m'), ...
        wig_lbl('高度指令','Altitude command')}, 'Location','northeast');

subplot(2,2,3);
histogram(emax, 12); hold on;
xline(median(emax), 'b-', 'LineWidth', 1.5);
xlabel(wig_lbl('高度误差峰值 [m]','Peak altitude error [m]'));
ylabel(wig_lbl('样本数','Number of samples'));
title(wig_lbl('(b) 自适应：高度误差峰值分布', ...
              '(b) Adaptive: peak altitude-error distribution'));

subplot(2,2,4);
histogram(emaxn, 12); hold on;
xline(median(emaxn), 'r-', 'LineWidth', 1.5);
xlabel(wig_lbl('高度误差峰值 [m]','Peak altitude error [m]'));
ylabel(wig_lbl('样本数','Number of samples'));
title(wig_lbl('(c) 无自适应：高度误差峰值分布', ...
              '(c) No adaptation: peak altitude-error distribution'));
wig_savefig(f10, 'fig10_montecarlo');

save(fullfile(fileparts(mfilename('fullpath')),'..','results','montecarlo.mat'), ...
     'rms','emax','hmin','okv','rmsn','emaxn','okn','W1n','W2n','env_lo','env_hi', ...
     'env_p5','env_p95','Hm','ts');

fprintf('\n================ 蒙特卡洛结束 ================\n');

end

% =====================================================================
function stat(name, v, fmt)
q = prctile(v, 95);
fprintf(['%-22s ' fmt ' ' fmt ' ' fmt ' ' fmt ' ' fmt '\n'], ...
    name, mean(v), std(v), median(v), q, max(v));
end
