function run_00_stab()
%RUN_00_STAB  稳定性导数与地效影响诊断

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_stab.txt'), 'run_00_stab_body');

end
