function [A, n, R2] = wig_ge_fit_cfd(csvfile)
%WIG_GE_FIT_CFD  由 ANSYS CFD 结果标定地效因子模型参数 (A, n)
%
%   [A, n, R2] = wig_ge_fit_cfd()                       % 默认路径
%   [A, n, R2] = wig_ge_fit_cfd('D:\...\ge_kappa.csv')
%
%   输入 CSV 格式（首行为表头，逗号分隔）：
%       h_m,span_m,kappa
%       0.050,2.40,0.052
%       0.100,2.40,0.131
%       ...
%   其中 kappa = C_Di(h)/C_Di(h->inf) ∈ (0,1] 为地效因子（诱导阻力/下洗保留系数），
%   由 ANSYS Fluent 定常 CFD 计算不同离地高度下的升力、阻力得到：
%       kappa = (C_D - C_D0) / (C_D - C_D0)|_far
%   或由下洗/诱导阻力比直接给出。
%
%   拟合模型： kappa(x) = x^n / (A + x^n),  x = h/span
%   采用对数域线性最小二乘：
%       ln(1/kappa - 1) = ln(A) - n*ln(x)
%   即对 y = ln(1/kappa-1) 与 u = ln(x) 做一元线性回归，斜率 = -n，截距 = ln(A)。
%
%   典型用法（在 run_analysis 之前）：
%       [A,n] = wig_ge_fit_cfd();
%       p = wig_params();  p.ge_A = A;  p.ge_n = n;  p.ge_src = 'cfd';
%   注意：标定后【名义模型】的地效特性随之更新，控制器内部模型与真实对象的
%   失配将显著减小，属于"ANSYS → MATLAB 数据闭环"的标准流程。

if nargin < 1 || isempty(csvfile)
    here = fileparts(mfilename('fullpath'));
    csvfile = fullfile(here, '..', '..', 'ANSYS', 'data', 'ge_kappa.csv');
end

if ~isfile(csvfile)
    error('wig_ge_fit_cfd:noFile', ...
        ['未找到 CFD 数据文件：%s\n' ...
         '请先在 ANSYS 目录下按 README 说明生成 ge_kappa.csv，' ...
         '或显式传入文件路径。'], csvfile);
end

T = readtable(csvfile);
vn = T.Properties.VariableNames;
hcol = pick(vn, {'h_m','h','height'});
scol = pick(vn, {'span_m','span','b'});
kcol = pick(vn, {'kappa','kappa_cfd','cdi_ratio'});

h = T.(hcol);  span = T.(scol);  k = T.(kcol);
h = h(:); span = span(:); k = k(:);

% 剔除无效点并限制在 (0,1)
m = isfinite(h) & isfinite(span) & isfinite(k) & (h > 0) & (span > 0) & (k > 0) & (k < 1);
h = h(m); span = span(m); k = k(m);
if numel(h) < 3
    error('wig_ge_fit_cfd:tooFew', '有效数据点不足（需要至少 3 个）。');
end

x = h ./ span;
y = log(1./k - 1);
u = log(x);

cf = polyfit(u, y, 1);      % y = p(1)*u + p(2)
n  = -cf(1);
A  = exp(cf(2));

yhat = polyval(cf, u);
R2 = 1 - sum((y - yhat).^2) / max(sum((y - mean(y)).^2), eps);

fprintf('CFD 地效因子标定（数据文件: %s）\n', wig_shortpath(csvfile));
fprintf('  有效数据点 %d 个，h/span ∈ [%.4f, %.4f]\n', numel(h), min(x), max(x));
fprintf('  拟合结果: A = %.5f,  n = %.5f,  R^2 = %.5f\n', A, n, R2);
fprintf('  对应 p.ge_A = %.5f; p.ge_n = %.5f;\n', A, n);

end

% =====================================================================
function name = pick(vn, cands)
name = '';
for i = 1:numel(cands)
    idx = find(strcmpi(vn, cands{i}), 1);
    if ~isempty(idx)
        name = vn{idx};
        return;
    end
end
error('wig_ge_fit_cfd:badColumns', ...
    'CSV 缺少必要列，期望其一：%s（实际列：%s）', strjoin(cands, '/'), strjoin(vn, ', '));
end
