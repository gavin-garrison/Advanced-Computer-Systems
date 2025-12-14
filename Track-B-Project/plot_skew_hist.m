function plot_skew_hist(P, stats_list, labels, fname)
% Plot skew distributions (histogram + CDF) for multiple configs.
%
%   stats_list : cell array of stats structs (with .skews)
%   labels     : cell array of names, e.g. {'H-tree','Hybrid','Adaptive'}

  nCfg = numel(stats_list);

  % -------- Histogram --------
  f1 = figure('Color','w');
  tiledlayout(1, nCfg, "TileSpacing","compact", "Padding","compact");

  for k = 1:nCfg
      nexttile;
      s_ps = stats_list{k}.skews * 1e12;
      histogram(s_ps, 'Normalization','pdf');
      xlabel('Skew (ps)');
      ylabel('PDF');
      title(labels{k});
      grid on;
  end
  title(tiledlayout(gcf), 'Skew distributions (PDF)');
  exportgraphics(f1, fullfile(P.outdir, [fname '_hist.png']), 'Resolution',300);
  close(f1);

  % -------- CDF overlay --------
  f2 = figure('Color','w');
  hold on; grid on; box on;
  for k = 1:nCfg
      s_ps = sort(stats_list{k}.skews * 1e12);
      N    = numel(s_ps);
      F    = (1:N)/N;
      plot(s_ps, F, 'LineWidth',1.5);
  end
  xlabel('Skew (ps)');
  ylabel('CDF');
  title('Skew robustness (CDF)');
  legend(labels, 'Location','southeast');
  exportgraphics(f2, fullfile(P.outdir, [fname '_cdf.png']), 'Resolution',300);
  close(f2);
end
