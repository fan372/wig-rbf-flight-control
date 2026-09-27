function run_00_chk2_body()
%RUN_00_CHK2_BODY

p  = wig_params();
pt = wig_truth_params(p);

% ---- 历史调试增益（复现早期 log_chk2.txt 的工况，非出厂值） ----
% 本脚本刻意保留当时的整定中间态：k_h=3.00, k_hd=0.80, k_th=3.20, k_q=12.0,
% k_V=3.00, k_IV=0.80, Gam1=0.005, Gam2=3.0。
% 对照 wig_params.m 的最终出厂值：k_h=2.00, k_hd=0.80, k_th=3.20, k_q=6.00,
% k_V=1.53, k_IV=0.42, Gam1=0.005, Gam2=3.0。
p.ctrl.k_h = 3.00; p.ctrl.k_hd = 0.80;
p.ctrl.k_th = 3.20; p.ctrl.k_q = 12.0;
p.ctrl.k_V = 3.00; p.ctrl.k_IV = 0.80;
p.ctrl.nn.Gam1 = 0.005; p.ctrl.nn.Gam2 = 3.0;

scnA = struct(); scnA.p = p; scnA.pt = pt; scnA.Tend = 12.0; scnA.plant = 'truth';
scnA.ref.h = [0 0.20]; scnA.ref.V = [0 18];
R = wig_simulate(scnA);

dt = p.sim.dt;
gamdot_rec  = diff(R.gam)/dt;
Fperp_rec   = R.aux(:,1) + R.T.*sin(R.alpha) - pt.m*pt.g*cos(R.gam);
gamdot_pred = Fperp_rec ./ (pt.m*R.V);

fprintf('---- A 组：记录量 vs 力模型 ----\n');
fprintf('max |dgam/dt - Fperp/(mV)| = %.6e rad/s\n', ...
    max(abs(gamdot_rec - gamdot_pred(1:end-1))));

fprintf('\n t      gam[deg]    Fperp      dgam预测      dgam记录     h        V\n');
for tt = [0 0.5 1 2 3 4 5 6 8 10]
    k = round(tt/dt)+1;
    if k >= numel(R.t), continue; end
    fprintf('%5.2f %11.5f %10.3f %13.6e %13.6e %9.5f %9.5f\n', ...
        R.t(k), R.gam(k)*180/pi, Fperp_rec(k), gamdot_pred(k), gamdot_rec(k), R.h(k), R.V(k));
end

% ---- 直接复算若干时刻的导数，与有限差分对照 ----
fprintf('\n t      状态      dx(解析)        有限差分        偏差\n');
for tt = [1 3 5]
    k = round(tt/dt)+1;
    dxk = wig_dynamics(R.x(k,:)', R.u(k,:)', pt, 'truth', [0;0]);
    fd  = (R.x(k+1,:)' - R.x(k,:)')/dt;
    nm = {'V','gam','alpha','q','h','T','de'};
    for i = 2:3
        fprintf('%5.2f %8s %15.6e %15.6e %12.3e\n', R.t(k), nm{i}, dxk(i), fd(i), dxk(i)-fd(i));
    end
end

% ---- 同一状态下手算 Fperp 并与辅助量对照 ----
fprintf('\n---- 在 t=5 的状态下直接调用 wig_aero 与 wig_dynamics ----\n');
k = round(5.0/dt)+1;
x5 = R.x(k,:)';
[F5, a5] = wig_aero(x5, pt, 'truth');
dx5 = wig_dynamics(x5, R.u(k,:)', pt, 'truth', [0;0]);
fprintf('状态 = '); fprintf('%.6f ', x5); fprintf('\n');
fprintf('wig_aero L=%.4f D=%.4f M=%.4f  (记录 L=%.4f)\n', F5(1), F5(2), F5(3), R.aux(k,1));
% 分项升力全部取自 wig_aero 的 aux 输出（a5.Lw / a5.Lram / a5.Lnl / a5.Lt），
% 其中 Lnl 为升力非线性软化项，旧版本此处硬编码为 0，无法反映真实失速软化量。
fprintf('aux: Lw=%.3f Lram=%.3f Lnl=%.3f Lt=%.3f kap_w=%.4f CLw=%.4f\n', ...
    a5.Lw, a5.Lram, a5.Lnl, a5.Lt, a5.kap_w, a5.CLw);
fprintf('aux 分项校验: Lw+Lram+Lnl+Lt=%.4f  (wig_aero L=%.4f, 偏差 %.3e)\n', ...
    a5.Lw + a5.Lram + a5.Lnl + a5.Lt, F5(1), ...
    (a5.Lw + a5.Lram + a5.Lnl + a5.Lt) - F5(1));
Fperp = F5(1) + x5(6)*sin(x5(3)) - pt.m*pt.g*cos(x5(2));
fprintf('Fperp = %.4f N  -> dgam = %.6e rad/s\n', Fperp, Fperp/(pt.m*x5(1)));
fprintf('wig_dynamics 给出的 dx(2) = %.6e\n', dx5(2));
fprintf('wig_dynamics 给出的 dx(5) = %.6e  (V*sin(gam)=%.6e)\n', dx5(5), x5(1)*sin(x5(2)));

end
