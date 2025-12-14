function stats = monte_carlo(P, topo, ~)
%MONTE_CARLO Run Monte Carlo for skew/power (no toolboxes, no parfor).
%   Uses sim_transient in fast mode (no waveforms) for speed.

  % Effective MC sample count (optional override)
  if isfield(P, 'Nmc_eff') && P.Nmc_eff > 0
      Nmc = P.Nmc_eff;
  else
      Nmc = P.Nmc;
  end

  skews  = zeros(Nmc,1);
  powers = zeros(Nmc,1);

  for m = 1:Nmc
      % Copy params for this sample
      Pm = P;

      % Fast mode: do NOT store waveforms in sim_transient
      Pm.store_waveforms = false;

      % Global interconnect variation
      dRg = randn() * P.sig_Rp_global;
      dCg = randn() * P.sig_Cp_global;

      % Scale interconnect
      Pm.Rp_tree = P.Rp_tree * (1 + dRg);
      Pm.Rp_mesh = P.Rp_mesh * (1 + dRg);
      Pm.Cp_tree = P.Cp_tree * (1 + dCg);
      Pm.Cp_mesh = P.Cp_mesh * (1 + dCg);

      % Driver variation (clamped to >= 1 Ω)
      Pm.Rdrv = max(1, P.Rdrv * (1 + randn() * P.sig_Rdrv));

      % Build MNA and run transient
      net = build_mna(Pm, topo);
      out = sim_transient(Pm, net);

      skews(m)  = out.skew;
      powers(m) = out.Pavg;
  end

  % ---------- Statistics ----------
  % Sort once for multiple percentiles
  x = sort(skews(:));
  n = numel(x);

  stats.skew_p95  = pct_sorted(x, n, 95);
  stats.skew_p99  = pct_sorted(x, n, 99);
  stats.Pavg      = mean(powers);
  stats.skew_mean = mean(skews);
  stats.skew_std  = std(skews);

  % NEW: keep raw samples for robustness plots
  stats.skews     = skews;
  stats.powers    = powers;
end

% ===== Local helper: percentile assuming x is already sorted =====
function v = pct_sorted(x, n, p)
%PCT_SORTED Linear-interpolated percentile (0–100) given sorted x.
  if n == 0
      v = NaN;
      return;
  end

  % Hyndman–Fan type 7 (MATLAB/NumPy default)
  r  = 1 + (n - 1) * (p / 100);
  lo = floor(r);
  hi = ceil(r);

  if lo == hi
      v = x(lo);
  else
      v = x(lo) + (r - lo) * (x(hi) - x(lo));
  end
end
