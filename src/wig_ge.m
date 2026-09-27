function [kap, dkap] = wig_ge(h, span, p)
%WIG_GE  地面效应（地效）因子 kappa(h) 及其对高度的导数
%
%   [kap, dkap] = wig_ge(h, span, p)
%
%   输入：
%       h     离地高度 [m]（标量，可 > 0；h<0 按 0 处理）
%       span  参考翼展 [m]（机翼取 p.b，平尾取 p.bt）
%       p     参数结构体（需含 p.ge_A, p.ge_n）
%   输出：
%       kap   地效因子 ∈ (0,1]
%                  kap -> 1 : 远离地面（自由空气，下洗完整保留）
%                  kap -> 0 : 贴地（地面镜像涡系抵消下洗）
%       dkap  d(kap)/dh [1/m]
%
%   模型：  kappa(x) = x^n / (A + x^n),   x = h/span
%   物理含义：kappa 是"诱导下洗保留系数"。机翼在距地面 h 处的镜像涡系使
%   下洗角与诱导阻力按 kappa 衰减，因而
%       诱导阻力   CDi(h)  = CL^2 * kappa / (pi*AR*e)
%       有效升力线斜率 a(h) = a0 / (1 + a0*kappa/(pi*AR*e))
%   当 kappa=1 时退化为自由空气的经典有限翼理论结果。
%
%   参数 A、n 由公开 WIG 风洞/CFD 数据拟合（见理论分析报告 2.3 节），
%   亦可由 ANSYS CFD 结果经 wig_ge_fit_cfd.m 标定后覆盖。

A = p.ge_A;
n = p.ge_n;

if span <= 0
    error('wig_ge:badSpan', 'span 必须为正数。');
end

x  = max(h, 0) / span;
if x <= 0
    kap  = 0;
    dkap = 0;
    return;
end

xn   = x^n;
den  = A + xn;
kap  = xn / den;
% d(kap)/dh = n*A*x^(n-1) / (span*(A+x^n)^2)
dkap = n * A * x^(n-1) / (span * den^2);

end
