function run_00_stab_body()
%RUN_00_STAB_BODY  稳定性诊断主体
%   1) 打印配平点处的 A 矩阵与关键稳定性导数
%   2) 对比"有地效 / 无地效"两种情况下的纵向模态
%   3) 给出经典浮沉模态理论值用于交叉校核

p  = wig_params();
pt = wig_truth_params(p);

fprintf('=========== 纵向稳定性诊断 ===========\n');

h0 = p.h0; V0 = p.V0;
trm = wig_trim(V0, h0, pt, 'truth');
lin = wig_linearize(trm, pt, 'truth');

nm = {'V','gam','alpha','q','h','T','de'};
fprintf('\n---- A 矩阵（真实对象, V=%.1f m/s, h=%.3f m） ----\n', V0, h0);
fprintf('%12s', '');
for j = 1:7, fprintf('%11s', nm{j}); end
fprintf('\n');
for i = 1:7
    fprintf('%12s', ['d' nm{i} '/dt']);
    for j = 1:7
        fprintf('%11.4f', lin.A(i,j));
    end
    fprintf('\n');
end

fprintf('\n---- 关键稳定性导数（数值） ----\n');
fprintf('dVdot/dV   = %+10.5f 1/s        dVdot/dgam = %+10.5f m/s^2\n', lin.A(1,1), lin.A(1,2));
fprintf('dgamdot/dV = %+10.5f 1/m        dgamdot/dalpha = %+10.5f 1/s\n', lin.A(2,1), lin.A(2,3));
fprintf('dgamdot/dh = %+10.5f 1/(m·s)    dgamdot/dgam = %+10.5f 1/s\n', lin.A(2,5), lin.A(2,2));
fprintf('dqdot/dalpha = %+10.5f 1/s^2    dqdot/dq = %+10.5f 1/s\n', lin.A(4,3), lin.A(4,4));
fprintf('dqdot/dh   = %+10.5f 1/(m·s^2)  dqdot/dde = %+10.5f 1/s^2\n', lin.A(4,5), lin.A(4,7));

% ---- 气动力/力矩对 h 的敏感性（用统一的分量分解函数，中心差分） ----
Dd = wig_mdh_decomp(trm.x, pt);
fprintf('\n---- 地效引起的力/力矩梯度 ----\n');
fprintf('dL/dh = %+10.3f N/m      dD/dh = %+10.3f N/m     dM/dh = %+10.4f N·m/m\n', ...
    Dd.dLdh, Dd.dDdh, Dd.total);
fprintf('地效高度刚度 |dL/dh|/m = %+10.4f 1/s^2  (对应高度振荡频率 %.3f rad/s)\n', ...
    abs(Dd.dLdh)/pt.m, sqrt(abs(Dd.dLdh)/pt.m));

fprintf('\n---- dM/dh 分量分解（%+.4f N·m/m 的构成） ----\n', Dd.total);
fprintf('  机翼（稳定项）      %+9.4f N·m/m\n', Dd.wing);
fprintf('  平尾（主导不稳定项）  %+9.4f N·m/m\n', Dd.tail);
fprintf('  RAM 附加力           %+9.4f N·m/m\n', Dd.ram);
fprintf('  升力非线性软化        %+9.4f N·m/m\n', Dd.nl);
fprintf('  机体                 %+9.4f N·m/m\n', Dd.fuse);
fprintf('  推力线偏置            %+9.4f N·m/m\n', Dd.thrust);
fprintf('  分量之和 %+9.4f（残差 %.2e）\n', Dd.sum_parts, Dd.resid);

% ---- 经典浮沉模态理论值（Lanchester 二状态近似） ----
%   wn_p   = sqrt(2)*g/V
%   zeta_p = 1/(sqrt(2)*(L/D)) = D/(sqrt(2)*L)
%   注：早期版本误写为 zeta_p = D/(m*V^2*wn_p)（量纲有误，差一个 V），
%       本版本已按经典公式更正。
qbar = 0.5*pt.rho*V0^2;
m = pt.m;
F0 = wig_aero(trm.x, pt, 'truth');
CL = F0(1)/(qbar*pt.S);
CD = F0(2)/(qbar*pt.S);
D  = F0(2);
L  = F0(1);
DV = 2*D/V0;
LV = 2*L/V0;
LD = L/D;
wn_p   = sqrt(2)*pt.g/V0;
zeta_p = D/(sqrt(2)*L);
fprintf('\n---- 经典浮沉（Phugoid）理论预估（Lanchester 2 状态近似） ----\n');
fprintf('CL=%.4f CD=%.5f  L=%.3f N D=%.3f N  L/D=%.3f\n', CL, CD, L, D, LD);
fprintf('L_V=%.3f N/(m/s)  D_V=%.3f N/(m/s)\n', LV, DV);
fprintf('理论 wn_p = %.4f rad/s, zeta_p = 1/(sqrt(2)*L/D) = %+.4f\n', wn_p, zeta_p);
fprintf('（对照：若误用 D/(m*V^2*wn_p) 会得到 %+.4f，量纲缺少一个 V）\n', D/(m*V0^2*wn_p));

% ---- 有地效 / 无地效对比 ----
fprintf('\n---- 模态对比：有地效 vs 无地效 ----\n');
pno = pt;  pno.ge_A = 1e-9;      % kappa -> 1，等效关闭地效
trm_no = wig_trim(V0, h0, pno, 'truth');
lin_no = wig_linearize(trm_no, pno, 'truth');

fprintf('%-28s | %-28s\n', '有地效 (真实)', '无地效 kappa=1');
ev1 = sort_by_real(lin.eig);
ev2 = sort_by_real(lin_no.eig);
for k = 1:7
    fprintf('%+9.4f %+9.4fi           | %+9.4f %+9.4fi\n', ...
        real(ev1(k)), imag(ev1(k)), real(ev2(k)), imag(ev2(k)));
end

fprintf('\n---- 逐高度扫描：浮沉/高度模态 ----\n');
hh = [0.05 0.10 0.20 0.30 0.50 0.80 1.50 3.00];
fprintf('  h[m]   复杂低频极点(实部,虚部)    阻尼比     高度刚度 dL/dh[N/m]   wn_h[rad/s]\n');
for k = 1:numel(hh)
    tk = wig_trim(V0, hh(k), pt, 'truth');
    lk = wig_linearize(tk, pt, 'truth');
    ev = lk.eig;
    sel = ev(abs(imag(ev))>0.05 & abs(ev)<5);
    Fk  = wig_aero(tk.x, pt, 'truth');
    Fk2 = wig_aero([tk.x(1);tk.x(2);tk.x(3);tk.x(4);tk.x(5)+0.001;tk.x(6);tk.x(7)], pt, 'truth');
    dLdh = (Fk2(1)-Fk(1))/0.001;
    if ~isempty(sel)
        lm = sel(1);
        fprintf('%6.3f   %+9.5f %+9.5f      %+8.4f     %+12.3f        %8.4f\n', ...
            hh(k), real(lm), imag(lm), -real(lm)/abs(lm), dLdh, sqrt(abs(dLdh)/pt.m));
    else
        fprintf('%6.3f   ---                         ---          %+12.3f        %8.4f\n', ...
            hh(k), dLdh, sqrt(abs(dLdh)/pt.m));
    end
end

fprintf('\n=========== 诊断结束 ===========\n');

end

% =====================================================================
function ev = sort_by_real(ev)
[~, idx] = sort(real(ev), 'descend');
ev = ev(idx);
end
