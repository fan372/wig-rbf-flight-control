function z = wig_ctrl_pack(c)
%WIG_CTRL_PACK  把控制器内部状态打包为数值向量（供 Simulink DWork 使用）
%
%   z = wig_ctrl_pack(ctrl)
%   布局: [gam_c; th_c; q_cf; IV; xf(4); W1(N1); W2(N2)]
%
%   输入校验（不合法时以标识符 wig_ctrl_pack:badState 报错）：
%       * c.xf 必须存在且恰为 4 个元素（量测滤波状态 [V; alpha; q; h]）；
%         wig_ctrl_init 在未给定 x0 时会把 xf 置空，需先经 wig_ctrl_update
%         用首拍量测初始化后才能打包。
%       * 打包结果长度必须等于 8 + numel(W1) + numel(W2)。
%   合法输入的打包顺序与旧版本完全一致。

nxf = 0;
if isfield(c, 'xf') && ~isempty(c.xf)
    nxf = numel(c.xf);
end
if nxf ~= 4
    error('wig_ctrl_pack:badState', ...
        ['wig_ctrl_pack: 控制器状态字段 xf 必须为 4 个元素 ' ...
         '（[V; alpha; q; h]），当前 numel(xf) = %d。'], nxf);
end

if ~isfield(c, 'W1') || ~isfield(c, 'W2')
    error('wig_ctrl_pack:badState', ...
        'wig_ctrl_pack: 控制器状态必须包含 RBF 权值字段 W1 与 W2（见 wig_ctrl_init）。');
end

n1 = numel(c.W1);
n2 = numel(c.W2);
nz = 8 + n1 + n2;

z = [c.gam_c; c.th_c; c.q_cf; c.IV; c.xf(:); c.W1(:); c.W2(:)];

if numel(z) ~= nz
    error('wig_ctrl_pack:badState', ...
        ['wig_ctrl_pack: 打包长度不一致，应为 8 + numel(W1) + numel(W2) = ' ...
         '8 + %d + %d = %d，实际 numel(z) = %d。'], n1, n2, nz, numel(z));
end

end
