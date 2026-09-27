function run_00_clp_body()
%RUN_00_CLP_BODY  闭环极点谱完整排查

p  = wig_params();
pt = wig_truth_params(p);

% ---- 基准控制器：直接使用 wig_params() 的出厂增益，不做任何覆盖 ----
pc = p;

% ---- 调试中间态增益（历史，k_h=3.0, k_hd=0.8, tau_g=0.05） ----
% 早期闭环发散排查时使用的中间态，保留下来是为了与历史 log_clp.txt 对比；
% 与 wig_params.m 的出厂值对照：
%   k_h 3.0 -> 2.00 | k_hd 0.8 -> 0.80（相同） | tau_g 0.05 -> 0.010
%   k_th 3.2 -> 3.20（相同） | k_q 6.0 -> 6.00（相同）
pc_hist = p;
pc_hist.ctrl.k_h = 3.0; pc_hist.ctrl.k_hd = 0.8; pc_hist.ctrl.tau_g = 0.05;
pc_hist.ctrl.k_th = 3.2; pc_hist.ctrl.k_q = 6.0;

trm  = wig_trim(p.V0, p.h0, pt, 'truth');
ref  = [p.h0; 0; p.V0; 0];

fprintf('=========== 闭环极点谱排查 ===========\n\n');
% 基准：出厂增益 + 长暖启动（Twarm=60 s，暖启动不足会让平衡点求解跳到
% 另一个定点分支）与精确平衡点求解
[Acl, ev, names, info] = wig_closedloop_eig(trm, p, pc, pt, 'truth', ref, ...
                                            struct('Twarm', 60, 'verbose', true));
fprintf('---- 基准：全部 15 个闭环极点（wig_params 出厂增益） ----\n');
% 机器可读块：供后续论文指标解析脚本提取。标题行与下列 max|z| / h_eq /
% res_eq 三行必须保持逐字不变（解析器锚定标题后向后检索这三个标记）；
% 因此紧随其后的历史增益块改用 |z|max= / h_eq= / 残差 等不同写法，不产生同名标记。
fprintf('最终整定参数（shipped wig_params）\n');
fprintf('  k_h=%.2f k_hd=%.2f tau_g=%.3f k_th=%.2f k_q=%.2f k_V=%.2f k_IV=%.2f\n', ...
    pc.ctrl.k_h, pc.ctrl.k_hd, pc.ctrl.tau_g, pc.ctrl.k_th, pc.ctrl.k_q, ...
    pc.ctrl.k_V, pc.ctrl.k_IV);
fprintf('  max|z| = %.5f\n', info.maxabsz);
fprintf('  h_eq = %.5f m（指令 %.5f m）\n', info.h_eq, ref(1));
fprintf('  res_eq = %.3e\n', info.res_eq);
fprintf('  平衡点初值残差 res_eq0 = %.3e，iters=%g，分支跳变 jumped=%d，暖启动 Twarm=%.0f s\n', ...
    info.res_eq0, info.iters, info.jumped, info.Twarm);
fprintf('  冻结权值范数：||W1||=%.4f  ||W2||=%.4f\n', norm(info.W1), norm(info.W2));
if info.maxabsz < 1
    fprintf('  稳定性判定：max|z| < 1 => 稳定\n');
else
    fprintf('  稳定性判定：max|z| >= 1 => 失稳\n');
end
fprintf('  #   |z|          s = log(z)/Ts           主导状态\n');
[~, ord] = sort(abs(ev), 'descend');
for k = 1:numel(ev)
    z = ev(ord(k));
    l = log(z)/pc.sim.Ts;
    fprintf('  %2d  |z|=%.5f  s=%+8.3f%+8.3fi   %s\n', ...
        k, abs(z), real(l), imag(l), info.dom{ord(k)});
end

% 历史中间态基线：保留旧覆盖值，使历史对比不丢失
fprintf('\n---- 调试中间态增益（历史，k_h=3.0, k_hd=0.8, tau_g=0.05） ----\n');
fprintf('  与出厂值对照：k_h 3.0 -> 2.00、tau_g 0.05 -> 0.010（k_hd/k_th/k_q 相同）\n');
[~, evh, ~, infoh] = wig_closedloop_eig(trm, p, pc_hist, pt, 'truth', ref, ...
                                        struct('Twarm', 60));
fprintf('  历史增益：h_eq=%.5f m，最大极点模 |z|max=%.6f（>1 即历史失稳工况）\n', ...
    infoh.h_eq, infoh.maxabsz);
fprintf('  平衡点残差 %.3e -> %.3e（iters=%g，jumped=%d）\n', ...
    infoh.res_eq0, infoh.res_eq, infoh.iters, infoh.jumped);
if infoh.maxabsz < 1
    fprintf('  历史增益 |z|max < 1 => 稳定\n');
else
    fprintf('  历史增益 |z|max > 1 => 失稳（正是改用出厂增益的原因）\n');
end
fprintf('  #   |z|          s = log(z)/Ts           主导状态\n');
[~, ordh] = sort(abs(evh), 'descend');
for k = 1:numel(evh)
    z = evh(ordh(k));
    l = log(z)/pc_hist.sim.Ts;
    fprintf('  %2d  |z|=%.5f  s=%+8.3f%+8.3fi   %s\n', ...
        k, abs(z), real(l), imag(l), infoh.dom{ordh(k)});
end

fprintf('\n---- 结构敏感性测试（max|z|，>1 失稳；历史中间态基准） ----\n');
tests = {};
t = pc_hist;                                          tests{end+1} = {'基准', t, pt};
t2 = t; t2.z_T = 0;                                   tests{end+1} = {'推力线过质心 z_T=0 (对象)', t2, t2};
t3 = t; t3.ctrl.enable_rob = false;                   tests{end+1} = {'关闭鲁棒项', t3, pt};
t4 = t; t4.ctrl.tau_T = 0.02;                         tests{end+1} = {'发动机 tau_T=0.02 (两侧)', t4, t4};
t5 = t; t5.ctrl.k_V = 0; t5.ctrl.k_IV = 0;            tests{end+1} = {'关闭速度环比例与积分', t5, pt};
t7 = t; t7.ctrl.tau_g = 0.02;                         tests{end+1} = {'tau_g=0.02', t7, pt};
t8 = t; t8.ctrl.tau_th = 0.02; t8.ctrl.tau_q = 0.015; tests{end+1} = {'tau_th=0.02, tau_q=0.015', t8, pt};
t9 = t; t9.ctrl.k_h=2.0; t9.ctrl.k_hd=0.5;            tests{end+1} = {'k_h=2, k_hd=0.5', t9, pt};

for i = 1:numel(tests)
    pci = tests{i}{2};
    pti = tests{i}{3};
    trmi = wig_trim(p.V0, p.h0, pti, 'truth');
    % 各测试的对象/控制器均与基准不同，故各自做 Twarm=60 s 暖启动（不复用基准暖启动点）
    [~, evi, ~, infoi] = wig_closedloop_eig(trmi, p, pci, pti, 'truth', ref, ...
                                            struct('Twarm', 60));
    [~, id] = max(abs(evi));
    l = log(evi(id))/pci.sim.Ts;
    fprintf('%-34s max|z| = %.5f  主导 s = %+.3f%+.3fi (%s)\n', ...
        tests{i}{1}, infoi.maxabsz, real(l), imag(l), infoi.dom{id});
end

fprintf('\n---- 主导极点完整特征向量（出厂增益基准，直接复用基准 Acl） ----\n');
[Vv, Dd] = eig(Acl);
dv = diag(Dd);
[~, id] = min(abs(dv - ev(ord(1))));
v = Vv(:, id);  v = v/max(abs(v));
fprintf('  主导极点 |z|=%.6f，主导状态 = %s\n', abs(ev(ord(1))), info.dom{ord(1)});
for i = 1:numel(names)
    fprintf('   %-7s 幅值=%9.5f 相位=%+8.2f\n', names{i}, abs(v(i)), angle(v(i))*180/pi);
end

fprintf('\n---- 高增益整定：寻找 max|z|<1 的组合 ----\n');
% 网格只扫描 k_h/k_hd/k_q/tau_g/tau_th，k_th 与 tau_q 固定取 pc.ctrl.*，
% 故在表头注明固定取值，表体逐行打印实际使用值（旧版本硬编码 3.2 / 0.04，
% 其中 tau_q 与真实取值不符）。
% 暖启动点复用基准的 info.warm（Twarm=60 s 收敛轨迹终端）：既快，又保证
% 每个网格点都落在与基准相同的定点分支上。
fprintf('  暖启动复用基准点 info.warm，逐点仿真已跳过。\n');
fprintf('  k_h  k_hd  k_th  k_q  tau_g  tau_th  tau_q   max|z|   (k_th=%.2f, tau_q=%.3f 固定)\n', ...
    pc.ctrl.k_th, pc.ctrl.tau_q);
best = inf; bp = pc;
opts_g = struct('warm', info.warm);
for kh = [1.0 2.0 3.0]
  for khd = [0.3 0.6 1.0]
    for kq = [4.0 8.0 14.0]
      for tg = [0.05 0.02]
        for tth = [0.06 0.03]
          pci = pc; pci.ctrl.k_h=kh; pci.ctrl.k_hd=khd; pci.ctrl.k_q=kq;
          pci.ctrl.tau_g=tg; pci.ctrl.tau_th=tth;
          [~, ~, ~, infoi] = wig_closedloop_eig(trm, p, pci, pt, 'truth', ref, opts_g);
          m = infoi.maxabsz;
          if m < 1
              fprintf('%5.1f %5.1f %5.1f %5.1f %6.2f %6.2f %6.3f   %.5f  <= 稳定\n', ...
                  kh, khd, pci.ctrl.k_th, kq, tg, tth, pci.ctrl.tau_q, m);
              if m < best, best = m; bp = pci; end
          end
        end
      end
    end
  end
end
if isfinite(best)
    fprintf('最佳: max|z| = %.5f  (k_h=%.1f, k_hd=%.1f, k_q=%.1f, tau_g=%.2f, tau_th=%.2f)\n', ...
        best, bp.ctrl.k_h, bp.ctrl.k_hd, bp.ctrl.k_q, bp.ctrl.tau_g, bp.ctrl.tau_th);
else
    fprintf('未找到 max|z|<1 的组合\n');
end

fprintf('\n=========== 排查结束 ===========\n');

end
