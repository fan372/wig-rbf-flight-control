function nn = wig_rbf_init(p)
%WIG_RBF_INIT  构造两路 RBF 神经网络的中心、宽度与归一化区间
%
%   nn = wig_rbf_init(p)
%
%   通道 1（力矩通道）：输入 zeta = [alpha, q, h]  ->  逼近 Delta_M/Iyy [rad/s^2]
%   通道 2（阻力通道）：输入 zeta = [alpha, V, h]  ->  逼近 Delta_D/m   [m/s^2]
%
%   中心布置：在归一化坐标 [-1,1]^3 上按网格均匀布置；宽度取网格间距，
%   保证相邻基函数在中心处重叠度 exp(-0.5) ≈ 0.61。
%   归一化： z = 2*(x - lo)/(hi - lo) - 1
%
%   输出结构体 nn：
%       .C1 .sig1 .rng1 .N1    力矩通道中心(3xN1)、宽度(3x1)、区间(3x2)、节点数
%       .C2 .sig2 .rng2 .N2    阻力通道

% ---------------- 力矩通道 ----------------
rng1 = [p.ctrl.nn.c1_a(:)'; p.ctrl.nn.c1_q(:)'; p.ctrl.nn.c1_h(:)'];
n1   = p.ctrl.nn.n1(:)';
nn.rng1 = rng1;
nn.C1   = grid_centers(n1);
nn.sig1 = grid_sigma(n1);
nn.N1   = size(nn.C1, 2);

% ---------------- 阻力通道 ----------------
rng2 = [p.ctrl.nn.c2_a(:)'; p.ctrl.nn.c2_V(:)'; p.ctrl.nn.c2_h(:)'];
n2   = p.ctrl.nn.n2(:)';
nn.rng2 = rng2;
nn.C2   = grid_centers(n2);
nn.sig2 = grid_sigma(n2);
nn.N2   = size(nn.C2, 2);

end

% =====================================================================
function C = grid_centers(n)
%GRID_CENTERS  在 [-1,1]^3 上生成网格中心，返回 3 x N 矩阵
g = cell(1,3);
for i = 1:3
    if n(i) <= 1
        g{i} = 0;
    else
        g{i} = linspace(-1, 1, n(i));
    end
end
[A, B, D] = ndgrid(g{1}, g{2}, g{3});
C = [A(:)'; B(:)'; D(:)'];
end

% =====================================================================
function s = grid_sigma(n)
%GRID_SIGMA  各输入维度的 RBF 宽度 = 归一化网格间距
s = zeros(3,1);
for i = 1:3
    if n(i) > 1
        s(i) = 2/(n(i) - 1);
    else
        s(i) = 1.0;
    end
end
end
