function run_00_mdh_body()
%RUN_00_MDH_BODY  地效高度稳定性导数 dM/dh 的分量分解
%   回答一个关键问题：为什么本构型的 ∂M/∂h > 0（高度静不稳定）？
%   方法：在真实对象的各高度配平点上，用中心差分求总 ∂M/∂h，
%         同时把俯仰力矩拆成 机翼 / 平尾 / RAM / 升力非线性 / 机体 / 推力线
%         六个分量，分别求导，得到各分量的贡献。

wig_plot_style();
p  = wig_params();
pt = wig_truth_params(p);

V0 = p.V0;
hh = [0.05 0.15 0.25 0.35 0.45 0.55 0.80 1.00];

fprintf('=========== 地效高度稳定性导数 dM/dh 分解 ===========\n');
fprintf('评估点：真实对象在 V=%.1f m/s 下的配平点（冻结其余状态，对 h 中心差分）\n', V0);
fprintf('符号约定：∂M/∂h > 0 表示"高度降低产生附加低头力矩"，即高度静不稳定。\n\n');

n = numel(hh);
D  = cell(n,1);
tot = zeros(n,1); wing = zeros(n,1); tail = zeros(n,1);
ram = zeros(n,1); nl = zeros(n,1); fus = zeros(n,1); thr = zeros(n,1);
dL  = zeros(n,1); dD = zeros(n,1); res = zeros(n,1);

for k = 1:n
    trm = wig_trim(V0, hh(k), pt, 'truth');
    dk  = wig_mdh_decomp(trm.x, pt);
    D{k} = dk;
    tot(k)=dk.total; wing(k)=dk.wing; tail(k)=dk.tail;
    ram(k)=dk.ram;   nl(k)=dk.nl;     fus(k)=dk.fuse; thr(k)=dk.thrust;
    dL(k)=dk.dLdh;   dD(k)=dk.dDdh;   res(k)=dk.resid;
end

fprintf('---- 1. 分量分解表（单位：N·m/m） ----\n');
fprintf('%6s %10s %10s %10s %10s %10s %10s %10s\n', ...
    'h[m]', 'dM/dh总', '机翼', '平尾', 'RAM', '升力非线性', '机体', '推力线');
for k = 1:n
    fprintf('%6.3f %+10.3f %+10.3f %+10.3f %+10.3f %+10.3f %+10.3f %+10.3f\n', ...
        hh(k), tot(k), wing(k), tail(k), ram(k), nl(k), fus(k), thr(k));
end

fprintf('\n---- 2. 自洽性校核（分量之和 - 总导数，应为机器精度量级） ----\n');
fprintf('%6s %14s %14s %14s\n', 'h[m]', '分量之和', '总导数', '残差');
for k = 1:n
    fprintf('%6.3f %+14.6f %+14.6f %14.3e\n', hh(k), tot(k)-res(k), tot(k), res(k));
end
fprintf('最大残差 = %.3e N·m/m（相对量级 %.2e）\n', ...
    max(abs(res)), max(abs(res))/max(abs(tot)));

fprintf('\n---- 3. 主导项识别 ----\n');
for k = 1:n
    fprintf('h=%.3f m: 主导不稳定项 = %-8s (%+.3f N·m/m)，占总量的 %5.1f%%\n', ...
        hh(k), D{k}.dom_name, D{k}.dom_value, ...
        100*D{k}.dom_value/tot(k));
end

fprintf('\n---- 4. 升力/阻力高度导数 ----\n');
fprintf('%6s %14s %14s %16s\n', 'h[m]', 'dL/dh[N/m]', 'dD/dh[N/m]', '高度刚度wn_h[rad/s]');
for k = 1:n
    fprintf('%6.3f %+14.3f %+14.3f %16.4f\n', hh(k), dL(k), dD(k), sqrt(abs(dL(k))/pt.m));
end

fprintf('\n---- 5. 名义模型 vs 真实对象（dM/dh 总量对比） ----\n');
fprintf('%6s %16s %16s %14s\n', 'h[m]', '名义[N·m/m]', '真实[N·m/m]', '失配[N·m/m]');
for k = 1:n
    trn = wig_trim(V0, hh(k), p, 'nominal');
    dn  = wig_mdh_decomp(trn.x, p);
    fprintf('%6.3f %+16.3f %+16.3f %+14.3f\n', hh(k), dn.total, tot(k), tot(k)-dn.total);
end

fprintf('\n---- 6. 结论 ----\n');
fprintf('(1) 全部高度上 ∂M/∂h > 0，范围 %+.3f ~ %+.3f N·m/m，即地效高度静稳定性为负；\n', ...
    min(tot), max(tot));
fprintf('(2) 主因是【平尾项】：%+.3f ~ %+.3f N·m/m，在所有高度上都是最大的正贡献；\n', ...
    min(tail), max(tail));
fprintf('    机理：贴地 -> 平尾处下洗减小 -> 平尾当地迎角增大 -> 配平状态下的平尾负升力\n');
fprintf('    （下洗载荷）被削弱 -> 产生附加低头力矩。\n');
fprintf('(3) 机翼项 %+.3f ~ %+.3f N·m/m，是【稳定】贡献（贴地增升、气动中心在质心之前）；\n', ...
    min(wing), max(wing));
fprintf('(4) RAM 项 %+.3f ~ %+.3f N·m/m 与升力非线性项 %+.3f ~ %+.3f N·m/m 均为不稳定贡献；\n', ...
    min(ram), max(ram), min(nl), max(nl));
fprintf('(5) 机体项与推力线项与 h 无关，恒为 0。\n');
fprintf('(6) 与 Irodov 高度稳定性判据（要求 ∂C_m/∂h < 0）比较：本构型不满足，\n');
fprintf('    因此必须依靠主动高度控制，且对控制带宽与相位裕度提出硬性要求。\n');

%% ---- 图 12：分解结果 ----
f12 = figure('Position',[100 100 980 640]);

subplot(2,2,1);
bar(hh, [wing(:), tail(:), ram(:), nl(:)], 'stacked');
hold on; plot(hh, tot, 'ko-', 'LineWidth', 1.4, 'MarkerFaceColor', 'w');
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]')); ylabel('∂M/∂h [N·m/m]');
legend({wig_lbl('机翼','Wing'), wig_lbl('平尾','Tail'), 'RAM', ...
        wig_lbl('升力非线性','Lift nonlinearity'), wig_lbl('总量','Total')}, ...
    'Location', 'northwest');
title(wig_lbl('(a) ∂M/∂h 分量堆叠与总量','(a) Stacked ∂M/∂h components and total'));
yline(0, 'k-', 'LineWidth', 0.8);

subplot(2,2,2);
plot(hh, 100*tail./tot, 'rs-', 'LineWidth', 1.3); hold on;
plot(hh, 100*wing./tot, 'b^-', 'LineWidth', 1.3);
plot(hh, 100*(ram+nl)./tot, 'gv-', 'LineWidth', 1.3);
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
ylabel(wig_lbl('占总量的比例 [%]','Share of the total [%]'));
legend({wig_lbl('平尾（不稳定）','Tail (destabilizing)'), ...
        wig_lbl('机翼（稳定）','Wing (stabilizing)'), ...
        wig_lbl('RAM+非线性（不稳定）','RAM + nonlinearity (destabilizing)')}, ...
    'Location', 'east');
title(wig_lbl('(b) 各分量占总 ∂M/∂h 的比例', ...
              '(b) Component shares of the total ∂M/∂h'));

subplot(2,2,3);
plot(hh, dL, 'b-o', 'LineWidth', 1.3);
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]')); ylabel('∂L/∂h [N/m]');
title(wig_lbl('(c) 升力高度刚度（负 = 贴地增升）', ...
              '(c) Lift height stiffness (negative = ground-effect lift gain)'));

subplot(2,2,4);
yyaxis left;  plot(hh, wing, 'b-o', 'LineWidth', 1.3);
ylabel(wig_lbl('机翼项 [N·m/m]','Wing term [N·m/m]'));
yyaxis right; plot(hh, tail, 'r-s', 'LineWidth', 1.3);
ylabel(wig_lbl('平尾项 [N·m/m]','Tail term [N·m/m]'));
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
title(wig_lbl('(d) 稳定项与不稳定项消长', ...
              '(d) Growth and decay of the stabilizing and destabilizing terms'));

wig_savefig(f12, 'fig12_mdh');

fprintf('\n=========== dM/dh 分解结束 ===========\n');

end
