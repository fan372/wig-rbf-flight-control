function lin = wig_linearize(trm, p, flag)
%WIG_LINEARIZE  在配平点对 7 阶纵向非线性模型做数值线性化并分析模态
%
%   lin = wig_linearize(trm, p, flag)
%
%   输出结构体 lin：
%       .A .B     连续时间状态空间矩阵（7x7, 7x2）
%       .C .D     输出矩阵（y = [V; gam; alpha; q; h; T; de]，C=I, D=0）
%       .x0 .u0   线性化工作点
%       .eig      特征值
%       .mode     模态识别结果（结构体数组：名称、频率、阻尼、时间常数）
%       .inputs   状态名与输入名（元胞）
%
%   数值微分采用中心差分；被控对象含执行器一阶动态，因此除纵向刚体模态外
%   还存在两个执行器极点，模态识别时会单独标注。

if nargin < 3 || isempty(flag)
    flag = 'nominal';
end

x0 = trm.x;      % 7x1
u0 = trm.u;      % 2x1
nx = numel(x0);
nu = numel(u0);

f0 = wig_dynamics(x0, u0, p, flag);

A = zeros(nx, nx);
for i = 1:nx
    dx = 1e-6 * max(1, abs(x0(i)));
    xp = x0; xp(i) = xp(i) + dx;
    xm = x0; xm(i) = xm(i) - dx;
    A(:, i) = (wig_dynamics(xp, u0, p, flag) - wig_dynamics(xm, u0, p, flag)) / (2*dx);
end

B = zeros(nx, nu);
for j = 1:nu
    du = 1e-6 * max(1, abs(u0(j)));
    up = u0; up(j) = up(j) + du;
    um = u0; um(j) = um(j) - du;
    B(:, j) = (wig_dynamics(x0, up, p, flag) - wig_dynamics(x0, um, p, flag)) / (2*du);
end

ev = eig(A);

lin.A  = A;
lin.B  = B;
lin.C  = eye(nx);
lin.D  = zeros(nx, nu);
lin.x0 = x0;
lin.u0 = u0;
lin.f0 = f0;
lin.eig = ev;
lin.inputs = {'升降舵 de_cmd [rad]', '油门 dt_cmd [0-1]'};
lin.states = {'V [m/s]', 'gam [rad]', 'alpha [rad]', 'q [rad/s]', ...
              'h [m]', 'T [N]', 'de [rad]'};
lin.mode = classify_modes(ev);

end

% =====================================================================
function modes = classify_modes(ev)
%CLASSIFY_MODES  按极点位置识别纵向模态（短周期/长周期/高度/执行器）
%   判别依据：固有频率与阻尼比。高度模态为小实根（积分器型），
%   执行器为两个快实极点。
wn = abs(ev);
zeta = -real(ev) ./ max(wn, eps);

modes = struct('name', {}, 'lambda', {}, 'wn', {}, 'zeta', {}, 'T', {});
for k = 1:numel(ev)
    lam = ev(k);
    if wn(k) < 1e-6
        nm = '刚性积分模态';
    elseif wn(k) > 15
        nm = '执行器模态';
    elseif wn(k) < 1.2
        nm = '长周期(浮沉)模态';
    else
        nm = '短周期模态';
    end
    if abs(imag(lam)) < 1e-8
        Tc = abs(1/real(lam));
    else
        Tc = 1/max(-real(lam), eps) ;
    end
    modes(k).name   = nm;
    modes(k).lambda = lam;
    modes(k).wn     = wn(k);
    modes(k).zeta   = zeta(k);
    modes(k).T      = Tc;
end
end
