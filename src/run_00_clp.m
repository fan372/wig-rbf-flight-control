function run_00_clp()
%RUN_00_CLP  闭环极点分析

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_clp.txt'), 'run_00_clp_body');

end
