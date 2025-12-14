function M = region_mesh(center_xy, reg_w, reg_h, P, pr, region_id)
%REGION_MESH Mesh covering the full region; density via line counts (Nx, Ny).
% pr in [0,1] maps to Nx,Ny in [P.mesh_Nmin, P.mesh_Nmax].
% Returns:
%   nodes {names}, xy [N x 2], edges {a,b,Lum,'mesh'}, center_node, center_len_um

  % Choose grid counts from density
  Nx = max(2, round(P.mesh_Nmin + pr*(P.mesh_Nmax - P.mesh_Nmin)));
  Ny = max(2, round(P.mesh_Nmin + pr*(P.mesh_Nmax - P.mesh_Nmin)));

  % Span the region with a small margin so staples are short
  span_x = 0.9 * reg_w;   % 90% of region width
  span_y = 0.9 * reg_h;

  x0 = center_xy(1) - span_x/2;
  y0 = center_xy(2) - span_y/2;
  dx = span_x / (Nx - 1);
  dy = span_y / (Ny - 1);

  % Allocate nodes
  nodes = cell(Nx*Ny, 1);
  xy    = zeros(Nx*Ny, 2);
  k = 0;
  for ix = 1:Nx
    for iy = 1:Ny
      k = k + 1;
      x = x0 + (ix-1)*dx;
      y = y0 + (iy-1)*dy;
      nodes{k} = sprintf('mesh_r%d_%d_%d', region_id, ix, iy);
      xy(k,:)  = [x, y];
    end
  end

  % 4-neighbor edges; lengths in µm
  edges = {};
  for ix = 1:Nx
    for iy = 1:Ny
      idx = (ix-1)*Ny + iy;
      if ix < Nx
        idx2 = ix*Ny + iy;
        edges(end+1,:) = {nodes{idx}, nodes{idx2}, dx, 'mesh'}; %#ok<AGROW>
      end
      if iy < Ny
        idx2 = (ix-1)*Ny + (iy+1);
        edges(end+1,:) = {nodes{idx}, nodes{idx2}, dy, 'mesh'}; %#ok<AGROW>
      end
    end
  end

  % central node (closest to geometric center)
  [~, cidx]   = min(sum((xy - center_xy).^2, 2));
  center_node = nodes{cidx};
  center_len_um = sqrt(sum((xy(cidx,:) - center_xy).^2));

  M.nodes = nodes;
  M.xy = xy;
  M.edges = edges;
  M.center_node = center_node;
  M.center_len_um = center_len_um;
end
