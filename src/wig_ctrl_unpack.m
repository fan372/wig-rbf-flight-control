function c = wig_ctrl_unpack(z, nn)
%WIG_CTRL_UNPACK  由数值向量还原控制器内部状态结构体
%
%   c = wig_ctrl_unpack(z, nn)   nn 为 wig_rbf_init 给出的网络结构
%
%   输入校验（不合法时以标识符 wig_ctrl_unpack:badSize 报错）：
%       * nn 必须含字段 N1、N2（RBF 节点数）；
%       * 向量长度必须等于 8 + nn.N1 + nn.N2，否则说明 DWork 尺寸与当前
%         网络结构不匹配（例如改动 n1/n2 后未重新编译模型）。
%   合法输入的解包顺序与旧版本完全一致。

z = z(:);

if ~isstruct(nn) || ~isfield(nn, 'N1') || ~isfield(nn, 'N2')
    error('wig_ctrl_unpack:badSize', ...
        'wig_ctrl_unpack: 网络结构 nn 必须包含字段 N1 与 N2（见 wig_rbf_init）。');
end

nz = 8 + nn.N1 + nn.N2;
if numel(z) ~= nz
    error('wig_ctrl_unpack:badSize', ...
        ['wig_ctrl_unpack: 状态向量长度必须为 8 + N1 + N2 = 8 + %d + %d = %d，' ...
         '当前 numel(z) = %d（DWork 尺寸与网络结构不匹配？）。'], ...
        nn.N1, nn.N2, nz, numel(z));
end

c = struct();
c.nn    = nn;
c.gam_c = z(1);
c.th_c  = z(2);
c.q_cf  = z(3);
c.IV    = z(4);
c.xf    = z(5:8);

n1 = nn.N1;  n2 = nn.N2;
c.W1 = z(9 : 8+n1);
c.W2 = z(9+n1 : 8+n1+n2);

end
