function run_all()
%RUN_ALL  地效飞行器 RBF 神经网络自适应飞控 —— 一键运行全部算例
%
%   依次执行（顺序固定，前 5 项为出图/出报告的主流程）：
%       run_00_smoke      冒烟测试（自检）              -> results/log_smoke.txt
%       run_analysis      模型分析（地效/配平/模态）     -> results/log_analysis.txt, fig1~fig3
%       run_scenarios     典型场景仿真                  -> results/log_scenarios.txt, fig4~fig9
%       run_montecarlo    蒙特卡洛鲁棒性统计            -> results/log_montecarlo.txt, fig10
%       run_simulink      Simulink 模型构建与一致性验证 -> results/log_simulink.txt, fig11
%       run_00_mdh        dM/dh 分量分解诊断            -> results/log_mdh.txt, fig12
%       run_00_stab       稳定性/配平诊断               -> results/log_stab.txt
%       run_00_clp        闭环极点谱排查                -> results/log_clp.txt
%       run_00_cfdfit     ANSYS CFD 数据接口测试        -> results/log_cfdfit.txt
%
%   本函数【不】产生下列诊断日志，需在 src 下单独运行对应入口函数：
%       run_00_dbg      -> results/log_dbg.txt   （逐拍调试时间历程，输出很长）
%       run_00_chk      -> results/log_chk.txt   （积分一致性核验）
%       run_00_chk2     -> results/log_chk2.txt  （逐点核对 dgam/dt）
%       run_00_lag      -> results/log_lag.txt   （时滞/时间常数敏感性扫描）
%       run_00_opt      -> results/log_opt.txt   （非线性指标精调扫描）
%       run_00_tune     -> results/log_tune.txt  （四轮增益整定扫描）
%   以上 6 个脚本耗时较长或属于逐拍调试/参数扫描，故不并入一键流程。
%
%   全部文本输出写入 ../results/log_*.txt（UTF-8），图形写入 ../figures/*.png
%   本函数会切换到 src 目录执行，退出时（含出错退出）用 onCleanup 恢复调用者目录。

here = fileparts(mfilename('fullpath'));
addpath(here);
oldDir = cd(here);
restoreDir = onCleanup(@() cd(oldDir));   % 退出（含异常退出）时自动恢复原工作目录

fprintf('################################################################\n');
fprintf('#  地效飞行器 RBF 神经网络自适应飞行控制 —— 全部算例\n');
fprintf('################################################################\n\n');

t0 = tic;

steps = { ...
    'run_00_smoke',   '冒烟测试 / 自检'; ...
    'run_analysis',   '模型分析（地效特性、配平、纵向模态）'; ...
    'run_scenarios',  '典型场景仿真'; ...
    'run_montecarlo', '蒙特卡洛鲁棒性统计'; ...
    'run_simulink',   'Simulink 模型构建与一致性验证'; ...
    'run_00_mdh',     'dM/dh 分量分解诊断'; ...
    'run_00_stab',    '稳定性与配平诊断'; ...
    'run_00_clp',     '闭环极点谱排查'; ...
    'run_00_cfdfit',  'ANSYS CFD 数据接口测试'};

for i = 1:size(steps,1)
    fprintf('\n>>>>>>>>>>>>>>>> [%d/%d] %s <<<<<<<<<<<<<<<<\n\n', ...
        i, size(steps,1), steps{i,2});
    ts = tic;
    feval(steps{i,1});
    fprintf('\n>>>>>>>>>>>>>>>> [%d/%d] 完成，耗时 %.1f s <<<<<<<<<<<<<<<<\n', ...
        i, size(steps,1), toc(ts));
end

fprintf('\n################################################################\n');
fprintf('#  全部算例完成，总耗时 %.1f s\n', toc(t0));
fprintf('#  日志: results/log_*.txt    图形: figures/*.png    模型: models/*.slx\n');
fprintf('#  注: log_dbg/log_chk/log_chk2/log_lag/log_opt/log_tune 需单独运行对应脚本\n');
fprintf('################################################################\n');

end
