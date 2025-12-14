function plot_pareto_annotated(P, T_uni, T_adap)
% Highlight H-tree, Mesh, Hybrid, Adaptive on p99-skew vs power.

  Pu = T_uni.P_avgMC * 1e3;      % mW
  Su = T_uni.skew_p99 * 1e12;    % ps

  has_adap = ~isempty(T_adap);
  if has_adap
      Pa = T_adap.P_avgMC * 1e3;
      Sa = T_adap.skew_p99 * 1e12;
  end

  f = figure('Color','w');
  semilogy(Pu, Su, '-o', 'LineWidth', 1.3); hold on;
  if has_adap
      semilogy(Pa, Sa, '-s', 'LineWidth', 1.3);
  end
  grid on; box on;
  xlabel('Power (mW)');
  ylabel('p99 Skew (ps)');
  title('Skew–Power Pareto: H-tree / Mesh / Hybrid / Region-Adaptive');

  % Find indices for key points in uniform curve
  [~, i_htree] = min(T_uni.p_r);          % p_r = 0
  [~, i_mesh]  = max(T_uni.p_r);          % p_r = 1
  [~, i_hyb]   = min(abs(T_uni.p_r - 0.25)); % pick p_r ≈ 0.25 as “hybrid”

  plot(Pu(i_htree), Su(i_htree), 'ko', 'MarkerSize',9, 'LineWidth',1.8);
  text(Pu(i_htree), Su(i_htree)*1.2, 'H-tree (p_r=0)', ...
       'HorizontalAlignment','center', 'FontSize',8);

  plot(Pu(i_mesh), Su(i_mesh), 'ko', 'MarkerSize',9, 'LineWidth',1.8);
  text(Pu(i_mesh), Su(i_mesh)*1.2, 'Mesh (p_r=1)', ...
       'HorizontalAlignment','center', 'FontSize',8);

  plot(Pu(i_hyb), Su(i_hyb), 'ko', 'MarkerSize',9, 'LineWidth',1.8);
  text(Pu(i_hyb), Su(i_hyb)*1.2, sprintf('Hybrid (p_r=%.2g)', T_uni.p_r(i_hyb)), ...
       'HorizontalAlignment','center', 'FontSize',8);

  if has_adap
      % pick adaptive point with similar avg p_r
      target = T_uni.p_r(i_hyb);
      [~, i_ad] = min(abs(T_adap.p_r_avg - target));
      plot(Pa(i_ad), Sa(i_ad), 'ks', 'MarkerSize',9, 'LineWidth',1.8);
      text(Pa(i_ad), Sa(i_ad)*1.2, ...
           sprintf('Region-adaptive (avg p_r=%.2g)', T_adap.p_r_avg(i_ad)), ...
           'HorizontalAlignment','center', 'FontSize',8);
      legend('Uniform','Region-Adaptive','Location','southwest');
  else
      legend('Uniform','Location','southwest');
  end

  ylim([1e-1, 1e3]);  % adjust if needed
  exportgraphics(f, fullfile(P.outdir,'pareto_annotated.png'), 'Resolution',300);
  close(f);
end
