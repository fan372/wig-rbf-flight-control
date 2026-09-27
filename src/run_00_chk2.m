function run_00_chk2()
%RUN_00_CHK2  精确复现 A 组工况，逐点核对 dgam/dt 与 Fperp/(mV)

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_chk2.txt'), 'run_00_chk2_body');

end
