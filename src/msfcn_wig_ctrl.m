function msfcn_wig_ctrl(block)
%MSFCN_WIG_CTRL  RBF 神经网络自适应飞控 —— Level-2 MATLAB S-Function（离散）
%
%   输入 : [x(7); ref(4)] = [V;gam;alpha;q;h;T;de; h_c;hd_c;V_c;Vd_c]（11x1）
%   输出 : u = [de_cmd; dt_cmd]（2x1）
%   采样 : Ts = p.sim.Ts（零阶保持）
%   DWork: 1 个，数值打包保存控制器内部状态（4 个滤波状态 + 量测滤波 4 个
%          + 力矩通道权值 N1 + 阻力通道权值 N2）
%
%   参数取自基础工作区变量：
%       p_nom  —— 名义参数（控制器内部模型）
%       x0_sim —— 初始状态（用于指令滤波器与量测滤波器初始化）

setup(block);

end

% =====================================================================
function setup(block)

p  = getpar_nom();
nn = wig_rbf_init(p);
nz = 8 + nn.N1 + nn.N2;

block.NumInputPorts  = 1;
block.NumOutputPorts = 1;
block.SetPreCompInpPortInfoToDynamic;
block.SetPreCompOutPortInfoToDynamic;

block.InputPort(1).Dimensions        = 11;
block.InputPort(1).DatatypeID        = 0;
block.InputPort(1).Complexity        = 'Real';
block.InputPort(1).DirectFeedthrough = true;
block.InputPort(1).SamplingMode      = 'Sample';

block.OutputPort(1).Dimensions    = 2;
block.OutputPort(1).DatatypeID    = 0;
block.OutputPort(1).Complexity    = 'Real';
block.OutputPort(1).SamplingMode  = 'Sample';

block.NumDworks = 0;   % 真实数量在 PostPropagationSetup 中声明

block.SampleTimes = [p.sim.Ts 0];
block.SetAccelRunOnTLC(false);
block.SimStateCompliance = 'DefaultSimState';

block.RegBlockMethod('PostPropagationSetup', @DoPostPropSetup);
block.RegBlockMethod('InitializeConditions', @InitConditions);
block.RegBlockMethod('Outputs',              @Output);
block.RegBlockMethod('Update',               @Update);

end

% =====================================================================
function DoPostPropSetup(block)
% DWork（离散状态）数量只能在 PostPropagationSetup 中设置
p  = getpar_nom();
nn = getnn();
nz = 8 + nn.N1 + nn.N2;

block.NumDworks = 1;
block.Dwork(1).Name            = 'ctrlState';
block.Dwork(1).Dimensions      = nz;
block.Dwork(1).DatatypeID      = 0;
block.Dwork(1).Complexity      = 'Real';
block.Dwork(1).UsedAsDiscState = true;
end

% =====================================================================
function InitConditions(block)
p    = getpar_nom();
x0   = evalin('base', 'x0_sim');
ctrl = wig_ctrl_init(p, x0);
block.Dwork(1).Data = wig_ctrl_pack(ctrl);
end

% =====================================================================
function Output(block)
p   = getpar_nom();
nn  = getnn();
in  = block.InputPort(1).Data;
x   = in(1:7);
ref = in(8:11);

ctrl = wig_ctrl_unpack(block.Dwork(1).Data, nn);
[u, ctrl] = wig_ctrl_update(x(:), ref(:), ctrl, p);

block.Dwork(1).Data      = wig_ctrl_pack(ctrl);
block.OutputPort(1).Data = u(:);

end

% =====================================================================
function Update(~)
% 状态已在 Outputs 中更新（单速率离散块）
end

% =====================================================================
function nn = getnn()
persistent NN
if isempty(NN)
    NN = wig_rbf_init(getpar_nom());
end
nn = NN;
end

% =====================================================================
function p = getpar_nom()
persistent P
if isempty(P)
    P = evalin('base', 'p_nom');
end
p = P;
end
