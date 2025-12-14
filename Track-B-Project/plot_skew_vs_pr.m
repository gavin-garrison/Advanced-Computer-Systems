function plot_skew_vs_pr(P, T_uni, T_adap)
% p99 skew versus mesh density p_r (and adaptive average p_r).

  f = figure('Color','w');
  plot(T_uni.p_r, T_uni.skew_p99*1e12, '-o', 'LineWidth',1.5); hold on;
  grid on; box on;
  xlabel('Uniform mesh density p_r');
  ylabel('p99 Skew (ps)');
  title('Skew vs Mesh Density (Uniform)');

  % Optional overlay of adaptive average p_r
  if ~isempty(T_adap)
      plot(T_adap.p_r_avg, T_adap.skew_p99*1e12, '-s', 'LineWidth',1.5);
      legend('Uniform','Region-Adaptive avg p_r','Location','northeast');
  end
  exportgraphics(f, fullfile(P.outdir,'skew_vs_pr.png'), 'Resolution',300);
  close(f);
end
