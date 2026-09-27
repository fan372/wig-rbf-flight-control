function run_00_chk_body()
%RUN_00_CHK_BODY  一致性核验主体

p  = wig_params();
pt = wig_truth_params(p);

% ---------- A. 开环纯积分：配平点 + 配平控制，应保持不动 ----------
fprintf('=========== 积分一致性核验 ===========\n\n');
fprintf('---- A. 开环：真实配平点 + 固定配平控制 ----------\n');
trm = wig_trim(p.V0, 0.20, pt, 'truth');
fprintf('配平: V=%.5f h=%.5f alpha=%.6f rad de=%.6f rad T=%.5f N\n', ...
    trm.V, trm.h, trm.alpha, trm.de, trm.T);
fprintf('配平残差: %.3e %.3e %.3e\n', trm.res(1), trm.res(2), trm.res(3));

x = trm.x; u = trm.u;
dx = wig_dynamics(x, u, pt, 'truth', []);
fprintf('dx(t=0) = [%.3e %.3e %.3e %.3e %.3e %.3e %.3e]\n\n', dx);

dt = 0.001; Tn = 3.0;
% 第 5 列为 dh/dt 的【有限差分】估计：内部样本用中心差分 (h_{k+1}-h_{k-1})/(2*dt)，
% 首样本无 h_{k-1}，退化为前向差分 (h_{k+1}-h_k)/dt；与第 6 列的解析式
% V*sin(gam) 互为独立校验（旧版本此列误填 V*sin(gam)，与第 6 列完全重复）。
fprintf('  t      gam[deg]     h        V      dh/dt[有限差分]  V*sin(gam)    dgam/dt记录   Fperp/(mV)\n');
xx = x; t = 0;
h_prev = NaN;                      % h(t-dt)，用于中心差分
for k = 1:round(Tn/dt)
    k1 = wig_dynamics(xx,              u, pt, 'truth', []);
    k2 = wig_dynamics(xx + 0.5*dt*k1,  u, pt, 'truth', []);
    k3 = wig_dynamics(xx + 0.5*dt*k2,  u, pt, 'truth', []);
    k4 = wig_dynamics(xx + dt*k3,      u, pt, 'truth', []);
    xx_next = xx + (dt/6)*(k1 + 2*k2 + 2*k3 + k4);

    if mod(k, 500) == 1
        F = wig_aero(xx, pt, 'truth');
        Fperp = F(1) + xx(6)*sin(xx(3)) - pt.m*pt.g*cos(xx(2));
        if isnan(h_prev)
            hdot_fd = (xx_next(5) - xx(5))/dt;           % 端点：前向差分
        else
            hdot_fd = (xx_next(5) - h_prev)/(2*dt);      % 内部：中心差分
        end
        fprintf('%5.2f %11.6f %9.6f %9.5f %13.6e %13.6e %13.6e %13.6e\n', ...
            t, xx(2)*180/pi, xx(5), xx(1), hdot_fd, xx(1)*sin(xx(2)), ...
            Fperp/(pt.m*xx(1)), Fperp/(pt.m*xx(1)));
    end

    h_prev = xx(5);
    xx = xx_next;
    t = t + dt;
end
fprintf('\n开环 3 s 后: gam=%.6f deg, h=%.6f, V=%.5f\n\n', xx(2)*180/pi, xx(5), xx(1));

% ---------- B. 闭环记录的自洽性核验 ----------
fprintf('---- B. 闭环记录自洽性（真实对象 + 自适应） ----------\n');
scn = struct(); scn.p = p; scn.pt = pt; scn.Tend = 6.0; scn.plant = 'truth';
scn.ref.h = [0 0.20]; scn.ref.V = [0 18];
R = wig_simulate(scn);

hdot_rec = diff(R.h)/dt;
gamdot_rec = diff(R.gam)/dt;
Vsin = R.V(1:end-1).*sin(R.gam(1:end-1));

Fperp = R.aux(:,1) + R.T.*sin(R.alpha) - pt.m*pt.g*cos(R.gam);
gamdot_pred = Fperp ./ (pt.m*R.V);

fprintf('dh/dt 与 V*sin(gam) 最大偏差 = %.6e m/s\n', max(abs(hdot_rec - Vsin)));
fprintf('dgam/dt 与 Fperp/(mV) 最大偏差 = %.6e rad/s\n', ...
    max(abs(gamdot_rec - gamdot_pred(1:end-1))));

% 直接复算 derivatives 与记录对比
kk = round(1.0/dt) + 1;
dxk = wig_dynamics(R.x(kk,:)', R.u(kk,:)', pt, 'truth', [0;0]);
fd  = (R.x(kk+1,:)' - R.x(kk,:)')/dt;
fprintf('\nt=%.2f 处：\n', R.t(kk));
nm = {'V','gam','alpha','q','h','T','de'};
fprintf('%8s %16s %16s\n', '状态', 'dx(解析)', '有限差分');
for i = 1:7
    fprintf('%8s %16.6e %16.6e\n', nm{i}, dxk(i), fd(i));
end

% ---------- C. 检查状态是否被错误地重置 ----------
fprintf('\n---- C. 状态上下限触发情况 ----\n');
fprintf('min(V)=%.5f  max(|q|)=%.5f  min(h)=%.6f  max(T)=%.3f  min(T)=%.3f\n', ...
    min(R.V), max(abs(R.q)), min(R.h), max(R.T), min(R.T));

fprintf('\n=========== 核验结束 ===========\n');

end
