function dx = wig_dynamics(x, ucmd, p, flag, gust)
%WIG_DYNAMICS  地效飞行器纵向非线性动力学（7 阶）
%
%   dx = wig_dynamics(x, ucmd, p, flag, gust)
%
%   状态  x = [V; gam; alpha; q; h; T; de]
%   控制  ucmd = [de_cmd; dt_cmd]   升降舵指令 [rad]、油门指令 [0,1]
%   gust  = [ug; wg] 水平/垂向阵风 [m/s]（可选，缺省无风）
%
%   运动方程（纵向，忽略横侧向；gamma 为航迹倾角，alpha 为迎角，theta = gam + alpha）：
%       m*dV/dt   = T*cos(alpha+i_T) - D - m*g*sin(gamma)
%       m*V*dgam  = L + T*sin(alpha+i_T) - m*g*cos(gamma)
%       dalpha/dt = q - dgam/dt
%       Iyy*dq/dt = M
%       dh/dt     = V*sin(gamma)
%       dT/dt     = (T_cmd - T)/tau_T
%       dde/dt    = (de_cmd - de)/tau_e
%
%   执行器模型：升降舵与发动机均建模为【一阶滞后 + 位置限幅 + 速率限幅】
%   （升降舵：tau_e 一阶滞后、de_max 位置限幅、de_rate 速率限幅；
%     发动机：tau_T 一阶滞后、油门限幅 0~1 对应推力 Tmin~Tmax）。
%   本函数只有单一输出 dx，【不返回任何饱和标志，也不做反算（back-calculation）】，
%   因此不存在"把饱和量反馈给控制器"的通道。抗积分饱和完全由【控制器内部】
%   完成：见 wig_ctrl_update.m 第 5 节，当升降舵/油门指令超出限幅（sat_e / sat_t）
%   时冻结对应通道的自适应权值更新，避免饱和期间权值被错误误差持续激励。

if nargin < 4
    flag = 'nominal';
end
if nargin < 5
    gust = [];
end

V     = max(x(1), 0.5);
gam   = x(2);
alpha = x(3);
q     = x(4);
h     = x(5);
T     = x(6);
de    = x(7);

%% ---------------- 执行器 ----------------
de_c = wig_sat(ucmd(1), p.de_max);
dt_c = wig_sat(ucmd(2), 0.0, 1.0);

T_cmd = p.Tmin + dt_c * (p.Tmax - p.Tmin);

de_rate = wig_sat((de_c - de) / p.tau_e, p.de_rate);

%% ---------------- 气动力与力矩（含阵风引起的相对气流修正） ----------------
if ~isempty(gust) && any(gust ~= 0)
    % 地坐标系风速 -> 相对气流速度与气流航迹角
    Vx = V*cos(gam) - gust(1);
    Vz = V*sin(gam) - gust(2);
    Va = sqrt(Vx^2 + Vz^2);
    if Va < 1.0
        Va = 1.0;
    end
    gam_a   = atan2(Vz, Vx);
    alpha_a = (gam + alpha) - gam_a;      % 气流迎角（theta - gam_a）
    xa = [Va; gam_a; alpha_a; q; h; T; de];
    F = wig_aero(xa, p, flag);
else
    F = wig_aero(x, p, flag);
end
L = F(1);
D = F(2);
M = F(3);

%% ---------------- 运动方程 ----------------
Tx = T * cos(alpha + p.i_T);
Tz = T * sin(alpha + p.i_T);

Falong = Tx - D - p.m * p.g * sin(gam);
Fperp  = L + Tz - p.m * p.g * cos(gam);

dV   = Falong / p.m;
dgam = Fperp / (p.m * V);

dx = zeros(7,1);
dx(1) = dV;
dx(2) = dgam;
dx(3) = q - dgam;
dx(4) = M / p.Iyy;
dx(5) = V * sin(gam);
dx(6) = (T_cmd - T) / p.tau_T;
dx(7) = de_rate;

end
