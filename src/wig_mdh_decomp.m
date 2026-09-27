function D = wig_mdh_decomp(x, p, dh)
%WIG_MDH_DECOMP  俯仰力矩对离地高度导数 dM/dh 的分量分解
%
%   D = wig_mdh_decomp(x, p)
%   D = wig_mdh_decomp(x, p, dh)
%
%   输入：
%       x    状态向量 [V; gam; alpha; q; h; T; de]（通常取配平点）
%       p    参数结构体（真实对象请传 wig_truth_params 的结果）
%       dh   中心差分步长 [m]（缺省 1e-4）
%   输出（结构体）：
%       D.total    总俯仰力矩导数 dM/dh            [N·m/m]
%       D.wing     机翼贡献（含 Cmac 常数项）
%       D.tail     平尾贡献
%       D.ram      RAM 附加力贡献（仅真实对象非零）
%       D.nl       升力非线性软化残差贡献（仅真实对象非零）
%       D.fuse     机体贡献（本模型与 h 无关，恒为 0）
%       D.thrust   推力线偏置贡献（本模型与 h 无关，恒为 0）
%       D.sum_parts 各分量之和（应与 D.total 一致，用于自洽性校核）
%       D.resid    D.sum_parts - D.total（数值残差，量级 ~1e-9）
%       D.dLdh     总升力对高度的导数 dL/dh        [N/m]
%       D.dDdh     总阻力对高度的导数 dD/dh        [N/m]
%       D.h        评估点离地高度 [m]
%       D.alpha    评估点迎角 [rad]
%       D.truth    是否为真实对象
%       D.parts    名称元胞数组，与 D.vals 一一对应
%       D.vals     各分量数值向量 [N·m/m]
%
%   方法：对离地高度 h 做中心差分
%       dM/dh ≈ [ M(x; h+dh) - M(x; h-dh) ] / (2*dh)
%   其余状态量保持在 x 给定值不变（即"冻结状态"意义下的偏导数，
%   这正是 Irodov 高度稳定性判据中 ∂C_m/∂h 的定义）。
%
%   物理意义：本构型在整个使用包线内 D.total > 0，即地效高度静稳定性为负。
%   分解后可看出主因是平尾项 D.tail —— 贴地使平尾处下洗减小、平尾当地迎角
%   增大，而配平状态下平尾承担负升力（下洗载荷），当地迎角增大会削弱这一
%   负升力，从而产生附加低头力矩。详见理论分析报告第 3 章。
%
%   用法：
%       p  = wig_params();  pt = wig_truth_params(p);
%       trm = wig_trim(p.V0, 0.20, pt, 'truth');
%       D = wig_mdh_decomp(trm.x, pt);
%       fprintf('dM/dh = %+.3f N·m/m (wing %+.3f, tail %+.3f, ram %+.3f)\n', ...
%           D.total, D.wing, D.tail, D.ram);

if nargin < 3 || isempty(dh)
    dh = 1e-4;
end

x  = x(:);
h0 = x(5);
if h0 - dh < 0
    dh = 0.5 * h0;                       % 避免扰动到 h < 0
end

xp = x;  xp(5) = h0 + dh;
xm = x;  xm(5) = h0 - dh;

flag = 'nominal';
if isfield(p, 'is_truth') && p.is_truth
    flag = 'truth';
end

[Fp, ap] = wig_aero(xp, p, flag);
[Fm, am] = wig_aero(xm, p, flag);

d = @(fp, fm) (fp - fm) / (2*dh);

D.h        = h0;
D.alpha    = x(3);
D.truth    = ap.truth;
D.total    = d(Fp(3), Fm(3));
D.wing     = d(ap.M_w,   am.M_w);
D.tail     = d(ap.M_t,   am.M_t);
D.ram      = d(ap.M_ram, am.M_ram);
D.nl       = d(ap.M_nl,  am.M_nl);
D.fuse     = d(ap.M_fus, am.M_fus);
D.thrust   = d(ap.M_T,   am.M_T);
D.dLdh     = d(Fp(1), Fm(1));
D.dDdh     = d(Fp(2), Fm(2));

D.parts    = {'wing','tail','ram','nl','fuse','thrust'};
D.vals     = [D.wing, D.tail, D.ram, D.nl, D.fuse, D.thrust];
D.sum_parts = sum(D.vals);
D.resid    = D.sum_parts - D.total;

% 主导不稳定项 = 正贡献中最大者（供报告/论文直接引用）
[mx, imx]    = max(D.vals);
D.dom_name   = D.parts{imx};
D.dom_value  = mx;

end
