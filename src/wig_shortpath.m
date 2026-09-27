function s = wig_shortpath(p)
%WIG_SHORTPATH  把项目内的绝对路径显示为相对仓库根目录的路径
%
%   s = wig_shortpath(p)
%
%   日志与文档中不应出现本机绝对路径（换台机器就失效，也不适合随仓库分发）。
%   本函数把位于本仓库内的路径折叠成 `./相对路径` 形式，仓库外的路径按与仓库根
%   的相对关系给出（如 `../ANSYS/data/xxx.csv`），便于日志引用。
%
%   例（src 位于 <repo>/src）：
%       D:\...\matlab_simulink\src\..\models\wig_adaptive_fcs.slx
%         -> ./models/wig_adaptive_fcs.slx
%       D:\...\matlab_simulink\src\..\..\ANSYS\data\ge_kappa.csv
%         -> ./ANSYS/data/ge_kappa.csv

here = fileparts(mfilename('fullpath'));    % <repo>/src
root = fileparts(here);                     % <repo>

p = char(p);
if ispc
    p = strrep(p, '/', '\');
end

% ---- 逐段折叠 "." 与 ".." ----
parts = strsplit(p, filesep);
stack = {};
for i = 1:numel(parts)
    seg = parts{i};
    if isempty(seg) || strcmp(seg, '.')
        continue;
    end
    if strcmp(seg, '..')
        if numel(stack) > 1
            stack(end) = []; %#ok<AGROW>
        end
        continue;
    end
    stack{end+1} = seg; %#ok<AGROW>
end

rparts = strsplit(root, filesep);
rparts = rparts(~cellfun(@isempty, rparts));

% ---- 求与仓库根的最长公共前缀，再构造相对路径 ----
n = min(numel(stack), numel(rparts));
k = 0;
for i = 1:n
    if strcmpi(stack{i}, rparts{i})
        k = i;
    else
        break;
    end
end

if k == 0
    s = strrep(strjoin(stack, filesep), filesep, '/');   % 与仓库无公共前缀
    return;
end

up   = numel(rparts) - k;
down = stack(k+1:end);
segs = [repmat({'..'}, 1, up), down];
if isempty(segs)
    s = '.';
else
    rel = strjoin(segs, '/');
    if isempty(up)
        s = ['./' rel];
    else
        s = rel;
    end
end

end
