function run_00_dbg_body()
%RUN_00_DBG_BODY  对照调试主体
%   A: 恒定指令 + 真实对象（应保持不动）
%   B: 机动指令 + 真实对象（含地效失配）
%   C: 机动指令 + 名义对象（无失配）
%   三组均使用【历史调试增益】（见下方注释，非 wig_params.m 出厂值）。

p  = wig_params();
pt = wig_truth_params(p);

% ---- 历史调试增益（复现早期 log_dbg.txt 的工况，非出厂值） ----
% 与 wig_params.m 的最终出厂值对照：k_h=2.00, k_hd=0.80, k_th=3.20, k_q=6.00,
% k_V=1.53, k_IV=0.42, Gam1=0.005, Gam2=3.0。此处保留历史整定中间态：
p.ctrl.k_h   = 3.00;  p.ctrl.k_hd  = 0.80;
p.ctrl.k_th  = 3.20;  p.ctrl.k_q   = 12.0;
p.ctrl.k_V   = 3.00;  p.ctrl.k_IV  = 0.80;
p.ctrl.nn.Gam1 = 0.005; p.ctrl.nn.Gam2 = 3.0;

% ---------------- A ----------------
scnA = struct(); scnA.p = p; scnA.pt = pt; scnA.Tend = 12.0; scnA.plant = 'truth';
scnA.ref.h = [0 0.20]; scnA.ref.V = [0 18];
RA = wig_simulate(scnA);
fprintf('---- A: 恒定指令 + 真实对象 ----\n');
fprintf('末端 h=%.5f (指令 %.3f)  V=%.4f  alpha=%.4f deg  de=%.3f deg  T=%.4f  W1n=%.3f W2n=%.3f\n', ...
    RA.h(end), RA.h_c(end), RA.V(end), RA.alpha(end)*180/pi, RA.de(end)*180/pi, RA.T(end), ...
    RA.DBG.W1norm(end), RA.DBG.W2norm(end));
fprintf('h_min=%.5f  h_max=%.5f  e_h rms=%.5f  de_max=%.3f deg\n\n', ...
    min(RA.h), max(RA.h), RA.metrics.h_rms, RA.metrics.de_max*180/pi);
print_hist(RA, 1.0);

% ---------------- B ----------------
scnB = struct(); scnB.p = p; scnB.pt = pt; scnB.Tend = 20.0; scnB.plant = 'truth';
scnB.ref.h = [0 0.20; 3 0.35; 9 0.10; 15 0.25];
scnB.ref.V = [0 18; 6 20];
RB = wig_simulate(scnB);
fprintf('\n---- B: 机动指令 + 真实对象 ----\n');
fprintf('h_min=%.4f  e_h rms=%.4f  e_V rms=%.4f  de_max=%.3f deg\n\n', ...
    RB.metrics.h_min, RB.metrics.h_rms, RB.metrics.V_rms, RB.metrics.de_max*180/pi);
print_hist(RB, 0.5);

% ---------------- C ----------------
scnC = scnB; scnC.pt = p; scnC.plant = 'nominal';
RC = wig_simulate(scnC);
fprintf('\n---- C: 机动指令 + 名义对象（无失配） ----\n');
fprintf('h_min=%.4f  e_h rms=%.4f  e_V rms=%.4f  de_max=%.3f deg\n\n', ...
    RC.metrics.h_min, RC.metrics.h_rms, RC.metrics.V_rms, RC.metrics.de_max*180/pi);
print_hist(RC, 0.5);

end

% =====================================================================
function print_hist(R, dtp)
step = max(1, round(dtp / (R.t(2)-R.t(1))));
fprintf('   t     h_c      h       V_c      V     alpha    theta     gam       q       de       T     e_h      e_q      W1n\n');
for k = 1:step:numel(R.t)
    fprintf('%6.2f %7.4f %8.5f %7.2f %7.3f %7.3f %8.3f %7.3f %8.4f %8.3f %7.3f %8.4f %8.4f %7.3f\n', ...
        R.t(k), R.h_c(k), R.h(k), R.V_c(k), R.V(k), R.alpha(k)*180/pi, ...
        R.theta(k)*180/pi, R.gam(k)*180/pi, R.q(k), R.de(k)*180/pi, R.T(k), ...
        R.DBG.e_h(k), R.DBG.e_q(k), R.DBG.W1norm(k));
end
fprintf('\n   t      L      D      M      Lw     Lt     Dw     Dt    qbar   kap_w   CLw    Fperp\n');
for k = 1:step:numel(R.t)
    L = R.aux(k,1); D = R.aux(k,2); M = R.aux(k,3);
    Lw = R.aux(k,4); Lt = R.aux(k,5);
    qbar = R.aux(k,8);
    Fperp = L + R.T(k)*sin(R.alpha(k)) - R.scn.pt.m*R.scn.pt.g*cos(R.gam(k));
    fprintf('%6.2f %7.2f %7.2f %7.3f %7.2f %7.2f %6.2f %6.3f %7.2f %7.4f %7.4f %8.3f\n', ...
        R.t(k), L, D, M, Lw, Lt, R.aux(k,6), R.aux(k,7), qbar, R.kap(k,1), R.kap(k,3), Fperp);
end
end
