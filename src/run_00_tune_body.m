function run_00_tune_body()
%RUN_00_TUNE_BODY  增益整定主体
%   场景：真实对象（含地效失配 + RAM + 非线性），初始在 h=0.20 m 配平，
%         高度指令 0.20 -> 0.35 -> 0.10 -> 0.25 m（跨越整个地效区），
%         同时速度指令 18 -> 20 m/s。评估闭环跟踪与安全性。

p  = wig_params();
pt = wig_truth_params(p);

base = struct();
base.p = p; base.pt = pt; base.Tend = 20.0; base.plant = 'truth';
base.ref.h = [0 0.20; 3 0.35; 9 0.10; 15 0.25];
base.ref.V = [0 18; 6 20];

fprintf('=========== 增益整定 ===========\n');
fprintf('场景：真实对象，h: 0.20->0.35->0.10->0.25 m, V: 18->20 m/s\n\n');

fprintf('--- 第一轮：高度外环 k_h / k_hd ---\n');
fprintf(' k_h   k_hd |  h_rms[m]  h_err_max[m]  h_min[m]  V_rms[m/s]  de_max[deg]  settle[s]  ok\n');
best = struct('score', inf, 'k_h', NaN, 'k_hd', NaN);
for kh = [1.5 2.0 3.0 4.0 5.0 7.0]
    for khd = [0.4 0.8 1.2 1.8 2.5]
        pc = p;
        pc.ctrl.k_h  = kh;
        pc.ctrl.k_hd = khd;
        scn = base; scn.pc = pc;
        R = wig_simulate(scn);
        m = R.metrics;
        score = m.h_rms + 10*max(0, 0.02 - m.h_min);
        fprintf('%5.1f %6.1f | %9.4f %12.4f %9.4f %11.4f %11.3f %9.2f %5d\n', ...
            kh, khd, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.de_max*180/pi, m.h_settle, m.ok);
        if score < best.score
            best.score = score; best.k_h = kh; best.k_hd = khd;
        end
    end
end
fprintf('>>> 高环最佳: k_h=%.1f, k_hd=%.1f (score=%.4f)\n\n', best.k_h, best.k_hd, best.score);

fprintf('--- 第二轮：姿态内环 k_th / k_q（固定 k_h=%.1f, k_hd=%.1f） ---\n', best.k_h, best.k_hd);
fprintf(' k_th  k_q  |  h_rms[m]  h_err_max[m]  h_min[m]  V_rms[m/s]  de_max[deg]  q_rms  ok\n');
best2 = struct('score', inf, 'k_th', NaN, 'k_q', NaN);
for kth = [2.0 3.2 4.5 6.0]
    for kq = [4.0 6.0 9.0 12.0]
        pc = p;
        pc.ctrl.k_h = best.k_h; pc.ctrl.k_hd = best.k_hd;
        pc.ctrl.k_th = kth; pc.ctrl.k_q = kq;
        scn = base; scn.pc = pc;
        R = wig_simulate(scn);
        m = R.metrics;
        score = m.h_rms + 10*max(0, 0.02 - m.h_min);
        fprintf('%5.1f %4.1f | %9.4f %12.4f %9.4f %11.4f %11.3f %7.4f %5d\n', ...
            kth, kq, m.h_rms, m.h_err_max, m.h_min, m.V_rms, m.de_max*180/pi, m.q_rms, m.ok);
        if score < best2.score
            best2.score = score; best2.k_th = kth; best2.k_q = kq;
        end
    end
end
fprintf('>>> 内环最佳: k_th=%.1f, k_q=%.1f (score=%.4f)\n\n', best2.k_th, best2.k_q, best2.score);

fprintf('--- 第三轮：速度环 k_V / k_IV ---\n');
fprintf(' k_V  k_IV |  h_rms[m]  V_rms[m/s]  V_err_max  de_max[deg]  ok\n');
best3 = struct('score', inf, 'k_V', NaN, 'k_IV', NaN);
for kV = [0.6 1.2 2.0 3.0]
    for kIV = [0.1 0.35 0.8]
        pc = p;
        pc.ctrl.k_h = best.k_h;  pc.ctrl.k_hd = best.k_hd;
        pc.ctrl.k_th = best2.k_th; pc.ctrl.k_q = best2.k_q;
        pc.ctrl.k_V = kV; pc.ctrl.k_IV = kIV;
        scn = base; scn.pc = pc;
        R = wig_simulate(scn);
        m = R.metrics;
        score = m.h_rms + m.V_rms + 10*max(0, 0.02 - m.h_min);
        fprintf('%5.1f %5.2f | %9.4f %11.4f %10.4f %11.3f %5d\n', ...
            kV, kIV, m.h_rms, m.V_rms, m.V_err_max, m.de_max*180/pi, m.ok);
        if score < best3.score
            best3.score = score; best3.k_V = kV; best3.k_IV = kIV;
        end
    end
end
fprintf('>>> 速度环最佳: k_V=%.1f, k_IV=%.2f (score=%.4f)\n\n', best3.k_V, best3.k_IV, best3.score);

fprintf('--- 第四轮：自适应增益 Gam1 / Gam2（固定上述全部增益） ---\n');
fprintf('  Gam1    Gam2  |  h_rms[m]  h_err_max[m]  V_rms[m/s]  W1n    W2n     ok\n');
best4 = struct('score', inf, 'G1', NaN, 'G2', NaN);
for g1 = [0.005 0.015 0.030 0.060 0.120]
    for g2 = [1.0 3.0 5.0 10.0 20.0]
        pc = p;
        pc.ctrl.k_h = best.k_h;   pc.ctrl.k_hd = best.k_hd;
        pc.ctrl.k_th = best2.k_th; pc.ctrl.k_q = best2.k_q;
        pc.ctrl.k_V = best3.k_V;  pc.ctrl.k_IV = best3.k_IV;
        pc.ctrl.nn.Gam1 = g1; pc.ctrl.nn.Gam2 = g2;
        scn = base; scn.pc = pc;
        R = wig_simulate(scn);
        m = R.metrics;
        score = m.h_rms + m.V_rms + 10*max(0, 0.02 - m.h_min);
        fprintf('%7.3f %7.1f | %9.4f %12.4f %11.4f %7.3f %7.3f %5d\n', ...
            g1, g2, m.h_rms, m.h_err_max, m.V_rms, m.W1n_end, m.W2n_end, m.ok);
        if score < best4.score
            best4.score = score; best4.G1 = g1; best4.G2 = g2;
        end
    end
end
fprintf('>>> 自适应增益最佳: Gam1=%.3f, Gam2=%.1f (score=%.4f)\n\n', best4.G1, best4.G2, best4.score);

fprintf('=========== 推荐参数 ===========\n');
fprintf('p.ctrl.k_h    = %.2f;\n', best.k_h);
fprintf('p.ctrl.k_hd   = %.2f;\n', best.k_hd);
fprintf('p.ctrl.k_th   = %.2f;\n', best2.k_th);
fprintf('p.ctrl.k_q    = %.2f;\n', best2.k_q);
fprintf('p.ctrl.k_V    = %.2f;\n', best3.k_V);
fprintf('p.ctrl.k_IV   = %.2f;\n', best3.k_IV);
fprintf('p.ctrl.nn.Gam1= %.3f;\n', best4.G1);
fprintf('p.ctrl.nn.Gam2= %.1f;\n', best4.G2);

fprintf('\n=========== 整定结束 ===========\n');

end
