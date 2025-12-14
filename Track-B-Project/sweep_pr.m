function T = sweep_pr(P)
%SWEEP_PR Sweep uniform p_r and (optionally) region-adaptive p_r,
% run MC, and generate Pareto plots, heatmaps, and robustness plots.

  % ----------------------------------------------------------------------
  % Determine actual number of regions from the H-tree builder
  % ----------------------------------------------------------------------
  [taps, ~] = htree_build(P);
  nR = numel(taps);

  pr_refs = P.pr_values(:);
  nPR     = numel(pr_refs);

  rows_uni = zeros(nPR, 6);   % [p_r, skew_nom, skew_p95, skew_p99, P_nom, P_avgMC]

  % ======================================================================
  %                           UNIFORM SWEEP
  % ======================================================================
  for i = 1:nPR
      pr = pr_refs(i);

      % Uniform mesh density for all regions
      pr_map = pr * ones(nR,1);

      topo = gen_topology(P, pr_map);
      net  = build_mna(P, topo);

      % Nominal (no extra MC variation – just baseline params)
      out_nom = sim_transient(P, net);

      % Monte-Carlo with variation
      stats = monte_carlo(P, topo, []);

      rows_uni(i,:) = [ ...
          pr, ...
          out_nom.skew, ...
          stats.skew_p95, ...
          stats.skew_p99, ...
          out_nom.Pavg, ...
          stats.Pavg];

      % Heatmap for nominal arrivals
      fname_hm = fullfile(P.outdir, sprintf('heat_uniform_pr%.2f.png', pr));
      export_heatmap(P, topo, out_nom.arr, fname_hm);
  end

  T = array2table(rows_uni, 'VariableNames', ...
       {'p_r','skew_nom','skew_p95','skew_p99','P_nom','P_avgMC'});

  % Save numeric results (UNIFORM) with the names you were using
  writetable(T, fullfile(P.outdir,'pareto_uniform.csv'));

  % Keep a single MAT that will hold everything
  S = struct();
  S.P          = P;
  S.T_uniform  = T;

  % ======================================================================
  %                        REGION-ADAPTIVE SWEEP
  % ======================================================================
  if P.adaptive
      rows_ad = zeros(nPR, 6);   % [p_r_avg, skew_nom, skew_p95, skew_p99, P_nom, P_avgMC]

      for i = 1:nPR
          pr_avg = pr_refs(i);

          % 1) First pass (uniform) to get nominal arrivals
          pr0   = pr_avg * ones(nR,1);
          topo0 = gen_topology(P, pr0);
          net0  = build_mna(P, topo0);
          out0  = sim_transient(P, net0);

          % 2) Adaptive mapping based on lateness
          pr_map = adaptive_policy(P, topo0, out0.arr(:), pr_avg);

          topoA  = gen_topology(P, pr_map);
          netA   = build_mna(P, topoA);

          % Nominal adaptive result
          outA   = sim_transient(P, netA);
          statsA = monte_carlo(P, topoA, []);

          rows_ad(i,:) = [ ...
              mean(pr_map), ...
              outA.skew, ...
              statsA.skew_p95, ...
              statsA.skew_p99, ...
              outA.Pavg, ...
              statsA.Pavg];

          % Heatmap for adaptive arrivals
          fname_hmA = fullfile(P.outdir, sprintf('heat_adapt_avgpr%.2f.png', pr_avg));
          export_heatmap(P, topoA, outA.arr, fname_hmA);
      end

      TA = array2table(rows_ad, 'VariableNames', ...
          {'p_r_avg','skew_nom','skew_p95','skew_p99','P_nom','P_avgMC'});

      writetable(TA, fullfile(P.outdir,'pareto_adaptive.csv'));
      S.T_adaptive = TA;
  else
      TA = [];
      S.T_adaptive = [];
  end

  % Save combined MAT with everything important
  save(fullfile(P.outdir,'sweep_results.mat'), '-struct', 'S');

  % ======================================================================
  %          PLOT 0: BASIC LINEAR PARETOS (UNIFORM + VS ADAPTIVE)
  % ======================================================================
  Pu_mW = T.P_avgMC * 1e3;        % W -> mW
  Su_ps = T.skew_p99 * 1e12;      % s -> ps

  % Uniform only
  f0 = figure('Color','w');
  plot(Pu_mW, Su_ps, '-o', 'LineWidth', 1.5, 'MarkerSize', 7);
  grid on; box on;
  xlabel('Power (mW)');
  ylabel('p99 Skew (ps)');
  title('Pareto: Uniform p_r');
  exportgraphics(f0, fullfile(P.outdir,'pareto_uniform.png'), 'Resolution',300);
  close(f0);

  % Uniform vs adaptive (linear)
  if ~isempty(TA)
      Pa_mW = TA.P_avgMC * 1e3;
      Sa_ps = TA.skew_p99 * 1e12;

      f0b = figure('Color','w');
      plot(Pu_mW, Su_ps, '-o', 'LineWidth', 1.5, 'MarkerSize', 7); hold on;
      plot(Pa_mW, Sa_ps, '-s', 'LineWidth', 1.5, 'MarkerSize', 7);
      grid on; box on;
      xlabel('Power (mW)');
      ylabel('p99 Skew (ps)');
      title('Pareto: Uniform vs Adaptive');
      legend('Uniform','Region-Adaptive','Location','best');
      exportgraphics(f0b, fullfile(P.outdir,'pareto_uniform_vs_adaptive.png'), 'Resolution',300);
      close(f0b);
  end

  % ======================================================================
  %                      PLOT 1: ANNOTATED PARETO (LOG Y)
  %   Skew–Power Pareto highlighting H-tree, Mesh, Hybrid, Adaptive
  % ======================================================================
  f1 = figure('Color','w');
  semilogy(Pu_mW, Su_ps, '-o', 'LineWidth', 1.5, 'MarkerSize', 7); hold on;
  grid on; box on;
  xlabel('Power (mW)');
  ylabel('p99 Skew (ps)');
  title('Skew–Power Pareto: H-tree / Mesh / Hybrid / Region-Adaptive');

  % Identify key points on the uniform curve
  [~, i_htree] = min(T.p_r);                 % p_r closest to 0
  [~, i_mesh]  = max(T.p_r);                 % p_r closest to 1
  [~, i_hyb]   = min(abs(T.p_r - 0.25));     % mid hybrid ~0.25

  % Mark H-tree
  plot(Pu_mW(i_htree), Su_ps(i_htree), 'ko', 'MarkerSize',9, 'LineWidth',1.8);
  text(Pu_mW(i_htree), Su_ps(i_htree)*1.2, ...
       sprintf('H-tree (p_r=%.2g)', T.p_r(i_htree)), ...
       'HorizontalAlignment','center', 'FontSize',8);

  % Mark Mesh
  plot(Pu_mW(i_mesh), Su_ps(i_mesh), 'ko', 'MarkerSize',9, 'LineWidth',1.8);
  text(Pu_mW(i_mesh), Su_ps(i_mesh)*1.2, ...
       sprintf('Mesh (p_r=%.2g)', T.p_r(i_mesh)), ...
       'HorizontalAlignment','center', 'FontSize',8);

  % Mark Hybrid (uniform)
  plot(Pu_mW(i_hyb), Su_ps(i_hyb), 'ko', 'MarkerSize',9, 'LineWidth',1.8);
  text(Pu_mW(i_hyb), Su_ps(i_hyb)*1.2, ...
       sprintf('Hybrid uniform (p_r=%.2g)', T.p_r(i_hyb)), ...
       'HorizontalAlignment','center', 'FontSize',8);

  % Overlay adaptive curve if available
  if ~isempty(TA)
      Pa_mW = TA.P_avgMC * 1e3;
      Sa_ps = TA.skew_p99 * 1e12;
      semilogy(Pa_mW, Sa_ps, '-s', 'LineWidth',1.5, 'MarkerSize',7);

      % Find adaptive point with avg p_r closest to uniform hybrid
      target = T.p_r(i_hyb);
      [~, i_ad] = min(abs(TA.p_r_avg - target));
      plot(Pa_mW(i_ad), Sa_ps(i_ad), 'ks', 'MarkerSize',9, 'LineWidth',1.8);
      text(Pa_mW(i_ad), Sa_ps(i_ad)*1.2, ...
           sprintf('Region-adaptive (avg p_r=%.2g)', TA.p_r_avg(i_ad)), ...
           'HorizontalAlignment','center', 'FontSize',8);

      legend('Uniform','Region-Adaptive','Location','southwest');
  else
      legend('Uniform','Location','southwest');
  end

  ylim([1e-1, 1e3]);  % tweak as needed
  exportgraphics(f1, fullfile(P.outdir,'pareto_annotated.png'), 'Resolution',300);
  close(f1);

  % ======================================================================
  %                 PLOT 2: SKEW VS MESH DENSITY p_r
  % ======================================================================
  f2 = figure('Color','w');
  plot(T.p_r, T.skew_p99*1e12, '-o', 'LineWidth',1.5, 'MarkerSize',7); hold on;
  grid on; box on;
  xlabel('Uniform mesh density p_r');
  ylabel('p99 Skew (ps)');
  title('Skew vs Mesh Density (Uniform)');

  if ~isempty(TA)
      plot(TA.p_r_avg, TA.skew_p99*1e12, '-s', 'LineWidth',1.5, 'MarkerSize',7);
      legend('Uniform','Region-Adaptive avg p_r','Location','northeast');
  end

  exportgraphics(f2, fullfile(P.outdir,'skew_vs_pr.png'), 'Resolution',300);
  close(f2);

  % ======================================================================
  %       PLOT 3: ROBUSTNESS DISTRIBUTIONS (PDF + CDF of skew)
  % ======================================================================

  hero_labels = {};
  hero_skews  = {};   % each cell: vector of skew samples [s]

  % Slightly larger Nmc for robustness plots (but capped)
  if isfield(P, 'Nmc_robust')
      Nmc_robust = P.Nmc_robust;
  else
      Nmc_robust = min(max(P.Nmc, 150), 300);
  end

  % --- H-tree ---
  pr_ht = T.p_r(i_htree);
  P_R          = P;
  P_R.Nmc      = Nmc_robust;
  P_R.store_waveforms = false;
  pr_map = pr_ht * ones(nR,1);
  topoR  = gen_topology(P_R, pr_map);
  statsR = monte_carlo(P_R, topoR, []);
  s = get_skew_samples(statsR);
  hero_skews{end+1}  = s;
  hero_labels{end+1} = sprintf('H-tree (p_r=%.2g)', pr_ht);

  % --- Hybrid uniform (p_r ~ 0.25) ---
  pr_hyb = T.p_r(i_hyb);
  P_R          = P;
  P_R.Nmc      = Nmc_robust;
  P_R.store_waveforms = false;
  pr_map = pr_hyb * ones(nR,1);
  topoR  = gen_topology(P_R, pr_map);
  statsR = monte_carlo(P_R, topoR, []);
  s = get_skew_samples(statsR);
  hero_skews{end+1}  = s;
  hero_labels{end+1} = sprintf('Hybrid uniform (p_r=%.2g)', pr_hyb);

  % --- Region-adaptive with similar avg p_r (if available) ---
  if ~isempty(TA)
      target = pr_hyb;
      [~, i_ad] = min(abs(TA.p_r_avg - target));
      pr_avg = pr_refs(i_hyb);

      % Rebuild adaptive topology for that reference pr_avg
      pr0   = pr_avg * ones(nR,1);
      topo0 = gen_topology(P, pr0);
      net0  = build_mna(P, topo0);
      out0  = sim_transient(P, net0);
      pr_map_ad = adaptive_policy(P, topo0, out0.arr(:), pr_avg);
      topoAd    = gen_topology(P, pr_map_ad);

      P_R          = P;
      P_R.Nmc      = Nmc_robust;
      P_R.store_waveforms = false;

      statsAd = monte_carlo(P_R, topoAd, []);
      s = get_skew_samples(statsAd);
      hero_skews{end+1}  = s;
      hero_labels{end+1} = sprintf('Region-adaptive (avg p_r=%.2g)', TA.p_r_avg(i_ad));
  end

  % ---- PDFs ----
  nCfg = numel(hero_skews);
  if nCfg > 0
      f3 = figure('Color','w');
      tl = tiledlayout(1, nCfg, "TileSpacing","compact", "Padding","compact");

      for k = 1:nCfg
          nexttile;
          s_ps = hero_skews{k} * 1e12;
          histogram(s_ps, 'Normalization','pdf');
          xlabel('Skew (ps)');
          ylabel('PDF');
          title(hero_labels{k}, 'Interpreter','none');
          grid on;
      end
      title(tl, 'Skew distributions (PDF)');
      exportgraphics(f3, fullfile(P.outdir,'robustness_skew_hist.png'), 'Resolution',300);
      close(f3);

      % ---- CDF overlay ----
      f4 = figure('Color','w');
      hold on; grid on; box on;
      for k = 1:nCfg
          s_ps = sort(hero_skews{k} * 1e12);
          N    = numel(s_ps);
          F    = (1:N)/N;
          plot(s_ps, F, 'LineWidth',1.5);
      end
      xlabel('Skew (ps)');
      ylabel('CDF');
      title('Skew robustness (CDF)');
      legend(hero_labels, 'Location','southeast');
      exportgraphics(f4, fullfile(P.outdir,'robustness_skew_cdf.png'), 'Resolution',300);
      close(f4);
  end
end

% ======================================================================
% Helper: get_skew_samples(stats) with graceful fallback
% ======================================================================
function s = get_skew_samples(stats)
% Expect stats.skews from monte_carlo; if missing, synthesize
% samples from mean/std as a rough approximation.

  if isfield(stats, 'skews') && ~isempty(stats.skews)
      s = stats.skews(:);
      return;
  end

  % Fallback: approximate distribution as Gaussian with mean/std
  if isfield(stats,'skew_mean') && isfield(stats,'skew_std')
      M = 1000;
      mu = stats.skew_mean;
      sig = max(stats.skew_std, eps);
      s = mu + sig * randn(M,1);
      s(s < 0) = 0;   % no negative skew
  else
      % Last resort: just return a constant vector so plots still work
      s = repmat(stats.skew_p99, 1000, 1);
  end
end
