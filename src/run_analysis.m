function run_analysis()
%RUN_ANALYSIS  模型分析：地效特性 / 配平特性 / 纵向模态 / 高度稳定性
%   产出 figures/fig1_ge.png ~ fig3_modes.png 与 results/log_analysis.txt

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_analysis.txt'), 'run_analysis_body');

end
