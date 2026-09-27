function lang = wig_plot_style(lang)
%WIG_PLOT_STYLE  统一绘图风格（字体、网格、线宽）+ 绘图语言开关
%
%   wig_plot_style()         按【当前语言】配置默认绘图风格，返回时语言不变
%                            （首次调用默认 'zh'，与历史版本行为完全一致）
%   wig_plot_style('zh')     切换到中文绘图（字体 Microsoft YaHei，图存 figures/）
%   wig_plot_style('en')     切换到英文绘图（字体 Arial，图存 figures_en/）
%   lang = wig_plot_style()  仅查询当前绘图语言，不改变任何全局设置
%
%   语言状态存放在 persistent 变量中，供 wig_lbl / wig_savefig 读取：
%     'zh' -> 绘图标签取中文分支，图形输出到 ../figures/
%     'en' -> 绘图标签取英文分支，图形输出到 ../figures_en/
%
%   注意：无参数调用【不会】重置语言，只按当前语言落地字体/线宽设置，
%   因此 run_*_body 里的 `wig_plot_style();` 在 'en' 模式下依然保持英文。

persistent curlang
if isempty(curlang)
    curlang = 'zh';
end

if nargin >= 1 && ~isempty(lang)
    if isstring(lang) && isscalar(lang)
        lang = char(lang);
    end
    if ~ischar(lang) || ~any(strcmpi(lang, {'zh', 'en'}))
        error('wig_plot_style:badLang', ...
            '不支持的语言，只接受 ''zh'' 或 ''en''。');
    end
    curlang = lower(lang);
end

% 无参数调用（历史用法）与显式切换语言都要落地字体/线宽；
% 只有 `lang = wig_plot_style()` 这种"纯查询"用法不改动全局设置。
if nargin >= 1 || nargout == 0
    apply_style(curlang);
end

if nargout > 0
    lang = curlang;
end

end

% =====================================================================
function apply_style(lang)
%APPLY_STYLE  按语言选择字体族并设置全局默认绘图属性
%   中文图沿用历史字体 'Microsoft YaHei'（保证 figures/ 中的图逐字节不变）；
%   英文图用 'Arial'（IEEE 常用无衬线字体，避免中文字体带来的字形差异）。
%   字号、线宽、网格、配色等其余设置两种语言完全一致。

switch lang
    case 'en'
        fam = 'Arial';
    otherwise
        fam = 'Microsoft YaHei';
end

try
    set(0, 'defaultAxesFontName', fam);
    set(0, 'defaultTextFontName', fam);
    set(0, 'defaultLegendFontName', fam);
catch
end
set(0, 'defaultAxesFontSize', 9);
set(0, 'defaultTextFontSize', 9);
set(0, 'defaultLineLineWidth', 1.4);
set(0, 'defaultAxesLineWidth', 0.8);
set(0, 'defaultAxesGridLineStyle', ':');
set(0, 'defaultAxesXGrid', 'on');
set(0, 'defaultAxesYGrid', 'on');
set(0, 'defaultAxesBox', 'on');
set(0, 'defaultFigureColor', 'w');
set(0, 'defaultAxesColor', 'w');

end
