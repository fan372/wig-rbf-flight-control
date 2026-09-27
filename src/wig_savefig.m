function outpath = wig_savefig(fig, name)
%WIG_SAVEFIG  把图窗保存到 ../figures/name.png（英文模式：../figures_en/name.png）
%
%   outpath = wig_savefig(fig, 'fig1_ge')
%
%   输出目录由当前绘图语言决定（见 wig_plot_style）：
%     'zh' -> ../figures/      中文图；既有中文文档/技术报告依赖该目录，
%                              目录名与文件路径与历史版本完全一致
%     'en' -> ../figures_en/   英文图；供英文 IEEE 会议论文使用
%   DPI（200）与导出方式两种语言完全一致。

here = fileparts(mfilename('fullpath'));
if strcmpi(wig_plot_style(), 'en')
    sub = 'figures_en';
else
    sub = 'figures';
end
outd = fullfile(here, '..', sub);
if ~exist(outd, 'dir')
    mkdir(outd);
end
outpath = fullfile(outd, [name '.png']);

try
    exportgraphics(fig, outpath, 'Resolution', 200);
catch
    print(fig, outpath, '-dpng', '-r200');
end

end
