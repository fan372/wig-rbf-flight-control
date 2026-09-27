function run_scenarios()
%RUN_SCENARIOS  典型飞行场景仿真与自适应/非自适应对比
%   产出 figures/fig4_tracking.png、fig5_states.png、fig6_adaptive.png、
%   fig7_perturbation.png、fig8_gust.png 以及 fig9_lowalt.png（极限低空掠飞，
%   量测噪声 + 执行器限制），并写入 results/log_scenarios.txt

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_scenarios.txt'), 'run_scenarios_body');

end
