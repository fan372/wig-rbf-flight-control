function run_montecarlo()
%RUN_MONTECARLO  蒙特卡洛鲁棒性统计（随机参数摄动）
%   产出 figures/fig10_montecarlo.png 与 results/log_montecarlo.txt

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_montecarlo.txt'), 'run_montecarlo_body');

end
