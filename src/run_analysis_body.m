function run_analysis_body()
%RUN_ANALYSIS_BODY  模型分析主体

wig_plot_style();
p  = wig_params();
pt = wig_truth_params(p);

out = struct();
out.p  = p;
out.pt = pt;

fprintf('================ 地效飞行器纵向模型分析 ================\n\n');

%% ================= 1. 地效特性 =================
hv = linspace(0.01, 1.20, 240);
kap_n = zeros(size(hv)); kap_t = zeros(size(hv));
awn   = zeros(size(hv)); awt   = zeros(size(hv));
for k = 1:numel(hv)
    kn = wig_ge(hv(k), p.b,  p);
    kt = wig_ge(hv(k), p.b, pt);
    kap_n(k) = kn;  kap_t(k) = kt;
    awn(k) = p.a0 /(1 + p.a0 *kn/(pi*p.AR *p.e));
    awt(k) = pt.a0/(1 + pt.a0*kt/(pi*pt.AR*pt.e));
end
aw0_n = p.a0 /(1 + p.a0 *1/(pi*p.AR *p.e));
aw0_t = pt.a0/(1 + pt.a0*1/(pi*pt.AR*pt.e));

fprintf('---- 1. 地效因子与有效升力线斜率 ----\n');
fprintf('  h[m]   h/b    kappa_nom kappa_true  a_w,nom  a_w,true  a_w增幅(nom)\n');
for hh = [0.05 0.10 0.15 0.20 0.30 0.50 0.80 1.20]
    kn = wig_ge(hh, p.b, p);  kt = wig_ge(hh, p.b, pt);
    an = p.a0 /(1 + p.a0 *kn/(pi*p.AR *p.e));
    at = pt.a0/(1 + pt.a0*kt/(pi*pt.AR*pt.e));
    fprintf('%6.3f %7.4f %10.4f %10.4f %9.4f %9.4f %11.2f%%\n', ...
        hh, hh/p.b, kn, kt, an, at, (an/aw0_n-1)*100);
end

f1 = figure('Position',[100 100 900 340]);
subplot(1,2,1);
plot(hv, kap_n, 'b-', hv, kap_t, 'r--');
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
ylabel(wig_lbl('地效因子 \kappa','Ground-effect factor \kappa'));
legend({wig_lbl('\kappa_{nom}（名义）','\kappa_{nom} (nominal)'), ...
        wig_lbl('\kappa_{true}（真实）','\kappa_{true} (true plant)')}, ...
    'Location','northwest');
title(wig_lbl('(a) 地效因子 \kappa(h)','(a) Ground-effect factor \kappa(h)'));
ylim([0 1.05]);

subplot(1,2,2);
plot(hv, awn/aw0_n, 'b-', hv, awt/aw0_t, 'r--', hv, kap_n, 'g-.');
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
ylabel(wig_lbl('相对自由空气的比值','Ratio to free-air value'));
legend({wig_lbl('a_{w,GE}/a_{w,\infty}（名义）','a_{w,GE}/a_{w,\infty} (nominal)'), ...
        wig_lbl('a_{w,GE}/a_{w,\infty}（真实）','a_{w,GE}/a_{w,\infty} (true plant)'), ...
        'C_{Di,GE}/C_{Di,\infty}'}, ...
    'Location','east');
title(wig_lbl('(b) 升力线斜率增强与诱导阻力下降', ...
              '(b) Lift-curve-slope gain and induced-drag reduction'));
wig_savefig(f1, 'fig1_ge');

%% ================= 2. 配平特性 =================
hT = 0.05:0.025:0.55;
nT = numel(hT);
TR_n = cell(nT,1); TR_t = cell(nT,1);
al_n = zeros(nT,1); de_n = zeros(nT,1); dt_n = zeros(nT,1); ld_n = zeros(nT,1);
al_t = zeros(nT,1); de_t = zeros(nT,1); dt_t = zeros(nT,1); ld_t = zeros(nT,1);
dMdh = zeros(nT,1); dLdh = zeros(nT,1); sm   = zeros(nT,1);
for k = 1:nT
    a = wig_trim(p.V0, hT(k), p,  'nominal');  TR_n{k} = a;
    b = wig_trim(p.V0, hT(k), pt, 'truth');    TR_t{k} = b;
    al_n(k)=a.alpha; de_n(k)=a.de; dt_n(k)=a.dt; ld_n(k)=a.L_D;
    al_t(k)=b.alpha; de_t(k)=b.de; dt_t(k)=b.dt; ld_t(k)=b.L_D;

    % 真实对象在配平点的地效稳定性导数（统一用 wig_mdh_decomp，中心差分）
    Dk = wig_mdh_decomp(b.x, pt);
    dMdh(k) = Dk.total;
    dLdh(k) = Dk.dLdh;

    % 静稳定裕度（中性点相对 CG，以平均气动弦为单位）
    %  V_H = l_t*S_t/(c*S)；尾翼对中性点的后移量 = eta_t*V_H*(a_t/a_w)*(1-deps/dalpha)*c
    %  升力线斜率一律取模型自身的有效值（不再使用硬编码常数）
    VH   = pt.lt*pt.St/(pt.c*pt.S);
    [~, ax_] = wig_aero(b.x, pt, 'truth');
    a_w  = ax_.aw;
    a_t  = ax_.at;
    np_aft = -pt.x_acw + pt.eta_t*VH*(a_t/a_w)*(1 - pt.eps_a*wig_ge(hT(k),pt.b,pt))*pt.c;
    sm(k) = np_aft/pt.c;
end

fprintf('\n---- 2. 配平特性（V=%.1f m/s） ----\n', p.V0);
fprintf('  h[m]   alpha_nom alpha_true  de_nom  de_true   dt_nom  dt_true   L/D_nom L/D_true  dL/dh[N/m] dM/dh[N·m/m]  SM[%%MAC]\n');
for k = 1:4:nT
    fprintf('%6.3f %9.3f %10.3f %8.3f %8.3f %8.4f %8.4f %9.2f %8.2f %11.1f %12.3f %9.2f\n', ...
        hT(k), al_n(k)*180/pi, al_t(k)*180/pi, de_n(k)*180/pi, de_t(k)*180/pi, ...
        dt_n(k), dt_t(k), ld_n(k), ld_t(k), dLdh(k), dMdh(k), sm(k)*100);
end

f2 = figure('Position',[100 100 980 620]);
subplot(2,2,1);
plot(hT, al_n*180/pi, 'b-', hT, al_t*180/pi, 'r--');
ylabel(wig_lbl('配平迎角 \alpha_0 [deg]','Trim angle of attack \alpha_0 [deg]'));
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
legend({wig_lbl('\alpha_0（名义）','\alpha_0 (nominal)'), ...
        wig_lbl('\alpha_0（真实）','\alpha_0 (true plant)')}, 'Location','northeast');
title(wig_lbl('(a) 配平迎角','(a) Trim angle of attack'));

subplot(2,2,2);
plot(hT, de_n*180/pi, 'b-', hT, de_t*180/pi, 'r--');
ylabel(wig_lbl('配平升降舵 \delta_{e0} [deg]','Trim elevator \delta_{e0} [deg]'));
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
legend({wig_lbl('\delta_{e0}（名义）','\delta_{e0} (nominal)'), ...
        wig_lbl('\delta_{e0}（真实）','\delta_{e0} (true plant)')}, 'Location','northeast');
title(wig_lbl('(b) 配平升降舵','(b) Trim elevator deflection'));

subplot(2,2,3);
plot(hT, ld_n, 'b-', hT, ld_t, 'r--');
ylabel(wig_lbl('配平升阻比 L/D','Trim lift-to-drag ratio L/D'));
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
legend({wig_lbl('L/D（名义）','L/D (nominal)'), ...
        wig_lbl('L/D（真实）','L/D (true plant)')}, 'Location','northeast');
title(wig_lbl('(c) 升阻比（地效增升减阻）', ...
              '(c) Lift-to-drag ratio (ground-effect gain)'));

subplot(2,2,4);
yyaxis left;  plot(hT, dLdh, 'b-'); ylabel('dL/dh [N/m]');
yyaxis right; plot(hT, dMdh, 'r-'); ylabel('dM/dh [N·m/m]');
xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
title(wig_lbl('(d) 地效高度稳定性导数','(d) Ground-effect height stability derivatives'));
wig_savefig(f2, 'fig2_trim');

%% ================= 3. 纵向模态 =================
hM = 0.05:0.05:1.00;
nM = numel(hM);
ev_all = zeros(nM, 7);
ev_nog = zeros(nM, 7);
re_lp = zeros(nM,1); im_lp = zeros(nM,1); z_lp = zeros(nM,1);
for k = 1:nM
    a = wig_trim(p.V0, hM(k), pt, 'truth');
    l = wig_linearize(a, pt, 'truth');
    ev_all(k,:) = l.eig;

    png = pt; png.ge_A = 1e-9;               % 等效关闭地效
    ag  = wig_trim(p.V0, hM(k), png, 'truth');
    lg  = wig_linearize(ag, png, 'truth');
    ev_nog(k,:) = lg.eig;

    % 识别低频模态
    e = l.eig;
    sel = e(abs(imag(e))>0.05 & abs(e)<5);
    if isempty(sel)
        sel = e(abs(e)<5 & abs(real(e))<5);
    end
    if ~isempty(sel)
        [~, i2] = max(abs(imag(sel)));
        re_lp(k) = real(sel(i2)); im_lp(k) = abs(imag(sel(i2)));
        z_lp(k)  = -real(sel(i2))/abs(sel(i2));
    end
end

fprintf('\n---- 3. 纵向模态随高度变化（真实对象） ----\n');
fprintf('  h[m]   低频模态实部  虚部    阻尼比   无地效低频模态实部  虚部\n');
for k = 1:nM
    eg = ev_nog(k,:);
    selg = eg(abs(imag(eg))>0.05 & abs(eg)<5);
    if ~isempty(selg)
        [~, i2] = max(abs(imag(selg)));
        fprintf('%6.3f %12.4f %8.4f %9.4f %18.4f %8.4f\n', ...
            hM(k), re_lp(k), im_lp(k), z_lp(k), real(selg(i2)), abs(imag(selg(i2))));
    else
        fprintf('%6.3f %12.4f %8.4f %9.4f %18s %8s\n', hM(k), re_lp(k), im_lp(k), z_lp(k), '---', '---');
    end
end

f3 = figure('Position',[100 100 980 360]);
subplot(1,2,1);
hold on;
plot(real(ev_all(:)), imag(ev_all(:)), 'b.', 'MarkerSize', 10);
plot(real(ev_nog(:)), imag(ev_nog(:)), 'r+', 'MarkerSize', 6);
xline(0, 'k-', 'LineWidth', 0.8);
xlabel(wig_lbl('实部 \sigma [1/s]','Real part \sigma [1/s]'));
ylabel(wig_lbl('虚部 j\omega [1/s]','Imaginary part j\omega [1/s]'));
legend({wig_lbl('有地效（真实对象）','With ground effect (true plant)'), ...
        wig_lbl('无地效 \kappa\equiv1','Without ground effect \kappa\equiv1')}, ...
    'Location','southwest');
title(wig_lbl('(a) 纵向极点分布（h=0.05~1.0 m）', ...
              '(a) Longitudinal pole map (h = 0.05-1.0 m)'));
xlim([-12 3]); ylim([-12 12]);

subplot(1,2,2);
plot(hM, re_lp, 'bo-'); hold on;
xline(0,'k-'); xlabel(wig_lbl('离地高度 h [m]','Altitude h [m]'));
ylabel(wig_lbl('低频模态实部 \sigma [1/s]','Real part of the low-frequency mode \sigma [1/s]'));
title(wig_lbl('(b) 浮沉-高度耦合模态实部（\sigma>0 即失稳）', ...
              '(b) Real part of the phugoid-height coupled mode (\sigma>0 means unstable)'));
wig_savefig(f3, 'fig3_modes');

%% ================= 4. 经典浮沉理论校核 =================
fprintf('\n---- 4. 经典浮沉模态理论校核 ----\n');
fprintf('（Lanchester 2 状态近似： wn_p = sqrt(2)*g/V, zeta_p = 1/(sqrt(2)*(L/D))）\n');
for hh = [0.02 0.20 0.50 1.20]
    a = wig_trim(p.V0, hh, pt, 'truth');
    F = wig_aero(a.x, pt, 'truth');
    L = F(1); D = F(2);
    wn_p = sqrt(2)*pt.g/p.V0;
    zeta_p = D/(sqrt(2)*L);
    fprintf('h=%.2f m: L=%.3f N D=%.3f N L/D=%.3f -> 经典 wn_p=%.4f zeta_p=%+.4f\n', ...
        hh, L, D, L/D, wn_p, zeta_p);
end

save(fullfile(fileparts(mfilename('fullpath')),'..','results','analysis.mat'), ...
     'hT','al_n','al_t','de_n','de_t','dt_n','dt_t','ld_n','ld_t','dLdh','dMdh','sm', ...
     'hM','ev_all','ev_nog','re_lp','im_lp','z_lp','hv','kap_n','kap_t','awn','awt');

fprintf('\n================ 模型分析结束 ================\n');

end
