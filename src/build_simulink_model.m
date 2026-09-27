function build_simulink_model(modelName, opts)
%BUILD_SIMULINK_MODEL  以编程方式构建地效飞行器 RBF 自适应飞控 Simulink 模型
%
%   build_simulink_model()                     % 默认模型名 wig_adaptive_fcs
%   build_simulink_model('myModel')
%   build_simulink_model('myModel', struct('plant','truth','Tend',40,'refH',...,'refV',...))
%
%   模型结构（与下方 add_block / add_line 严格一一对应）：
%
%     [From Workspace: 参考指令]                      [To Workspace: 参考记录 ref]
%      变量 refdata（4 路：h_c,hd_c,V_c,Vd_c）          变量 refout
%            |                                                ^
%            | 4 路                                           | 4 路
%            v                                                |
%       +-----------+  11 路   +---------------------+         |
%       |   Mux     |--------->| RBF自适应飞控        |---------+
%       | Inputs=7,4|          | msfcn_wig_ctrl      |
%       +-----------+          | （200 Hz 离散）      |-------> [To Workspace: 控制量记录 u]
%            ^                 +---------------------+          变量 uout（2 路）
%            | 7 状态                 | 2 路 u = [de_cmd; dt_cmd]
%            |                        v
%            |              +----------------------+
%            +--------------| 被控对象              |
%                           | msfcn_wig_plant      |-------> [To Workspace: 状态记录 x]
%                           | （7 阶连续状态）      |          变量 xout（7 状态）
%                           +----------------------+
%
%   说明：Mux 端口 1 = 被控对象 7 个状态 x，端口 2 = refdata 的 4 路参考指令 ref，
%   合计 11 路送入控制器 S-Function；控制器输出 u = [de_cmd; dt_cmd]（2 路）回送
%   被控对象。全模型共三个 To Workspace 记录（xout / uout / refout），
%   【模型中没有 Terminator 模块】。
%
%   被控对象：msfcn_wig_plant（7 阶连续状态，Level-2 MATLAB S-Function）
%   控制器　：msfcn_wig_ctrl （200 Hz 离散，RBF 自适应 + 鲁棒项）
%   参考指令：由 refdata = [t, h_c, hd_c, V_c, Vd_c] 构成，源自二阶指令滤波器

if nargin < 1 || isempty(modelName)
    modelName = 'wig_adaptive_fcs';
end
if nargin < 2
    opts = struct();
end

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'models');
if ~exist(outd, 'dir'), mkdir(outd); end

p  = wig_params();
pt = wig_truth_params(p);

if isfield(opts,'plant') && ~isempty(opts.plant), plantFlag = opts.plant; else, plantFlag = 'truth'; end
Tend = 40.0;
if isfield(opts,'Tend') && ~isempty(opts.Tend), Tend = opts.Tend; end

% ---- 参考指令与工作点 ----
if isfield(opts,'refH') && ~isempty(opts.refH), refH = opts.refH; else
    refH = [0 0.20; 3 0.35; 12 0.10; 21 0.25];
end
if isfield(opts,'refV') && ~isempty(opts.refV), refV = opts.refV; else
    refV = [0 18; 6 20];
end

dt = p.sim.dt;
Ts = p.sim.Ts;
t  = (0:Ts:Tend)';                       % 参考指令在控制器采样率上生成
refdata = local_refgen(t, refH, refV, 1.2, 1.2);

if strcmpi(plantFlag, 'truth')
    Pobj = pt;
else
    Pobj = p;
end
trm = wig_trim(p.V0, p.h0, Pobj, plantFlag);
x0  = trm.x;

% 把参数与参考放入基础工作区（From Workspace / DialogPrm 均在基础工作区求值）
assignin('base', 'refdata', refdata);
assignin('base', 'p_nom',   p);
assignin('base', 'p_obj',   Pobj);
assignin('base', 'x0_sim',  x0);

% ---- 关闭已有模型 ----
if bdIsLoaded(modelName)
    try
        set_param(modelName, 'Dirty', 'off');
        close_system(modelName, 0);
    catch
        close_system(modelName, 1);
    end
end
new_system(modelName);
load_system(modelName);

SFC = 'simulink/User-Defined Functions/Level-2 MATLAB S-Function';

add_block(SFC, [modelName '/被控对象（7阶纵向非线性模型）'], ...
    'Position', [470 180 640 260]);
set_param([modelName '/被控对象（7阶纵向非线性模型）'], 'FunctionName', 'msfcn_wig_plant');

add_block(SFC, [modelName '/RBF自适应飞控（200Hz离散）'], ...
    'Position', [250 175 400 265]);
set_param([modelName '/RBF自适应飞控（200Hz离散）'], 'FunctionName', 'msfcn_wig_ctrl');

add_block('simulink/Sources/From Workspace', [modelName '/参考指令'], ...
    'Position', [30 300 160 350]);
set_param([modelName '/参考指令'], 'VariableName', 'refdata');
set_param([modelName '/参考指令'], 'SampleTime', num2str(Ts));
set_param([modelName '/参考指令'], 'Interpolate', 'on');
set_param([modelName '/参考指令'], 'OutputAfterFinalValue', 'Holding final value');

add_block('simulink/Signal Routing/Mux', [modelName '/Mux'], ...
    'Position', [190 230 215 320], 'Inputs', '7,4');

add_block('simulink/Sinks/To Workspace', [modelName '/状态记录 x'], ...
    'Position', [700 150 790 190]);
set_param([modelName '/状态记录 x'], 'VariableName', 'xout');
set_param([modelName '/状态记录 x'], 'SaveFormat', 'Structure With Time');
set_param([modelName '/状态记录 x'], 'MaxDataPoints', 'inf');

add_block('simulink/Sinks/To Workspace', [modelName '/控制量记录 u'], ...
    'Position', [700 260 790 300]);
set_param([modelName '/控制量记录 u'], 'VariableName', 'uout');
set_param([modelName '/控制量记录 u'], 'SaveFormat', 'Structure With Time');

add_block('simulink/Sinks/To Workspace', [modelName '/参考记录 ref'], ...
    'Position', [700 360 790 400]);
set_param([modelName '/参考记录 ref'], 'VariableName', 'refout');
set_param([modelName '/参考记录 ref'], 'SaveFormat', 'Structure With Time');

% ---- 连线 ----
add_line(modelName, '参考指令/1', 'Mux/2', 'autorouting', 'on');
add_line(modelName, '被控对象（7阶纵向非线性模型）/1', 'Mux/1', 'autorouting', 'on');
add_line(modelName, 'Mux/1', 'RBF自适应飞控（200Hz离散）/1', 'autorouting', 'on');
add_line(modelName, 'RBF自适应飞控（200Hz离散）/1', ...
         '被控对象（7阶纵向非线性模型）/1', 'autorouting', 'on');
add_line(modelName, '被控对象（7阶纵向非线性模型）/1', '状态记录 x/1', 'autorouting', 'on');
add_line(modelName, 'RBF自适应飞控（200Hz离散）/1', '控制量记录 u/1', 'autorouting', 'on');
add_line(modelName, '参考指令/1', '参考记录 ref/1', 'autorouting', 'on');

% ---- 求解器与仿真设置 ----
set_param(modelName, 'Solver', 'ode4');
set_param(modelName, 'FixedStep', num2str(dt));
set_param(modelName, 'StopTime', num2str(Tend));
set_param(modelName, 'SolverType', 'Fixed-step');
set_param(modelName, 'SaveOutput', 'off');
set_param(modelName, 'SaveTime', 'on');
set_param(modelName, 'RelTol', '1e-6');
set_param(modelName, 'AbsTol', '1e-8');

% 模型不设置 PreLoadFcn。旧版本的 PreLoadFcn 只是把基础工作区里已有的
% p_nom/p_obj/x0_sim 读回同名变量后立即丢弃（写回 base 之外的任何地方都没有），
% 属于空操作，故置为空字符串。
% 注意：模型运行依赖基础工作区变量 p_nom / p_obj / x0_sim / refdata
% （由本函数 assignin 写入，run_simulink 亦会写入），控制器与对象 S-Function
% 在初始化时用 evalin('base', ...) 读取它们。因此【必须先调用
% build_simulink_model（或 run_simulink）准备好这些变量，再打开/仿真模型】，
% 否则模型会因基础工作区缺少变量而报错。
set_param(modelName, 'PreLoadFcn', '');

% ---- 保存 ----
slxPath = fullfile(outd, [modelName '.slx']);
save_system(modelName, slxPath);

fprintf('Simulink 模型已生成: %s\n', wig_shortpath(slxPath));
fprintf('  被控对象: %s 参数（%s），来自基础工作区变量 p_obj\n', plantFlag, class(Pobj));
fprintf('  控制器  : 名义参数来自基础工作区变量 p_nom，初始状态 x0_sim\n');
fprintf('  仿真时长: %.1f s，定步长 ode4，步长 %.4f s\n', Tend, dt);
fprintf('  参考指令: h %s | V %s\n', mat2str(refH), mat2str(refV));

end

% =====================================================================
function ref = local_refgen(t, refH, refV, wn_h, wn_V)
%LOCAL_REFGEN  二阶指令滤波器（与 wig_simulate 内部一致）
N = numel(t);
zh = [refH(1,2); 0];
zv = [refV(1,2); 0];
h_c  = zeros(N,1); hd_c = zeros(N,1);
V_c  = zeros(N,1); Vd_c = zeros(N,1);
th = refH; tv = refV;
for k = 1:N
    tk = t(k);
    h_t = interp1(th(:,1), th(:,2), tk, 'previous', th(end,2));
    v_t = interp1(tv(:,1), tv(:,2), tk, 'previous', tv(end,2));
    if k > 1
        dtk = t(k) - t(k-1);
        zh = zh + dtk*[zh(2); wn_h^2*(h_t - zh(1)) - 2*wn_h*zh(2)];
        zv = zv + dtk*[zv(2); wn_V^2*(v_t - zv(1)) - 2*wn_V*zv(2)];
    end
    h_c(k) = zh(1); hd_c(k) = zh(2);
    V_c(k) = zv(1); Vd_c(k) = zv(2);
end
ref = [t, h_c, hd_c, V_c, Vd_c];
end
