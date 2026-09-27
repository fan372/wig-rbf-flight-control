function run_00_smoke()
%RUN_00_SMOKE  阶段一冒烟测试入口
%   运行 run_00_smoke_body，输出同时打印到控制台并写入
%   results/log_smoke.txt（UTF-8）。

here = fileparts(mfilename('fullpath'));
outd = fullfile(here, '..', 'results');
if ~exist(outd, 'dir')
    mkdir(outd);
end
wig_logged(fullfile(outd, 'log_smoke.txt'), 'run_00_smoke_body');

end
