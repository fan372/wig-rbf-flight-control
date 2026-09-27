function [W, Wd] = wig_proj(W, tau, Wmax, Ts)
%WIG_PROJ  权值投影算子（Ioannou & Sun 型）与前向欧拉更新
%
%   [W, Wd] = wig_proj(W, tau, Wmax, Ts)
%
%   投影算子：
%       若 ||W|| < Wmax，或 ||W|| = Wmax 且 W'*tau <= 0，则   Wd = tau
%       否则                                                Wd = tau - (W*W'*tau)/||W||^2
%   性质：若 ||W(0)|| <= Wmax，则对任意 t >= 0 有 ||W(t)|| <= Wmax。
%   该性质是 Lyapunov 分析中"权值一致有界"的直接依据（见报告 4.4 节）。
%
%   随后按 W <- W + Ts*Wd 做一次前向欧拉积分；为避免浮点误差导致的
%   极小越界，仅在越界超过 0.1% 时做一次径向收缩（实际几乎不触发）。

Wd = wig_proj_op(W, tau, Wmax);
W  = W + Ts * Wd;

n = norm(W);
if n > Wmax * 1.001
    W = W * (Wmax / n);
end

end

% =====================================================================
function Wd = wig_proj_op(W, tau, Wmax)
n2 = W' * W;
if n2 < Wmax^2 || (W' * tau <= 0)
    Wd = tau;
else
    Wd = tau - (W * (W' * tau)) / n2;
end
end
