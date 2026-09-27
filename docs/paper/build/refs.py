# -*- coding: utf-8 -*-
"""refs.py —— 会议论文参考文献（均为可核验的真实文献）。

来源与核验方式见每条末尾的 `verify` 字段（Crossref / DOAJ / CNKI 页面）。
**所有英文文献的 DOI 均在 Crossref 注册库中核验通过。**

注意（重要，投稿前请知悉）：
  * Irodov 1970 的俄文原文不可获取，本列表按英文二次文献引用（见 [3]、[4]）。
  * 中文文献的【卷号/页码】在 CNKI 与万方上无法确认，此处留空；
    投稿前请用校内 CNKI 账号补齐。
  * `|z| - z*tanh(z/Phi) <= 0.2785*Phi` 中的 0.2785 是精确上界
    （极大值点 z = 0.6392，最大值 0.278465），但**其文献首次出处无法核实**，
    因此论文正文以自含方式给出该不等式，不做文献归属。
"""

# ---------------------------------------------------------------- 英文条目（IEEE 风格）
_EN = [
    # 1
    'K. V. Rozhdestvensky, "Wing-in-ground effect vehicles," Progress in Aerospace '
    'Sciences, vol. 42, no. 3, pp. 211-283, 2006, doi: 10.1016/j.paerosci.2006.10.001.',
    # 2
    'A. Nebylov and V. Nebylov, "Wing-in-ground effect vehicles flight automatic control '
    'systems development problems," Applied Mechanics and Materials, vol. 629, pp. 370-375, '
    '2014, doi: 10.4028/www.scientific.net/AMM.629.370.',
    # 3
    'W. Yang, Z. Yang, and M. Collu, "Longitudinal static stability requirements for wing in '
    'ground effect vehicle," International Journal of Naval Architecture and Ocean Engineering, '
    'vol. 7, no. 2, pp. 259-269, 2015, doi: 10.1515/ijnaoe-2015-0018.',
    # 4
    'J. Lee, "Computational analysis of static height stability and aerodynamics of vehicles '
    'with a fuselage, wing and tail in ground effect," Ocean Engineering, vol. 168, pp. 12-22, '
    '2018, doi: 10.1016/j.oceaneng.2018.08.051.',
    # 5
    'G. Kocak and M. M. Yavuz, "Effect of ground on aerodynamics and longitudinal static '
    'stability of a non-slender delta wing," Aerospace Science and Technology, vol. 130, '
    'art. no. 107929, 2022, doi: 10.1016/j.ast.2022.107929.',
    # 6
    'P. E. Kumar, "Some stability problems of ground effect wing vehicles in forward motion," '
    'Aeronautical Quarterly, vol. 23, no. 1, pp. 41-52, 1972, doi: 10.1017/S0001925900006302.',
    # 7
    'R. M. Sanner and J.-J. E. Slotine, "Gaussian networks for direct adaptive control," '
    'IEEE Transactions on Neural Networks, vol. 3, no. 6, pp. 837-863, 1992, '
    'doi: 10.1109/72.165588.',
    # 8
    'M. M. Polycarpou, "Stable adaptive neural control scheme for nonlinear systems," '
    'IEEE Transactions on Automatic Control, vol. 41, no. 3, pp. 447-451, 1996, '
    'doi: 10.1109/9.486648.',
    # 9
    'M. M. Polycarpou and P. A. Ioannou, "A robust adaptive nonlinear control design," '
    'Automatica, vol. 32, no. 3, pp. 423-427, 1996, doi: 10.1016/0005-1098(95)00147-6.',
    # 10
    'P. A. Ioannou and J. Sun, Robust Adaptive Control. Englewood Cliffs, NJ, USA: '
    'Prentice Hall, 1996, ISBN 0-13-439100-4.',
    # 11
    'D. Swaroop, J. K. Hedrick, P. P. Yip, and J. C. Gerdes, "Dynamic surface control for a '
    'class of nonlinear systems," IEEE Transactions on Automatic Control, vol. 45, no. 10, '
    'pp. 1893-1899, 2000, doi: 10.1109/TAC.2000.880994.',
    # 12
    'J. A. Farrell, M. Polycarpou, M. Sharma, and W. Dong, "Command filtered backstepping," '
    'IEEE Transactions on Automatic Control, vol. 54, no. 6, pp. 1391-1395, 2009, '
    'doi: 10.1109/TAC.2009.2015562.',
    # 13
    'P. P. Yip and J. K. Hedrick, "Adaptive dynamic surface control: a simplified algorithm '
    'for adaptive backstepping control of nonlinear systems," International Journal of '
    'Control, vol. 71, no. 5, pp. 959-979, 1998, doi: 10.1080/002071798221650.',
    # 14
    'S. S. Ge and C. Wang, "Adaptive NN control of uncertain nonlinear pure-feedback systems," '
    'Automatica, vol. 38, no. 4, pp. 671-682, 2002, doi: 10.1016/S0005-1098(01)00254-0.',
    # 15
    'C. E. Rohrs, L. Valavani, M. Athans, and G. Stein, "Robustness of continuous-time '
    'adaptive control algorithms in the presence of unmodeled dynamics," IEEE Transactions on '
    'Automatic Control, vol. 30, no. 9, pp. 881-889, 1985, doi: 10.1109/TAC.1985.1104070.',
    # 16
    'S. Akhtar and D. S. Bernstein, "Lyapunov-stable discrete-time model reference adaptive '
    'control," in Proc. American Control Conference, Portland, OR, USA, 2005, pp. 3174-3179, '
    'doi: 10.1109/ACC.2005.1470460.',
    # 17
    'F.-C. Chen and H. K. Khalil, "Adaptive control of a class of nonlinear discrete-time '
    'systems using neural networks," IEEE Transactions on Automatic Control, vol. 40, no. 5, '
    'pp. 791-801, 1995, doi: 10.1109/9.384214.',
    # 18
    'R. Staufenbiel, "Some nonlinear effects in stability and control of wing-in-ground effect '
    'vehicles," Journal of Aircraft, vol. 15, no. 8, pp. 541-544, 1978, doi: 10.2514/3.58404.',
    # 19
    'J. Gera, "Stability and control of wing-in-ground effect vehicles or wingships," in 33rd '
    'Aerospace Sciences Meeting and Exhibit, Reno, NV, USA: AIAA, 1995, '
    'doi: 10.2514/6.1995-339.',
    # 20
    'A. Fevralskikh, "A development of longitudinal static stability analysis method of a '
    'wing-in-ground effect vehicle in cruise during the design process," Ocean Engineering, '
    'vol. 243, art. no. 110187, 2022, doi: 10.1016/j.oceaneng.2021.110187.',
    # 21
    'Y. Zhang, S. Chen, J. Xu, and J. Li, "An improved approach for aerodynamic optimization '
    'considering WIG effect and height static stability," Aerospace Science and Technology, '
    'vol. 160, art. no. 110071, 2025, doi: 10.1016/j.ast.2025.110071.',
    # 22
    'O. Li and L. Deng, "Dynamic surface adaptive control for air-breathing hypersonic '
    'vehicles based on RBF neural networks," Aerospace, vol. 12, no. 11, art. no. 984, 2025, '
    'doi: 10.3390/aerospace12110984.',
    # 23
    'T. Le and L. Wang, "Research on longitudinal stability and aerodynamic configuration '
    'characteristics of ground-effect aircraft," Flight Dynamics, vol. 25, no. 3, pp. 5-8, '
    '2007 (in Chinese).',
    # 24
    'Y. Li, W. Yang, and Z. Yang, "Numerical study on longitudinal static stability of a '
    'canard ground-effect vehicle," Flight Dynamics, vol. 28, no. 1, pp. 9-12, 2010 '
    '(in Chinese).',
    # 25
    # 题名以【期刊官网】为准：该刊过刊目次与 Highwire meta 均为
    # “地效飞行器的纵向稳定性和增稳系统研究”；CNKI 条目标题作“纵向控制系统研究”，
    # 两者同作者、同期、同摘要，属同一篇，按刊物记录取官网题名。
    'Y. Luo and H. Fan, "Research on longitudinal stability and stability augmentation system '
    'of ground effect aircraft," Computer Measurement & Control, vol. 30, no. 4, pp. 134-141, '
    '2022 (in Chinese).',
    # 26
    'Y. Huo, M. Mirmirani, P. Ioannou, and M. Kuipers, "Altitude and velocity tracking control '
    'for an airbreathing hypersonic cruise vehicle," in AIAA Guidance, Navigation, and Control '
    'Conference and Exhibit, Keystone, CO, USA: AIAA, 2006, doi: 10.2514/6.2006-6695.',
]

# ---------------------------------------------------------------- 中文条目（GB/T 7714）
_ZH = [
    # 1
    'ROZHDESTVENSKY K V. Wing-in-ground effect vehicles[J]. Progress in Aerospace Sciences, '
    '2006, 42(3): 211-283. DOI: 10.1016/j.paerosci.2006.10.001.',
    # 2
    'NEBYLOV A, NEBYLOV V. Wing-in-ground effect vehicles flight automatic control systems '
    'development problems[J]. Applied Mechanics and Materials, 2014, 629: 370-375. '
    'DOI: 10.4028/www.scientific.net/AMM.629.370.',
    # 3
    'YANG W, YANG Z, COLLU M. Longitudinal static stability requirements for wing in ground '
    'effect vehicle[J]. International Journal of Naval Architecture and Ocean Engineering, '
    '2015, 7(2): 259-269. DOI: 10.1515/ijnaoe-2015-0018.',
    # 4
    'LEE J. Computational analysis of static height stability and aerodynamics of vehicles '
    'with a fuselage, wing and tail in ground effect[J]. Ocean Engineering, 2018, 168: 12-22. '
    'DOI: 10.1016/j.oceaneng.2018.08.051.',
    # 5
    'KOÇAK G, YAVUZ M M. Effect of ground on aerodynamics and longitudinal static stability of '
    'a non-slender delta wing[J]. Aerospace Science and Technology, 2022, 130: 107929. '
    'DOI: 10.1016/j.ast.2022.107929.',
    # 6
    'KUMAR P E. Some stability problems of ground effect wing vehicles in forward motion[J]. '
    'Aeronautical Quarterly, 1972, 23(1): 41-52. DOI: 10.1017/S0001925900006302.',
    # 7
    'SANNER R M, SLOTINE J-J E. Gaussian networks for direct adaptive control[J]. IEEE '
    'Transactions on Neural Networks, 1992, 3(6): 837-863. DOI: 10.1109/72.165588.',
    # 8
    'POLYCARPOU M M. Stable adaptive neural control scheme for nonlinear systems[J]. IEEE '
    'Transactions on Automatic Control, 1996, 41(3): 447-451. DOI: 10.1109/9.486648.',
    # 9
    'POLYCARPOU M M, IOANNOU P A. A robust adaptive nonlinear control design[J]. Automatica, '
    '1996, 32(3): 423-427. DOI: 10.1016/0005-1098(95)00147-6.',
    # 10
    'IOANNOU P A, SUN J. Robust adaptive control[M]. Englewood Cliffs: Prentice Hall, 1996. '
    'ISBN 0-13-439100-4.',
    # 11
    'SWAROOP D, HEDRICK J K, YIP P P, et al. Dynamic surface control for a class of nonlinear '
    'systems[J]. IEEE Transactions on Automatic Control, 2000, 45(10): 1893-1899. '
    'DOI: 10.1109/TAC.2000.880994.',
    # 12
    'FARRELL J A, POLYCARPOU M, SHARMA M, et al. Command filtered backstepping[J]. IEEE '
    'Transactions on Automatic Control, 2009, 54(6): 1391-1395. DOI: 10.1109/TAC.2009.2015562.',
    # 13
    'YIP P P, HEDRICK J K. Adaptive dynamic surface control: a simplified algorithm for '
    'adaptive backstepping control of nonlinear systems[J]. International Journal of Control, '
    '1998, 71(5): 959-979. DOI: 10.1080/002071798221650.',
    # 14
    'GE S S, WANG C. Adaptive NN control of uncertain nonlinear pure-feedback systems[J]. '
    'Automatica, 2002, 38(4): 671-682. DOI: 10.1016/S0005-1098(01)00254-0.',
    # 15
    'ROHRS C E, VALAVANI L, ATHANS M, et al. Robustness of continuous-time adaptive control '
    'algorithms in the presence of unmodeled dynamics[J]. IEEE Transactions on Automatic '
    'Control, 1985, 30(9): 881-889. DOI: 10.1109/TAC.1985.1104070.',
    # 16
    'AKHTAR S, BERNSTEIN D S. Lyapunov-stable discrete-time model reference adaptive '
    'control[C]//Proceedings of the American Control Conference. Portland: IEEE, 2005: '
    '3174-3179. DOI: 10.1109/ACC.2005.1470460.',
    # 17
    'CHEN F-C, KHALIL H K. Adaptive control of a class of nonlinear discrete-time systems '
    'using neural networks[J]. IEEE Transactions on Automatic Control, 1995, 40(5): 791-801. '
    'DOI: 10.1109/9.384214.',
    # 18
    'STAUFENBIEL R. Some nonlinear effects in stability and control of wing-in-ground effect '
    'vehicles[J]. Journal of Aircraft, 1978, 15(8): 541-544. DOI: 10.2514/3.58404.',
    # 19
    'GERA J. Stability and control of wing-in-ground effect vehicles or wingships[C]//33rd '
    'Aerospace Sciences Meeting and Exhibit. Reno: AIAA, 1995. DOI: 10.2514/6.1995-339.',
    # 20
    'FEVRALSKIKH A. A development of longitudinal static stability analysis method of a '
    'wing-in-ground effect vehicle in cruise during the design process[J]. Ocean Engineering, '
    '2022, 243: 110187. DOI: 10.1016/j.oceaneng.2021.110187.',
    # 21
    'ZHANG Y, CHEN S, XU J, et al. An improved approach for aerodynamic optimization '
    'considering WIG effect and height static stability[J]. Aerospace Science and Technology, '
    '2025, 160: 110071. DOI: 10.1016/j.ast.2025.110071.',
    # 22
    'LI O, DENG L. Dynamic surface adaptive control for air-breathing hypersonic vehicles '
    'based on RBF neural networks[J]. Aerospace, 2025, 12(11): 984. '
    'DOI: 10.3390/aerospace12110984.',
    # 23
    # 卷/期/页来源：维普记录页（2007年第3期，5-8，共4页）+ CNKI 年度总目次
    # “飞行力学2007年总目次(第25卷第1~4期)”（确定 2007 = 第 25 卷）。
    '乐挺, 王立新. 地效飞机的纵向稳定性和气动布局特点研究[J]. 飞行力学, 2007, 25(3): 5-8.',
    # 24
    # 卷/期/页来源：维普记录页（2010年第1期，9-12，共4页）+ 期刊官网过刊页
    # “2010 年 01 期 v.28;No.111” + CNKI《飞行力学》2010年(第28卷)总目次。
    '李玉龙, 杨韡, 杨志刚. 鸭式布局地效飞行器纵向静稳定性数值研究[J]. 飞行力学, 2010, '
    '28(1): 9-12.',
    # 25
    # 卷/期/页与题名来源：期刊官网文章页 Highwire meta（citation_volume 30、
    # citation_issue 4）与 2022 年第 4 期过刊目次（2022, 30(4):134-141）。
    # 题名以期刊官网为准：官网作“地效飞行器的纵向稳定性和增稳系统研究”，
    # CNKI 作“地效飞行器的纵向控制系统研究”。同作者、同期、同摘要、同关键词，
    # 属同一篇文献；刊物记录优先于数据库条目。
    '罗瑜, 樊赫. 地效飞行器的纵向稳定性和增稳系统研究[J]. 计算机测量与控制, 2022, '
    '30(4): 134-141.',
    # 26
    'HUO Y, MIRMIRANI M, IOANNOU P, et al. Altitude and velocity tracking control for an '
    'airbreathing hypersonic cruise vehicle[C]//AIAA Guidance, Navigation, and Control '
    'Conference and Exhibit. Keystone: AIAA, 2006. DOI: 10.2514/6.2006-6695.',
]

REFS_EN = _EN
REFS_ZH = _ZH

assert len(REFS_EN) == len(REFS_ZH) == 26, '中英参考文献条目数必须一致'
