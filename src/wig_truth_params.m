function pt = wig_truth_params(p, varargin)
%WIG_TRUTH_PARAMS  构造"真实对象"参数集（含建模失配与参数摄动）
%
%   pt = wig_truth_params(p)
%   pt = wig_truth_params(p, 'Name', value, ...)
%
%   真实对象 = 名义模型 + 以下被控制器忽略的物理效应：
%     (1) 地效强度失配：真实地效因子 A、n 与名义值不同（等效于 CFD 标定
%         结果与工程估算式之间的偏差）；
%     (2) RAM 效应：贴地时翼下高压区产生的附加升力与附加低头力矩；
%     (3) 升力非线性（失速软化，tanh 形式）；
%     (4) 气动系数/质量/惯量的参数摄动。
%
%   可选项（默认值）：
%       'ge_A'   (0.045)  真实地效形状参数
%       'ge_n'   (1.300)  真实地效指数
%       'k_ram'  (0.090)  RAM 附加升力系数幅值
%       'h_ram'  (0.250)  RAM 效应特征高度 [m]
%       'x_ram'  (-0.050) RAM 附加力作用点相对机翼气动中心的偏移 [m]
%       'CLmax'  (1.300)  升力非线性软化上限
%       'CD0'    (0.032)  真实废阻力系数
%       'CD0t'   (0.0120) 平尾废阻力系数
%       'eps_a'  (0.450)  真实下洗梯度
%       'a0'     (5.90)   真实二维升力线斜率
%       'Cmac'   (-0.058) 真实机翼俯仰力矩系数
%       'm'      (12.0)   真实质量 [kg]
%       'Iyy'    (1.15)   真实俯仰惯量
%       'Tmax'   (35.0)   真实最大推力
%
%   用法：pt = wig_truth_params(p, 'ge_A', 0.05, 'm', 13.2);

pt = p;

% ---- 默认真实值 ----
d.ge_A  = 0.045;
d.ge_n  = 1.300;
d.k_ram = 0.090;
d.h_ram = 0.250;
d.x_ram = -0.050;
d.CLmax = 1.300;
d.CD0   = 0.0320;
d.CD0t  = 0.0120;
d.eps_a = 0.450;
d.a0    = 5.90;
d.Cmac  = -0.058;
d.eta_t = 0.95;
d.m     = 12.0;
d.Iyy   = 1.15;
d.Tmax  = 35.0;

% ---- 解析可选参数 ----
if mod(numel(varargin), 2) ~= 0
    error('wig_truth_params:badArgs', '可选参数必须成对出现。');
end
for k = 1:2:numel(varargin)
    key = varargin{k};
    val = varargin{k+1};
    if ~isfield(d, key)
        error('wig_truth_params:unknownOption', '未知选项：%s', key);
    end
    d.(key) = val;
end

% ---- 覆盖 ----
pt.ge_A  = d.ge_A;
pt.ge_n  = d.ge_n;
pt.k_ram = d.k_ram;
pt.h_ram = d.h_ram;
pt.x_ram = p.x_acw + d.x_ram;   % RAM 力作用点（绝对机体坐标）
pt.CLmax = d.CLmax;
pt.CD0   = d.CD0;
pt.CD0t  = d.CD0t;
pt.eps_a = d.eps_a;
pt.a0    = d.a0;
pt.Cmac  = d.Cmac;
pt.eta_t = d.eta_t;
pt.m     = d.m;
pt.Iyy   = d.Iyy;
pt.Tmax  = d.Tmax;

% ---- 由真实几何重算派生量 ----
pt.S   = pt.b*pt.c;
pt.AR  = pt.b^2/pt.S;
pt.ARt = pt.bt^2/pt.St;

% 标记：真实模型启用 RAM / 失速软化等附加效应
pt.is_truth = true;

end
