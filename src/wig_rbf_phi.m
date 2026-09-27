function phi = wig_rbf_phi(z, C, sig)
%WIG_RBF_PHI  高斯径向基函数（RBF）向量求值
%
%   phi = wig_rbf_phi(z, C, sig)
%
%   z    3x1 归一化输入
%   C    3xN 中心矩阵（归一化坐标）
%   sig  3x1 各维度宽度
%   phi  Nx1 基函数向量，phi_j = exp( -0.5 * sum_i ((z_i-C_ij)/sig_i)^2 )
%
%   说明：基函数仅在中心邻域内显著非零，当工作点远离所有中心时 phi -> 0，
%   此时神经网络输出自然归零、控制器退化为"名义动态逆 + 鲁棒项"，
%   这一"局部支撑"性质保证了外推安全性。

N = size(C, 2);
d2 = zeros(1, N);
for i = 1:3
    d2 = d2 + ((z(i) - C(i,:)) ./ sig(i)).^2;
end
phi = exp(-0.5 * d2);
phi = phi(:);

end
