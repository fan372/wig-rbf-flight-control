function s = wig_lbl(zh, en)
%WIG_LBL  按当前绘图语言返回中文或英文字符串
%
%   s = wig_lbl('中文标签', 'English label')
%
%   当前绘图语言由 wig_plot_style('zh') / wig_plot_style('en') 设定，默认 'zh'
%   （见 wig_plot_style）。因此同一份绘图脚本可以产出两套图：
%
%     wig_plot_style('zh');  wig_savefig(f, 'fig1_ge')  -> ../figures/fig1_ge.png
%     wig_plot_style('en');  wig_savefig(f, 'fig1_ge')  -> ../figures_en/fig1_ge.png
%
%   使用约定：
%     * 只把【用户可见的文字】交给本函数（xlabel/ylabel/zlabel/title/legend/
%       text/annotation/sgtitle，以及最终进入图里的 sprintf/fprintf 文本）；
%     * 两个分支都必须保留原有的 TeX 数学写法（\kappa、\alpha、\delta_e …），
%       只翻译包裹数学符号的文字；
%     * 纯 ASCII/数学符号的标签（如 'dL/dh [N/m]'）无需经过本函数；
%     * 图例是 cell 数组时要逐项调用，例如
%         legend({wig_lbl('指令','Command'), wig_lbl('自适应','Adaptive')});
%     * 控制台/日志文本【不要】经过本函数，日志必须保持中文原样。

if nargin < 2
    error('wig_lbl:nargin', ...
        'wig_lbl 需要两个参数：wig_lbl(''中文字符串'', ''English string'')。');
end
if isstring(zh) && isscalar(zh), zh = char(zh); end
if isstring(en) && isscalar(en), en = char(en); end
if ~ischar(zh) || ~ischar(en)
    error('wig_lbl:badInput', 'wig_lbl 的两个参数都必须是字符数组（cell 图例请逐项调用）。');
end

if strcmpi(wig_plot_style(), 'en')
    s = en;
else
    s = zh;
end

end
