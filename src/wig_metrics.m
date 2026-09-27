function M = wig_metrics(R)
%WIG_METRICS  闭环仿真跟踪性能指标
%
%   M = wig_metrics(R)   R 为 wig_simulate 的输出
%
%   统计量在"评估窗口"内计算（默认剔除前 5 s 起动瞬态）：
%       .win           评估窗口 [t_begin, t_end]
%       .h_rms .h_max  高度跟踪误差 RMS / 最大绝对值 [m]
%       .V_rms .V_max  速度跟踪误差 RMS / 最大绝对值 [m/s]
%       .q_rms         俯仰角速度 RMS [rad/s]
%       .de_rms .de_max 升降舵偏度 RMS / 最大绝对值 [rad]
%       .de_rate_max   升降舵最大角速率 [rad/s]
%       .theta_rms     俯仰角波动 RMS [rad]
%       .h_settle      最后一次高度阶跃的调节时间（2% 带）[s]
%       .W1n_end .W2n_end  终值权值范数
%       .h_min         仿真中最低离地高度 [m]（安全裕度）
%       .ok            是否全程未发散、未触地

t = R.t;
e_h = R.h - R.h_c;
e_V = R.V - R.V_c;

t_beg = min(5.0, 0.25*t(end));
idx = t >= t_beg;
if ~any(idx)
    idx = true(size(t));
end
M.win = [t(find(idx,1,'first')), t(end)];

M.h_rms = sqrt(mean(e_h(idx).^2));
M.h_err_max = max(abs(e_h(idx)));
M.V_rms = sqrt(mean(e_V(idx).^2));
M.V_err_max = max(abs(e_V(idx)));
M.q_rms = sqrt(mean(R.q(idx).^2));
M.theta_rms = sqrt(mean((R.theta(idx) - mean(R.theta(idx))).^2));
M.de_rms = sqrt(mean(R.de(idx).^2));
M.de_max = max(abs(R.de(idx)));

de_rate = [0; diff(R.de)] / (t(2)-t(1));
M.de_rate_max = max(abs(de_rate));

M.h_min = min(R.h);
M.h_max_alt = max(R.h);

% ---- 最后一次高度阶跃的调节时间（2% 带，取阶跃后 60 s 内） ----
M.h_settle = NaN;
if isfield(R.scn,'ref') && isfield(R.scn.ref,'h') && size(R.scn.ref.h,1) >= 2
    tbl = R.scn.ref.h;
    tj  = tbl(end,1);
    if tj > 0 && tj < t(end)
        hj   = tbl(end,2);
        band = 0.02 * max(abs(hj), 0.05);
        ii   = find(t >= tj);
        e2   = abs(R.h(ii) - hj);
        kk   = find(e2 > band, 1, 'last');
        if isempty(kk)
            M.h_settle = 0;
        else
            M.h_settle = t(ii(kk)) - tj;
        end
    end
end

M.W1n_end = R.DBG.W1norm(end);
M.W2n_end = R.DBG.W2norm(end);

M.ok = all(isfinite(R.x(:))) && (M.h_min > 0.0) && (max(abs(R.q)) < 20);

end
