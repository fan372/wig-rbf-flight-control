function run_00_opt()
%RUN_00_OPT  控制器参数精调：围绕已验证的稳定解做【非线性闭环指标】扫描
%   （目标函数为 h_rms / h_err_max / h_min / V_rms / de_max 等时域指标，
%   逐点调用 wig_simulate；本脚本不调用 wig_closedloop_eig，不是极点配置法，
%   闭环极点分析见 run_00_clp）
%   产出 results/log_opt.txt

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_opt.txt'), 'run_00_opt_body');

end
