function run_00_dbg()
%RUN_00_DBG  控制器逐拍调试：名义对象 + 名义控制器 + 名义配平点
%   输出前若干秒的时间历程，用于定位闭环发散原因。

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd,'dir'), mkdir(outd); end
wig_logged(fullfile(outd,'log_dbg.txt'), 'run_00_dbg_body');

end
