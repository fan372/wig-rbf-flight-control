function z = wig_norm(x, rng)
%WIG_NORM  将物理量线性映射到归一化区间 [-1,1]
%
%   z = wig_norm(x, rng)    x: nx1, rng: nx2 ([lo hi])

lo = rng(:,1);
hi = rng(:,2);
z  = 2 * (x(:) - lo) ./ (hi - lo) - 1;

end
