function ctrl = wig_ctrl_init(p, x0)
%WIG_CTRL_INIT  初始化 RBF 神经网络自适应控制器内部状态
%
%   ctrl = wig_ctrl_init(p)
%   ctrl = wig_ctrl_init(p, x0)   % x0 为初始状态（用于把指令滤波器初值
%                                 %  对齐到初始俯仰姿态，避免起动瞬态）
%
%   控制器内部状态（全部为显式传递，便于在 Simulink 的 S-Function 中保存）：
%       .nn     RBF 网络结构（中心、宽度、归一化区间）
%       .W1     力矩通道权值 (N1 x 1)
%       .W2     阻力通道权值 (N2 x 1)
%       .gam_c  航迹倾角指令滤波状态 [rad]
%       .th_c   俯仰角指令滤波状态 [rad]
%       .q_cf   俯仰角速度指令滤波状态 [rad/s]
%       .IV     速度误差积分状态 [m/s]
%       .xf     量测一阶滤波状态 [V; alpha; q; h]

nn = wig_rbf_init(p);

ctrl.nn   = nn;
ctrl.W1   = zeros(nn.N1, 1);
ctrl.W2   = zeros(nn.N2, 1);
ctrl.gam_c = 0;
ctrl.th_c  = 0;
ctrl.q_cf  = 0;
ctrl.IV    = 0;
ctrl.xf    = [];

if nargin >= 2 && ~isempty(x0)
    x0 = x0(:);
    ctrl.th_c  = x0(2) + x0(3);   % theta = gam + alpha
    ctrl.gam_c = x0(2);
    ctrl.xf    = x0([1 3 4 5]);
end

end
