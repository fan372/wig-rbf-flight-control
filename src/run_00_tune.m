function run_00_tune()
%RUN_00_TUNE  高度/姿态回路增益整定（参数扫描）

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_tune.txt'), 'run_00_tune_body');

end
