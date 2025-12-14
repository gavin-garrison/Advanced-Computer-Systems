function export_heatmap(P, topo, arr_times, fname)
%EXPORT_HEATMAP Heat map of per-region arrival times (ps offset).
%   P         : params struct
%   topo      : topology struct (with topo.sinks, topo.taps)
%   arr_times : 1xN or Nx1 numeric vector of arrival times (seconds)
%   fname     : output filename for exportgraphics

  nR = numel(topo.sinks);

  % Region coordinates (tap centers)
  XY = zeros(nR,2);
  for r = 1:nR
      tap = topo.taps(r);
      XY(r,:) = [tap.x, tap.y];
  end

  % Ensure a numeric, nR×1 color vector even with NaNs
  arr = arr_times(:);
  arr = arr(1:nR);                  % guard against size drift
  finite = isfinite(arr);

  if any(finite)
      base = min(arr(finite));
      Tps  = (arr - base) * 1e12;   % ps offset from earliest
      maxv = max(Tps(finite));
      % mark missing as “late”
      Tps(~finite) = maxv + 10;
  else
      % all missing → flat color
      Tps = zeros(nR,1);
  end

  % Plot
  f = figure('Color','w');
  scatter(XY(:,1), XY(:,2), 120, Tps, 'filled');
  colormap(f, parula);
  cb = colorbar;
  cb.Label.String = 'Arrival offset (ps)';
  axis equal tight
  xlabel('x (µm)');
  ylabel('y (µm)');
  title('Clock arrival heatmap (ps offset from earliest)');

  if nargin >= 4 && ~isempty(fname)
      exportgraphics(f, fname, 'Resolution', 200);
      close(f);
  end
end
