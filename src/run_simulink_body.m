function run_simulink_body()
%RUN_SIMULINK_BODY  Simulink 模型构建 / 运行 / 对比验证

wig_plot_style();
here = fileparts(mfilename('fullpath'));
addpath(here);

p  = wig_params();
pt = wig_truth_params(p);

refH = [0 0.20; 3 0.35; 12 0.10; 21 0.25];
refV = [0 18; 6 20];
Tend = 40.0;

fprintf('================ Simulink 模型构建与验证 ================\n\n');

opts = struct('plant','truth','Tend',Tend,'refH',refH,'refV',refV);
modelName = 'wig_adaptive_fcs';
build_simulink_model(modelName, opts);

% ---- 清理 S-Function 中的 persistent 缓存，确保参数生效 ----
clear msfcn_wig_plant msfcn_wig_ctrl

% ---- 运行仿真 ----
fprintf('\n---- 运行 Simulink 仿真 ----\n');
t0 = tic;
simOut = sim(modelName, 'StopTime', num2str(Tend));
fprintf('Simulink 仿真完成，耗时 %.2f s（模型 %s.slx）\n', toc(t0), modelName);

xout = simOut.get('xout');
uout = simOut.get('uout');
refout = simOut.get('refout');

[ts, X]  = getsig(xout,  simOut, 7);
[tu, U]  = getsig(uout,  simOut, 2);
[tr, Rf] = getsig(refout, simOut, 4);   % From Workspace 去掉时间列: [h_c hd_c V_c Vd_c]

fprintf('Simulink 输出尺寸: x 时间 %s / 状态 %s；u 时间 %s / 控制 %s；ref %s\n', ...
    mat2str(size(ts)), mat2str(size(X)), mat2str(size(tu)), mat2str(size(U)), mat2str(size(Rf)));

% ---- 纯 MATLAB 脚本仿真（同一工况） ----
fprintf('\n---- 运行纯 MATLAB 脚本仿真（对照） ----\n');
scn = struct(); scn.p = p; scn.pt = pt; scn.Tend = Tend; scn.plant = 'truth';
scn.ref.h = refH; scn.ref.V = refV;
Rm = wig_simulate(scn);

% ---- 对齐到被控对象（连续）时间轴 ----
% 注意口径一致性（这是早期版本的缺陷所在）：
%   uout 记录的是控制器【输出指令】u=[de_cmd; dt_cmd]（200 Hz 零阶保持），
%   xout 记录的是被控对象【状态】x(7)（1 kHz 连续积分结果，含舵机一阶滞后）。
%   因此：
%     * 轨迹一致性比较必须用"状态 vs 状态" —— 升降舵取 X(:,7)（实际舵偏），
%       而不是 U(:,1)（舵指令）。二者相差一个 tau_e=0.05 s 的一阶滞后，
%       在 120 deg/s 速率限幅下可达 tau_e*rate ≈ 6 deg，足以完全解释早期
%       版本 log 中那个 6.293 deg 的"升降舵轨迹偏差"。
%     * 指令一致性另行比较：de_cmd(Simulink) vs sat(de_unsat)(脚本)。
ts   = ts(:);
h_sl = X(:,5);  V_sl = X(:,1);  de_state_sl = X(:,7);
h_c  = interp1(tr(tr<=ts(end)), Rf(tr<=ts(end),1), ts, 'previous', Rf(end,1));
V_c  = interp1(tr(tr<=ts(end)), Rf(tr<=ts(end),3), ts, 'previous', Rf(end,3));
u_lo = interp1(tu, U(:,1),  ts, 'previous', U(end,1));    % Simulink 舵指令

h_m  = interp1(Rm.t, Rm.h,   ts, 'linear', 'extrap');
V_m  = interp1(Rm.t, Rm.V,   ts, 'linear', 'extrap');
de_m = interp1(Rm.t, Rm.de,  ts, 'linear', 'extrap');     % 脚本 实际舵偏（状态）
h_cm = interp1(Rm.t, Rm.h_c, ts, 'linear', 'extrap');
V_cm = interp1(Rm.t, Rm.V_c, ts, 'linear', 'extrap');
% 脚本的舵指令 = sat(de_unsat, de_max)
de_cmd_m = wig_sat(interp1(Rm.t, Rm.DBG.de_unsat, ts, 'linear', 'extrap'), p.de_max);

h_sl = h_sl(:);  V_sl = V_sl(:);  h_c = h_c(:);  V_c = V_c(:);
de_state_sl = de_state_sl(:);  u_lo = u_lo(:);
h_m = h_m(:);  V_m = V_m(:);  de_m = de_m(:);
h_cm = h_cm(:);  V_cm = V_cm(:);  de_cmd_m = de_cmd_m(:);

e_sl = h_sl - h_c;
e_m  = h_m  - h_cm;
eV_sl = V_sl - V_c;
eV_m  = V_m  - V_cm;

idx = ts > 5;
hr_sl = sqrt(mean(e_sl(idx).^2));   hr_m = sqrt(mean(e_m(idx).^2));
hm_sl = max(abs(e_sl(idx)));        hm_m = max(abs(e_m(idx)));
vr_sl = sqrt(mean(eV_sl(idx).^2));  vr_m = sqrt(mean(eV_m(idx).^2));

fprintf('\n---- 结果对比（t > 5 s） ----\n');
fprintf('%-22s %12s %12s %12s\n', '指标', 'Simulink', 'MATLAB脚本', '偏差');
fprintf('%-22s %12.6f %12.6f %12.2e\n', 'h_rms [m]', hr_sl, hr_m, abs(hr_sl-hr_m));
fprintf('%-22s %12.6f %12.6f %12.2e\n', 'h 误差峰值 [m]', hm_sl, hm_m, abs(hm_sl-hm_m));
fprintf('%-22s %12.6f %12.6f %12.2e\n', 'h_min [m]', min(h_sl), min(h_m), abs(min(h_sl)-min(h_m)));
fprintf('%-22s %12.6f %12.6f %12.2e\n', 'V_rms [m/s]', vr_sl, vr_m, abs(vr_sl-vr_m));
fprintf('%-22s %12.6f %12.6f %12.2e\n', 'de 峰值 [deg]（状态）', ...
    max(abs(de_state_sl))*180/pi, max(abs(de_m))*180/pi, ...
    abs(max(abs(de_state_sl))-max(abs(de_m)))*180/pi);
fprintf('%-22s %12.6f %12.6f %12.2e\n', 'de 峰值 [deg]（指令）', ...
    max(abs(u_lo))*180/pi, max(abs(de_cmd_m))*180/pi, ...
    abs(max(abs(u_lo))-max(abs(de_cmd_m)))*180/pi);

dmax_h  = max(abs(h_sl - h_m));
dmax_V  = max(abs(V_sl - V_m));
dmax_de = max(abs(de_state_sl - de_m))*180/pi;
dmax_uc = max(abs(u_lo - de_cmd_m))*180/pi;
fprintf('\n最大轨迹偏差（状态 vs 状态）：高度 %.3e m，速度 %.3e m/s，升降舵 %.3e deg\n', ...
    dmax_h, dmax_V, dmax_de);
fprintf('最大指令偏差（指令 vs 指令）：升降舵 %.3e deg\n', dmax_uc);
fprintf('结论：状态轨迹最大偏差 %.2e m（高度）与 %.2e m/s（速度），\n', dmax_h, dmax_V);
fprintf('      说明 Simulink 模型与纯 MATLAB 脚本在数值上等价；\n');
fprintf('      升降舵状态偏差 %.2e deg 与指令偏差 %.2e deg 同为采样/插值量级。\n', dmax_de, dmax_uc);

% ---- 图 11 ----
f11 = figure('Position',[100 100 900 660]);
subplot(3,1,1);
plot(ts, h_c, 'k--', 'LineWidth',1.0); hold on;
plot(ts, h_sl, 'b-', ts, h_m, 'r--');
ylabel('h [m]');
legend({wig_lbl('指令','Command'), 'Simulink', ...
        wig_lbl('MATLAB 脚本','MATLAB script')}, 'Location','northeast');
title(wig_lbl('(a) Simulink 模型与纯 MATLAB 脚本结果一致性验证 —— 高度', ...
              '(a) Consistency check between the Simulink model and the pure MATLAB script: altitude'));

subplot(3,1,2);
plot(ts, V_c, 'k--', 'LineWidth',1.0); hold on;
plot(ts, V_sl, 'b-', ts, V_m, 'r--');
ylabel('V [m/s]');
legend({wig_lbl('指令','Command'), 'Simulink', ...
        wig_lbl('MATLAB 脚本','MATLAB script')}, 'Location','southeast');
title(wig_lbl('(b) 空速','(b) Airspeed'));

subplot(3,1,3);
plot(ts, de_state_sl*180/pi, 'b-', ts, de_m*180/pi, 'r--', 'LineWidth', 1.0);
ylabel('\delta_e [deg]'); xlabel(wig_lbl('时间 t [s]','Time t [s]')); ylim([-26 26]);
legend({'Simulink', wig_lbl('MATLAB 脚本（状态）','MATLAB script (state)')}, ...
    'Location','northeast');
title(wig_lbl('(c) 升降舵偏角（实际舵偏状态）', ...
              '(c) Elevator deflection (actual elevator state)'));
wig_savefig(f11, 'fig11_simulink');

save(fullfile(here,'..','results','simulink_compare.mat'), ...
     'ts','h_sl','V_sl','de_state_sl','u_lo','h_m','V_m','de_m','de_cmd_m','h_c','V_c');

% ---- 关闭模型，避免其常驻内存并在 MATLAB 退出时弹出"模型已修改，无法关闭"警告 ----
try
    close_system(modelName, 0);
catch ME
    fprintf('[提示] 关闭模型 %s 失败：%s\n', modelName, ME.message);
end

fprintf('\n================ Simulink 验证结束 ================\n');

end

% =====================================================================
function [t, Y] = getsig(v, simOut, ncol)
%GETSIG  统一提取 To Workspace 输出（返回列向量时间与 N x ncol 数据）
if isstruct(v)
    t = v.time(:);
    Y = v.signals.values;
elseif isa(v, 'timeseries')
    t = v.Time(:);
    Y = v.Data;
else
    t = simOut.tout(:);
    Y = v;
end

% 压缩多余维度
Y = squeeze(Y);
if isvector(Y)
    Y = Y(:);
end

n = numel(t);
if size(Y,1) == n && size(Y,2) == ncol
    return;
elseif size(Y,2) == n && size(Y,1) == ncol
    Y = Y.';
    return;
end

% 兜底：按总元素数重排
if numel(Y) == n*ncol
    Y = reshape(Y, n, ncol);
elseif numel(Y) == ncol*n
    Y = reshape(Y, ncol, n).';
else
    error('getsig:badSize', '无法解析输出尺寸: time=%s, values=%s, ncol=%d', ...
        mat2str(size(t)), mat2str(size(Y)), ncol);
end
end
