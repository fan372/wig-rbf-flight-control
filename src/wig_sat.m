function y = wig_sat(u, lo, hi)
%WIG_SAT  对称/非对称饱和函数
%
%   y = wig_sat(u, lim)        % 对称限幅, y ∈ [-lim, lim]
%   y = wig_sat(u, lo, hi)     % 非对称限幅, y ∈ [lo, hi]
%
%   与 Simulink 的 Saturation 模块语义一致，便于代码生成（无 toolbox 依赖）。

if nargin < 3
    hi = lo;
    lo = -hi;
end
y = min(max(u, lo), hi);

end
