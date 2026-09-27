function run_00_opt_body()
%RUN_00_OPT_BODY  以非线性闭环指标为目标做精调（围绕已稳定解）

p  = wig_params();
pt = wig_truth_params(p);

% 稳定的基准（F 组）
base = p;
base.ctrl.k_th=3.2; base.ctrl.k_h=2.0; base.ctrl.k_hd=0.8;
base.ctrl.tau_q=0.010; base.ctrl.tau_th=0.100; base.ctrl.tau_g=0.010;
base.ctrl.k_q=6.0; base.ctrl.k_V=1.53; base.ctrl.k_IV=0.42;
base.ctrl.eta_r=2.5; base.ctrl.Phi_r=0.8;
base.ctrl.eta_V=1.5; base.ctrl.Phi_V=1.0;

scn0 = struct(); scn0.p = p; scn0.pt = pt; scn0.Tend = 40.0; scn0.plant = 'truth';
scn0.ref.h = [0 0.20; 3 0.35; 12 0.10; 21 0.25];
scn0.ref.V = [0 18; 6 20];

fprintf('=========== 非线性精调 ===========\n\n');

% ---- 1. 参考指令滤波带宽 ----
fprintf('---- 1. 参考指令滤波带宽 wn_h ----\n');
for wn = [0.8 1.2 1.6 2.0 3.0]
    pc = base; scn = scn0; scn.pc = pc;
    scn.ref.wn_h = wn; scn.ref.wn_V = wn;
    R = wig_simulate(scn); m = R.metrics;
    fprintf('wn=%.1f  h_rms=%.4f h_err_max=%.4f h_min=%.4f V_rms=%.4f de_max=%5.1fdeg ok=%d\n', ...
        wn, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.de_max*180/pi, m.ok);
end

% ---- 2. 鲁棒项参数 ----
fprintf('\n---- 2. 鲁棒项 eta_r / Phi_r（eta_V=1.5, Phi_V=1.0, wn=1.2） ----\n');
fprintf(' eta_r  Phi_r  等效增益 |  h_rms   h_err_max  h_min   V_rms   de_max   ok\n');
for er = [1.5 2.5 4.0 6.0]
    for pr = [0.4 0.8 1.5 2.5]
        pc = base; pc.ctrl.eta_r=er; pc.ctrl.Phi_r=pr;
        scn = scn0; scn.pc = pc; scn.ref.wn_h=1.2; scn.ref.wn_V=1.2;
        R = wig_simulate(scn); m = R.metrics;
        fprintf('%6.1f %6.2f %9.1f | %7.4f %9.4f %8.4f %8.4f %8.1f %5d\n', ...
            er, pr, er/pr, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.de_max*180/pi, m.ok);
    end
end

% ---- 3. 高度外环 ----
fprintf('\n---- 3. 高度外环 k_h / k_hd（eta_r=2.5, Phi_r=0.8, wn=1.2） ----\n');
fprintf(' k_h   k_hd |  h_rms   h_err_max  h_min   V_rms   de_max   settle  ok\n');
for kh = [1.0 1.5 2.0 3.0 4.5]
    for khd = [0.4 0.8 1.2 2.0]
        pc = base; pc.ctrl.k_h=kh; pc.ctrl.k_hd=khd;
        scn = scn0; scn.pc = pc; scn.ref.wn_h=1.2; scn.ref.wn_V=1.2;
        R = wig_simulate(scn); m = R.metrics;
        fprintf('%5.1f %6.1f | %7.4f %9.4f %8.4f %8.4f %8.1f %7.2f %5d\n', ...
            kh, khd, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.de_max*180/pi, m.h_settle, m.ok);
    end
end

% ---- 4. 自适应增益 ----
fprintf('\n---- 4. 自适应增益 Gam1 / Gam2 ----\n');
fprintf('  Gam1    Gam2 |  h_rms   h_err_max  h_min   V_rms   W1n    W2n     ok\n');
for g1 = [0.005 0.015 0.030 0.060]
    for g2 = [1.0 3.0 8.0 20.0]
        pc = base; pc.ctrl.nn.Gam1=g1; pc.ctrl.nn.Gam2=g2;
        scn = scn0; scn.pc = pc; scn.ref.wn_h=1.2; scn.ref.wn_V=1.2;
        R = wig_simulate(scn); m = R.metrics;
        fprintf('%6.3f %7.1f | %7.4f %9.4f %8.4f %8.4f %6.3f %6.3f %5d\n', ...
            g1, g2, m.h_rms, m.h_err_max, m.h_min, m.V_rms, ...
            R.DBG.W1norm(end), R.DBG.W2norm(end), m.ok);
    end
end

fprintf('\n=========== 精调结束 ===========\n');

end
