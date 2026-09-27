function trm = wig_trim(V, h, p, flag, x0)
%WIG_TRIM  地效飞行器纵向定常直线飞行配平
%
%   trm = wig_trim(V, h, p, flag, x0)
%
%   输入：
%       V     指定空速 [m/s]
%       h     指定离地高度 [m]
%       p     参数结构体
%       flag  'nominal'（默认）或 'truth'
%       x0    初值（可选），缺省用经验初值
%   输出结构体 trm：
%       .x     配平状态 x = [V; gam; alpha; q; h; T; de]（gam=0, q=0）
%       .u     配平控制 u = [de; dt]
%       .alpha 配平迎角 [rad]
%       .de    配平升降舵 [rad]
%       .dt    配平油门 [0,1]
%       .T     配平推力 [N]
%       .CL .CD .L_D   配平升阻特性
%       .res   残差（无量纲化的三个方程残差）
%       .ok    是否收敛
%
%   配平方程（定常平飞：gam=0, q=0, dV=0, dgam=0, dq=0）：
%       f1 = T*cos(alpha+i_T) - D - m*g*sin(gam)  = 0
%       f2 = L + T*sin(alpha+i_T) - m*g*cos(gam)  = 0
%       f3 = M                                     = 0
%   未知量：alpha, de, T（油门由 T 反解）。
%
%   求解策略：先用阻尼牛顿法（数值雅可比）迭代，失败则回退到带边界的
%   信赖域搜索，保证不依赖 Optimization Toolbox。

if nargin < 4 || isempty(flag)
    flag = 'nominal';
end
if nargin < 5 || isempty(x0)
    % 经验初值：alpha ≈ W/(qbar*S*a_w) 量级
    qbar = 0.5*p.rho*V^2;
    aw   = p.a0/(1 + p.a0*wig_ge(h,p.b,p)/(pi*p.AR*p.e));
    a0g  = p.m*p.g/(qbar*p.S*aw) + p.aL0;
    x0   = [a0g - 0.010;  -0.05;  p.m*p.g*0.05];
end

z = x0(:);

opts = optimset('Display','off','TolFun',1e-12,'TolX',1e-12, ...
                'MaxIter',200,'MaxFunEvals',5000,'Algorithm','trust-region-dogleg');

% ---------- 主求解：fsolve（若可用） ----------
ok = false;
zsol = z;
try
    [zsol, ~, exitflag] = fsolve(@(zz) trim_residual(zz, V, h, p, flag), z, opts);
    ok = (exitflag > 0);
catch
    ok = false;
end

% ---------- 回退：自研阻尼牛顿法 ----------
if ~ok
    [zsol, ok] = newton_trim(z, V, h, p, flag);
end

alpha = zsol(1);
de    = zsol(2);
T     = zsol(3);

x = [V; 0; alpha; 0; h; T; de];

% ---------- 后处理 ----------
F   = wig_aero(x, p, flag);
qbar = 0.5*p.rho*V^2;
CL  = F(1)/(qbar*p.S);
CD  = F(2)/(qbar*p.S);

trm.x     = x;
trm.u     = [de; T/(p.Tmax - p.Tmin)];
trm.alpha = alpha;
trm.de    = de;
trm.T     = T;
trm.dt    = min(max(T/(p.Tmax - p.Tmin), 0), 1);
trm.CL    = CL;
trm.CD    = CD;
trm.L_D   = CL/CD;
trm.V     = V;
trm.h     = h;
trm.res   = trim_residual(zsol, V, h, p, flag);
trm.ok    = ok;
trm.flag  = flag;

end

% =====================================================================
function r = trim_residual(z, V, h, p, flag)
%TRIM_RESIDUAL  配平残差（无量纲化，便于数值求解）
alpha = z(1);
de    = z(2);
T     = z(3);

x = [V; 0; alpha; 0; h; T; de];
F = wig_aero(x, p, flag);

W = p.m * p.g;
r = [ (F(1) + T*sin(alpha + p.i_T) - W) / W;              % 法向力平衡
      (T*cos(alpha + p.i_T) - F(2))        / W;           % 切向力平衡
       F(3) / (W * p.c) ];                                % 俯仰力矩平衡
end

% =====================================================================
function [z, ok] = newton_trim(z, V, h, p, flag)
%NEWTON_TRIM  阻尼牛顿法 + 数值雅可比（不依赖任何工具箱）
ok = false;
W  = p.m * p.g;
for it = 1:200
    r = trim_residual(z, V, h, p, flag);
    if norm(r, inf) < 1e-12
        ok = true; break;
    end
    J = zeros(3,3);
    for j = 1:3
        dz = 1e-7 * max(1, abs(z(j)));
        zp = z; zp(j) = zp(j) + dz;
        J(:,j) = (trim_residual(zp, V, h, p, flag) - r) / dz;
    end
    if rcond(J) < 1e-12
        break;
    end
    d = -J \ r;
    % 阻尼线搜索
    lam = 1.0;
    for k = 1:30
        zn = z + lam*d;
        if norm(trim_residual(zn, V, h, p, flag)) < norm(r)
            break;
        end
        lam = lam * 0.5;
    end
    z = z + lam*d;
    z(3) = max(z(3), 0);        % 推力非负
end
if norm(trim_residual(z, V, h, p, flag), inf) < 1e-8
    ok = true;
end
end
