function run_00_cfdfit()
%RUN_00_CFDFIT  测试 ANSYS CFD 数据接口（读取模板并标定地效因子）

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_cfdfit.txt'), 'run_00_cfdfit_body');

end
