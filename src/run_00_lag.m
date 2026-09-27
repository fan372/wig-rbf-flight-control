function run_00_lag()
%RUN_00_LAG  时滞/时间常数敏感性与线性化验证
%   扫描对象舵机时间常数 tau_e、控制器 DSC 滤波常数 tau_th/tau_q、
%   量测滤波 tau_f、采样周期 Ts，并做线性化预测与非线性仿真对照。
%   注意：tau_e 只作用于【被控对象】（wig_dynamics 中的舵机一阶滞后），
%   控制器 wig_ctrl_update 并不使用 tau_e，详见 run_00_lag_body.m 中的注释。
%   产出 results/log_lag.txt

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_lag.txt'), 'run_00_lag_body');

end
