function run_00_mdh()
%RUN_00_MDH  地效高度稳定性导数 dM/dh 的分量分解诊断

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_mdh.txt'), 'run_00_mdh_body');

end
