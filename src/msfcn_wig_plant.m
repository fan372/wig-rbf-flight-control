function msfcn_wig_plant(block)
%MSFCN_WIG_PLANT  地效飞行器纵向非线性模型 —— Level-2 MATLAB S-Function
%
%   输入 : u = [de_cmd; dt_cmd]（2x1）
%   输出 : x = [V; gam; alpha; q; h; T; de]（7x1）
%   连续状态 : 7 个
%
%   参数取自基础工作区变量：
%       p_obj  —— 被控对象参数结构体（真实对象用 wig_truth_params 生成）
%
%   Level-2 MATLAB S-Function 在 MATLAB 解释器中运行，可直接复用
%   wig_dynamics.m / wig_trim.m，保证 Simulink 模型与纯脚本仿真完全一致。

setup(block);

end

% =====================================================================
function setup(block)

block.NumInputPorts  = 1;
block.NumOutputPorts = 1;
block.SetPreCompInpPortInfoToDynamic;
block.SetPreCompOutPortInfoToDynamic;

block.InputPort(1).Dimensions        = 2;
block.InputPort(1).DatatypeID        = 0;
block.InputPort(1).Complexity        = 'Real';
block.InputPort(1).DirectFeedthrough = false;
block.InputPort(1).SamplingMode      = 'Sample';

block.OutputPort(1).Dimensions    = 7;
block.OutputPort(1).DatatypeID    = 0;
block.OutputPort(1).Complexity    = 'Real';
block.OutputPort(1).SamplingMode  = 'Sample';

block.NumContStates = 7;
block.SampleTimes   = [0 0];
block.SetAccelRunOnTLC(false);
block.SimStateCompliance = 'DefaultSimState';

block.RegBlockMethod('InitializeConditions', @InitConditions);
block.RegBlockMethod('Outputs',              @Output);
block.RegBlockMethod('Derivatives',          @Derivatives);

end

% =====================================================================
function InitConditions(block)
p = getpar(block);
trm = wig_trim(p.V0, p.h0, p, 'truth');
block.ContStates.Data = trm.x(:);
end

% =====================================================================
function Output(block)
block.OutputPort(1).Data = block.ContStates.Data;
end

% =====================================================================
function Derivatives(block)
p = getpar(block);
u = block.InputPort(1).Data;
x = block.ContStates.Data;
block.Derivatives.Data = wig_dynamics(x(:), u(:), p, 'truth');
end

% =====================================================================
function p = getpar(~)
%GETPAR  从基础工作区读取被控对象参数（首次调用后缓存）
persistent P
if isempty(P)
    P = evalin('base', 'p_obj');
end
p = P;
end
