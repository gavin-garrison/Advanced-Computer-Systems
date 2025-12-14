function plot_pareto(P, T_uni, T_adap)
%PLOT_PARETO Make readable Pareto plots and save PNGs into P.outdir.
%
%   T_uni  : table with columns p_r, skew_p99, P_avgMC for uniform
%   T_adap : table with columns skew_p99, P_avgMC (can be [] if no adaptive)

  Pu_mW = T_uni.P_avgMC * 1e3;      % W -> mW
  Su_ps = T_uni.skew_p99 * 1e12;    % s -> ps

  has_adap = ~isempty(T_adap);

  if has_adap
      Pa_mW = T_adap.P_avgMC * 1e3;
      Sa_ps = T_adap.skew_p99 * 1e12;
  end

  %% ---- 1) Uniform only: log y so outlier + tiny values are visible ----
  f1 = figure('Color','w');
  semilogy(Pu_mW, Su_ps, '-o', 'LineWidth', 1.5, 'MarkerSize', 7); hold on;
  grid on; box on;
  xlabel('Power (mW)');
  ylabel('p99 Skew (ps)');
  title('Pareto (Uniform p_r) – log scale');

  % Label points with p_r
  for k = 1:height(T_uni)
      text(Pu_mW(k), Su_ps(k)*1.1, sprintf('p_r=%.2g', T_uni.p_r(k)), ...
          'HorizontalAlignment','center', 'FontSize',8);
  end

  ylim([1e-1, 1e3]);   % adjust if needed
  exportgraphics(f1, fullfile(P.outdir, 'pareto_uniform_log.png'), 'Resolution', 300);
  close(f1);

  %% ---- 2) Uniform vs Adaptive (log scale) ----
  if has_adap
      f2 = figure('Color','w');
      semilogy(Pu_mW, Su_ps, '-o', 'LineWidth', 1.5, 'MarkerSize', 7); hold on;
      semilogy(Pa_mW, Sa_ps, '-s', 'LineWidth', 1.5, 'MarkerSize', 7);
      grid on; box on;
      xlabel('Power (mW)');
      ylabel('p99 Skew (ps)');
      title('Pareto: Uniform vs Region-Adaptive (log scale)');
      legend('Uniform','Region-Adaptive','Location','southwest');

      % Labels (optional but nice)
      for k = 1:height(T_uni)
          text(Pu_mW(k), Su_ps(k)*1.1, sprintf('u:%.2g', T_uni.p_r(k)), ...
              'HorizontalAlignment','center', 'FontSize',8);
      end
      for k = 1:height(T_adap)
          text(Pa_mW(k), Sa_ps(k)*1.1, sprintf('a:%.2g', T_adap.p_r_avg(k)), ...
              'HorizontalAlignment','center', 'FontSize',8);
      end

      ylim([1e-1, 1e3]);
      exportgraphics(f2, fullfile(P.outdir, 'pareto_uniform_vs_adaptive_log.png'), ...
                     'Resolution', 300);
      close(f2);
  end

  %% ---- 3) Zoomed linear plot ignoring p_r = 0 monster ----
  idx = (T_uni.p_r > 0);
  if any(idx)
      f3 = figure('Color','w');
      plot(Pu_mW(idx), Su_ps(idx), '-o', 'LineWidth', 1.5, 'MarkerSize', 7);
      grid on; box on;
      xlabel('Power (mW)');
      ylabel('p99 Skew (ps)');
      title('Pareto (Uniform p_r>0) – zoomed');
      exportgraphics(f3, fullfile(P.outdir, 'pareto_uniform_zoom.png'), 'Resolution', 300);
      close(f3);
  end
end
