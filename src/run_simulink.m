function run_simulink()
%RUN_SIMULINK  构建并运行 Simulink 模型，与纯 MATLAB 脚本结果对比验证
%   产出 models/wig_adaptive_fcs.slx、figures/fig11_simulink.png、
%   results/log_simulink.txt

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_simulink.txt'), 'run_simulink_body');

end
