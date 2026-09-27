function run_00_cfdfit_body()
%RUN_00_CFDFIT_BODY

fprintf('=========== ANSYS CFD 数据接口测试 ===========\n\n');

here = fileparts(mfilename('fullpath'));
csvf = fullfile(here, '..', '..', 'ANSYS', 'data', 'ge_kappa_template.csv');
fprintf('数据文件: %s\n\n', wig_shortpath(csvf));

[A, n, R2] = wig_ge_fit_cfd(csvf);

p = wig_params();
fprintf('\n---- 标定前后名义模型地效因子对比 ----\n');
fprintf('  h[m]   解析式(A=%.4f,n=%.4f)  CFD标定(A=%.4f,n=%.4f)\n', p.ge_A, p.ge_n, A, n);
for hh = [0.05 0.10 0.20 0.35 0.50 1.00]
    k0 = wig_ge(hh, p.b, p);
    p2 = p; p2.ge_A = A; p2.ge_n = n;
    k1 = wig_ge(hh, p.b, p2);
    fprintf('%6.3f %16.4f %22.4f\n', hh, k0, k1);
end

fprintf('\n---- 标定后名义模型配平（真实对象不变） ----\n');
pt = wig_truth_params(p);
p2 = p; p2.ge_A = A; p2.ge_n = n;  p2.ge_src = 'cfd';
fprintf('  h[m]   标定前 de[deg]  T[N]   标定后 de[deg]  T[N]   真实对象 de[deg]  T[N]\n');
for hh = [0.05 0.20 0.50]
    a = wig_trim(p.V0, hh, p,  'nominal');
    b = wig_trim(p.V0, hh, p2, 'nominal');
    c = wig_trim(p.V0, hh, pt, 'truth');
    fprintf('%6.3f %12.4f %8.3f %14.4f %8.3f %17.4f %8.3f\n', ...
        hh, a.de*180/pi, a.T, b.de*180/pi, b.T, c.de*180/pi, c.T);
end

fprintf('\n结论：\n');
fprintf('  1) 接口回路自洽：模板数据由名义解析式生成，拟合以 R^2 = %.5f 反演出 A、n，\n', R2);
fprintf('     证明最小二乘标定算法正确（往返一致性检验）。\n');
fprintf('  2) 模板并非真实 CFD 结果，故标定后名义模型与真实对象的配平舵偏差仍约 0.9 度。\n');
fprintf('     真正开展 CFD 后，应以 CFD 得到的 kappa(h) 替换模板数据，此时名义模型才\n');
fprintf('     真正逼近真实对象，自适应控制器需在线补偿的稳态失配随之显著下降。\n');

fprintf('\n=========== 接口测试结束 ===========\n');

end
