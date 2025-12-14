
function export_heatmap(P, topo, arr_times, fname)
%EXPORT_HEATMAP Simple heat map of arrival times at region centers.
  nR = numel(topo.sinks);
  XY = zeros(nR,2);
  for r=1:nR
    tap = topo.taps(r);
    XY(r,:) = [tap.x, tap.y];
  end
  % Normalize times to ps
  Tps = (arr_times(:) - min(arr_times))*1e12;
  % Scatter heat
  figure('Color','w');
  scatter(XY(:,1), XY(:,2), 120, Tps, 'filled'); colorbar
  axis equal tight
  xlabel('x (um)'); ylabel('y (um)'); title('Arrival heatmap (ps offset)');
  exportgraphics(gcf, fname, 'Resolution', 200);
end
