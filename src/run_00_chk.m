function run_00_chk()
%RUN_00_CHK  积分一致性核验：状态导数与记录量是否自洽

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_chk.txt'), 'run_00_chk_body');

end
