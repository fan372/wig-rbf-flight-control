function run_00_smoke_body()
%RUN_00_SMOKE_BODY  冒烟测试主体（由 wig_logged 调用以便捕获文本输出）

fprintf('=========== WIG 仿真冒烟测试 ===========\n');

p  = wig_params();
pt = wig_truth_params(p);

fprintf('\n---- 1. 参数检查 ----\n');
fprintf('S=%.4f m^2  AR=%.3f  W=%.3f N  T/W=%.3f\n', p.S, p.AR, p.m*p.g, p.Tmax/(p.m*p.g));
fprintf('V=%.1f m/s 时需要 CL ~ %.3f\n', p.V0, p.m*p.g/(0.5*p.rho*p.V0^2*p.S));

fprintf('\n---- 2. 地效因子与有效升力线斜率 ----\n');
hh = [0.05 0.10 0.15 0.25 0.35 0.50 1.00];
fprintf('  h[m]   h/b     kap_nom  kap_true   aw_nom   aw_true   CDi/CDi_free(nom)\n');
for k = 1:numel(hh)
    kn = wig_ge(hh(k), p.b, p);
    kt = wig_ge(hh(k), p.b, pt);
    awn = p.a0 /(1 + p.a0 *kn/(pi*p.AR*p.e));
    awt = pt.a0/(1 + pt.a0*kt/(pi*pt.AR*pt.e));
    fprintf('%6.3f %7.4f %8.4f %9.4f %9.4f %9.4f %12.4f\n', ...
        hh(k), hh(k)/p.b, kn, kt, awn, awt, kn);
end

fprintf('\n---- 3. 配平（名义对象） ----\n');
fprintf('  h[m]   alpha[deg]  de[deg]   dt      T[N]    CL      CD      L/D    ok   res\n');
for k = 1:numel(hh)
    trm = wig_trim(p.V0, hh(k), p, 'nominal');
    fprintf('%6.3f %10.4f %9.4f %7.4f %7.3f %7.4f %7.5f %6.1f %5d %9.1e\n', ...
        hh(k), trm.alpha*180/pi, trm.de*180/pi, trm.dt, trm.T, trm.CL, trm.CD, ...
        trm.L_D, trm.ok, norm(trm.res,inf));
end

fprintf('\n---- 4. 配平（真实对象：地效失配 + RAM + 非线性） ----\n');
fprintf('  h[m]   alpha[deg]  de[deg]   dt      T[N]    CL      CD      L/D    ok   res\n');
TR = cell(numel(hh),1);
for k = 1:numel(hh)
    trm = wig_trim(p.V0, hh(k), pt, 'truth');
    TR{k} = trm;
    fprintf('%6.3f %10.4f %9.4f %7.4f %7.3f %7.4f %7.5f %6.1f %5d %9.1e\n', ...
        hh(k), trm.alpha*180/pi, trm.de*180/pi, trm.dt, trm.T, trm.CL, trm.CD, ...
        trm.L_D, trm.ok, norm(trm.res,inf));
end

fprintf('\n---- 5. 名义/真实模型失配量（在真实配平点上评估，de 置零） ----\n');
fprintf('  h[m]    dM0[N·m]   dL[N]     dD[N]\n');
for k = 1:numel(hh)
    x = TR{k}.x;  x(7) = 0;
    Fn = wig_aero(x, p,  'nominal');
    Ft = wig_aero(x, pt, 'truth');
    fprintf('%6.3f %10.4f %9.3f %9.3f\n', hh(k), Fn(3)-Ft(3), Fn(1)-Ft(1), Fn(2)-Ft(2));
end

fprintf('\n---- 6. 纵向模态随离地高度变化（真实对象） ----\n');
fprintf('  h[m]   短周期 wn/zeta     浮沉(长周期) wn/zeta     高度实根\n');
for k = 1:numel(hh)
    lin = wig_linearize(TR{k}, pt, 'truth');
    ev  = lin.eig;
    sp = ev(abs(imag(ev))>0.1 & abs(ev)>2 & abs(ev)<15);
    lp = ev(abs(imag(ev))>0.1 & abs(ev)<=2);
    hr = ev(abs(imag(ev))<=0.1 & abs(ev)<2 & abs(ev)>1e-6);
    if ~isempty(sp)
        sp = sp(1);
        sps = sprintf('%6.3f/%+6.3f', abs(sp), -real(sp)/abs(sp));
    else
        sps = '    ---       ';
    end
    if ~isempty(lp)
        lp = lp(1);
        lps = sprintf('%6.3f/%+6.3f', abs(lp), -real(lp)/abs(lp));
    else
        lps = '    ---       ';
    end
    if ~isempty(hr)
        hrs = sprintf('%+8.3f', real(hr(1)));
    else
        hrs = '   ---  ';
    end
    fprintf('%6.3f   %s        %s        %s\n', hh(k), sps, lps, hrs);
end

fprintf('\n---- 7. 闭环仿真 8 s（真实对象 + RBF 自适应） ----\n');
scn = struct();
scn.p = p; scn.pt = pt; scn.Tend = 8.0;
scn.ref.h = [0 p.h0; 3.0 p.h0+0.05];
scn.ref.V = [0 p.V0];
scn.plant = 'truth';
t0 = tic;
R = wig_simulate(scn);
fprintf('仿真耗时 %.2f s, %d 步\n', toc(t0), numel(R.t));
fprintf('末态: h=%.4f m (指令 %.4f), V=%.4f m/s, alpha=%.3f deg, theta=%.3f deg\n', ...
    R.h(end), R.h_c(end), R.V(end), R.alpha(end)*180/pi, R.theta(end)*180/pi);
fprintf('e_h: rms=%.4f m  max=%.4f m | e_V: rms=%.4f m/s\n', ...
    R.metrics.h_rms, R.metrics.h_err_max, R.metrics.V_rms);
fprintf('de: 末值=%.3f deg  max=%.3f deg | W1norm=%.4f W2norm=%.4f\n', ...
    R.de(end)*180/pi, R.metrics.de_max*180/pi, R.DBG.W1norm(end), R.DBG.W2norm(end));
fprintf('h_min=%.4f m  ok=%d\n', R.metrics.h_min, R.metrics.ok);

fprintf('\n---- 8. 闭环仿真 8 s（真实对象 + 关闭自适应与鲁棒项） ----\n');
pc = p; pc.ctrl.enable_nn = false; pc.ctrl.enable_rob = false;
scn2 = scn; scn2.pc = pc;
R2 = wig_simulate(scn2);
fprintf('末态: h=%.4f m (指令 %.4f), V=%.4f m/s\n', R2.h(end), R2.h_c(end), R2.V(end));
fprintf('e_h: rms=%.4f m  max=%.4f m | e_V: rms=%.4f m/s\n', ...
    R2.metrics.h_rms, R2.metrics.h_err_max, R2.metrics.V_rms);
fprintf('h_min=%.4f m  ok=%d\n', R2.metrics.h_min, R2.metrics.ok);

fprintf('\n---- 9. 一致性校验：名义对象 + 名义控制器 + 名义配平点（应保持不动） ----\n');
trmn = wig_trim(p.V0, p.h0, p, 'nominal');
scn3 = struct();
scn3.p = p; scn3.pt = p; scn3.Tend = 10.0; scn3.plant = 'nominal';
scn3.ref.h = [0 p.h0]; scn3.ref.V = [0 p.V0];
scn3.x0 = trmn.x;
R3 = wig_simulate(scn3);
fprintf('漂移: dh=%.3e m, dV=%.3e m/s, dtheta=%.3e deg, dq=%.3e rad/s\n', ...
    R3.h(end)-p.h0, R3.V(end)-p.V0, (R3.theta(end)-trmn.x(2)-trmn.x(3))*180/pi, R3.q(end));
fprintf('de 波动 max=%.3e rad,  T 波动 max=%.3e N\n', ...
    max(abs(R3.de-trmn.x(7))), max(abs(R3.T-trmn.x(6))));

fprintf('\n---- 10. 无地效失配时的极简校验：真实=名义 ----\n');
scn4 = scn3; scn4.Tend = 8.0; scn4.plant = 'truth'; scn4.pt = p;
R4 = wig_simulate(scn4);
fprintf('e_h rms=%.4f m, h_min=%.4f m, ok=%d\n', R4.metrics.h_rms, R4.metrics.h_min, R4.metrics.ok);

fprintf('\n---- 11. 高度模态特征向量（真实对象, h=%.3f m） ----\n', p.h0);
trmt = wig_trim(p.V0, p.h0, pt, 'truth');
lin = wig_linearize(trmt, pt, 'truth');
ev = lin.eig;
[~, isp] = min(abs(abs(ev)-2));            % 找一个低频复极点
lp = ev(abs(imag(ev))>0.1 & abs(ev)<=2);
if ~isempty(lp)
    [Vv, Dd] = eig(lin.A);
    lam = lp(1);
    [~, kk] = min(abs(diag(Dd) - lam));
    v = Vv(:,kk);  v = v / max(abs(v));
    fprintf('模态 lambda = %+.4f %+.4fi\n', real(lam), imag(lam));
    nm = {'V','gam','alpha','q','h','T','de'};
    for i = 1:7
        fprintf('   %-6s  幅值=%7.4f  相位=%+8.2f deg\n', nm{i}, abs(v(i)), angle(v(i))*180/pi);
    end
end

fprintf('\n=========== 冒烟测试结束 ===========\n');

end
