function run_figs_en()
%RUN_FIGS_EN  用英文标签重绘全部 12 张图到 ../figures_en/（中文图与日志原样不动）
%
%   用法（在 src 目录下，或已 addpath 到 src）：
%       run_figs_en
%
%   本脚本把绘图语言切到 'en'（见 wig_plot_style / wig_lbl / wig_savefig），
%   然后依次调用五个【主体函数】：
%       run_analysis_body    -> fig1_ge / fig2_trim / fig3_modes
%       run_scenarios_body   -> fig4_tracking ~ fig9_lowalt
%       run_montecarlo_body  -> fig10_montecarlo
%       run_simulink_body    -> fig11_simulink
%       run_00_mdh_body      -> fig12_mdh
%   12 张 PNG 以与中文图完全相同的尺寸/DPI（200）写入 ../figures_en/。
%
%   与 run_all 的区别（刻意为之）：
%     * 直接调用 *_body，【不】经过 wig_logged，因此 results/log_*.txt 不会被改写，
%       中文文档引用的日志与数字保持原样；
%     * 只切换绘图语言，不改动任何参数、算例、数值与绘图风格（颜色/线宽/DPI）；
%     * 结束时用 onCleanup 恢复 'zh' 语言与原始工作目录（正常或异常退出都恢复）；
%     * 可重复运行：输出目录与文件名固定，重复运行只覆盖 figures_en/ 下的同名 PNG。
%
%   最后一次语言自检会遍历所有打开图窗的标题/坐标轴标签/图例/文本对象，
%   一旦发现中文字符立即报错（说明有标签漏包 wig_lbl），避免英文图带中文。

here = fileparts(mfilename('fullpath'));
addpath(here);
oldDir = cd(here);
cleanupDir  = onCleanup(@() cd(oldDir));            % 恢复原工作目录
cleanupLang = onCleanup(@() wig_plot_style('zh'));  % 恢复中文绘图模式

wig_plot_style('en');

bodies = { ...
    'run_analysis_body',   'fig1~fig3   模型分析'; ...
    'run_scenarios_body',  'fig4~fig9   典型场景仿真'; ...
    'run_montecarlo_body', 'fig10       蒙特卡洛统计'; ...
    'run_simulink_body',   'fig11       Simulink 一致性验证'; ...
    'run_00_mdh_body',     'fig12       dM/dh 分量分解'};

outd = fullfile(here, '..', 'figures_en');
fprintf('################ 英文图重绘（绘图语言 = %s） ################\n', wig_plot_style());
fprintf('#  输出目录: %s    （中文图目录 ../figures/ 不受影响）\n', wig_shortpath(outd));
fprintf('#  日志: 本脚本不写日志，results/log_*.txt 保持原样\n\n');

t0 = tic;
for i = 1:size(bodies, 1)
    fprintf('\n>>>>>>>>>>>>>>>> [%d/%d] %s <<<<<<<<<<<<<<<<\n\n', ...
        i, size(bodies, 1), bodies{i, 2});
    feval(bodies{i, 1});
end
elapsed = toc(t0);

nfig = check_figs_language();

fprintf('\n################ 英文图重绘结束 ################\n');
fprintf('#  共 %d 张图写入 %s\n', nfig, wig_shortpath(outd));
fprintf('#  总耗时 %.1f s（绘图语言已恢复 %s）\n', elapsed, wig_plot_style());

end

% =====================================================================
function nfig = check_figs_language()
%CHECK_FIGS_LANGUAGE  自检：所有打开图窗的可见文本中不得出现中日韩字符
%   英文图里出现中文，说明某条标签漏包 wig_lbl；此处列出全部违规字符串并报错，
%   避免"英文论文里混进中文图"这类缺陷被静默放过。

pat  = '[\x{3000}-\x{303F}\x{4E00}-\x{9FFF}\x{FF00}-\x{FFEF}]';
figs = findall(groot, 'Type', 'figure');
bad  = {};
for k = 1:numel(figs)
    strs = fig_text_strings(figs(k));
    for j = 1:numel(strs)
        if ~isempty(regexp(strs{j}, pat, 'once'))
            bad{end+1} = sprintf('图 %s 的文本 "%s"', ...
                num2str(double(figs(k).Number)), strs{j}); %#ok<AGROW>
        end
    end
end

if ~isempty(bad)
    for j = 1:numel(bad)
        fprintf('  [发现中文] %s\n', bad{j});
    end
    error('run_figs_en:cjkInFigure', ...
        '英文图中有 %d 处中文字符，请检查是否漏用 wig_lbl。', numel(bad));
end

fprintf('\n[语言自检] %d 张图窗的标题/坐标轴标签/图例/文本对象均无中文字符。\n', numel(figs));
nfig = numel(figs);
end

% =====================================================================
function strs = fig_text_strings(f)
%FIG_TEXT_STRINGS  收集一个图窗里所有用户可见字符串
strs = {};

tx = findall(f, 'Type', 'text');            % 含 text()、图例条目、colorbar 标签
for k = 1:numel(tx)
    strs = addstr(strs, get(tx(k), 'String'));
end

ax = findall(f, 'Type', 'axes');            % 标题与坐标轴标签（兜底再取一次）
for k = 1:numel(ax)
    strs = addstr(strs, get(get(ax(k), 'Title'),  'String'));
    strs = addstr(strs, get(get(ax(k), 'XLabel'), 'String'));
    strs = addstr(strs, get(get(ax(k), 'YLabel'), 'String'));
    strs = addstr(strs, get(get(ax(k), 'ZLabel'), 'String'));
end

lg = findall(f, 'Type', 'legend');          % 图例条目
for k = 1:numel(lg)
    strs = addstr(strs, get(lg(k), 'String'));
end
end

% =====================================================================
function strs = addstr(strs, v)
%ADDSTR  把 char / cellstr / string 统一追加进 cellstr 列表
if isempty(v)
    return;
end
if isstring(v)
    v = cellstr(v);
elseif ischar(v)
    v = {v};
end
for k = 1:numel(v)
    s = v{k};
    if isstring(s)
        s = char(s);
    end
    if ischar(s) && ~isempty(s)
        strs{end+1} = s; %#ok<AGROW>
    end
end
end
