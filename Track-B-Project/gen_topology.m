function topo = gen_topology(P, pr_map)
%GEN_TOPOLOGY Generate H-tree taps and per-region meshes according to pr_map.
% Returns:
%   topo.edges    : {a, b, L_um, layer} rows (layer in {'tree','mesh'})
%   topo.sinks    : cell array of sink node names (one per region)
%   topo.nodes_xy : containers.Map(name -> [x y] µm)
%   topo.taps     : struct array from htree_build (name,x,y,w,h,region_id)
%   topo.Csink_r  : per-region sink caps (F)  [NEW]
%   topo.weights  : per-region criticality weights [NEW]

  % ---- H-tree taps and trunk edges (root -> tap) ----
  [taps, edges_tree] = htree_build(P);     % each tap: .name .x .y .w .h .region_id
  edges    = edges_tree;
  nodes_xy = containers.Map();
  nodes_xy('root') = [P.die_um/2, P.die_um/2];

  % Record tap coordinates up-front
  for i = 1:numel(taps)
    nodes_xy(taps(i).name) = [taps(i).x, taps(i).y];
  end

  % ---- pr_map sanity ----
  nR = numel(taps);
  if isscalar(pr_map)
    pr_map = repmat(pr_map, nR, 1);
  elseif numel(pr_map) ~= nR
    error('gen_topology:pr_map_len', ...
      'pr_map length (%d) does not match number of regions (%d).', numel(pr_map), nR);
  end
  pr_map = max(0, min(1, pr_map));   % clamp

  % ---- Per-region sink caps (Csink_r) & weights (w_r) ----
  % Default: constant Csink and unit weights
  Csink_r = P.Csink * ones(nR,1);
  switch lower(getfield_with_default(P,'Csink_map','const'))
    case 'lognormal'
      % Toolbox-free LogNormal sampler: exp(mu + sigma*randn)
      mu = getfield_with_default(P,'Csink_mu', log(P.Csink));   % log-space mean
      sg = getfield_with_default(P,'Csink_sigma', 0.4);         % log-space std
      Csink_r = exp(mu + sg.*randn(nR,1));
    case 'bimodal'
      p  = 0.35; a = 0.6*P.Csink; b = 2.0*P.Csink;
      m  = rand(nR,1) < p;
      Csink_r(m)  = a;
      Csink_r(~m) = b;
    case 'const'
      % keep defaults
  end

  w_r = ones(nR,1);
  switch lower(getfield_with_default(P,'weight_map','uniform'))
    case 'hotspot'
      rng(42);                        % reproducible “hot” clusters
      kHot = min( max(2, round(sqrt(nR)/2)), 6 );
      hot  = randperm(nR, kHot);
      w_r(hot) = 3.0;                % weight hot regions more
    case 'uniform'
      % do nothing
  end

  % ---- Per-region meshes (optional) ----
  sinks = cell(nR,1);
  for r = 1:nR
    pr  = pr_map(r);
    tap = taps(r).name;
    ctr = [taps(r).x, taps(r).y];

    if pr <= 0
      % Pure H-tree in this region: sink is the tap (no floating nodes)
      sinks{r} = tap;
      continue
    end

    % Build a region-wide mesh and connect it
    reg_w = taps(r).w;              % region width (µm)
    reg_h = taps(r).h;              % region height (µm)
    M = region_mesh(ctr, reg_w, reg_h, P, pr, r);

    % Record mesh nodes (coordinates)
    for k = 1:numel(M.nodes)
      nodes_xy(M.nodes{k}) = M.xy(k,:);
    end

    % Add mesh edges
    for k = 1:size(M.edges,1)
      edges(end+1,:) = {M.edges{k,1}, M.edges{k,2}, M.edges{k,3}, 'mesh'}; %#ok<AGROW>
    end

    % Staple tap to central mesh node; guard zero-length staple
    lstaple = M.center_len_um;
    if ~(isfinite(lstaple)) || lstaple < 1e-6
      lstaple = 1.0;   % 1 µm stub ensures nonzero R and C for stamping
    end
    edges(end+1,:) = {tap, M.center_node, lstaple, 'mesh'}; %#ok<AGROW>

    % Sink is the central mesh node (well-connected representative)
    sinks{r} = M.center_node;
  end

  % ---- Optional: stitch adjacent regions to form a sparse global mesh ----
  do_stitch = isfield(P,'stitch_mesh') && P.stitch_mesh && any(pr_map(:) > 0);
  if do_stitch
    gridN = 2^P.levels;             % regions per axis
    % Build a grid index by sorting taps by (y,x)
    XY = zeros(nR,3);               % [x y idx]
    for i=1:nR, XY(i,:) = [taps(i).x, taps(i).y, i]; end
    [~,ord] = sortrows(XY(:,1:2), [2 1]); % sort by y, then x (row-major)
    idxs = XY(ord,3);
    if numel(idxs) ~= gridN*gridN
      warning('gen_topology:stitch_index','Unexpected region count vs grid.');
    end
    Tgrid = reshape(idxs, [gridN, gridN]);

    for rr = 1:gridN
      for cc = 1:gridN
        i = Tgrid(rr,cc);
        ni = sinks{i};                         % region i sink node

        % horizontal stitch to right neighbor
        if cc < gridN
          j  = Tgrid(rr,cc+1); nj = sinks{j};
          L  = abs(taps(i).x - taps(j).x);    % center-to-center x distance
          if ~(isfinite(L)) || L < 1e-6, L = 1.0; end
          edges(end+1,:) = {ni, nj, L, 'mesh'}; %#ok<AGROW>
        end
        % vertical stitch to upper neighbor
        if rr < gridN
          j  = Tgrid(rr+1,cc); nj = sinks{j};
          L  = abs(taps(i).y - taps(j).y);    % center-to-center y distance
          if ~(isfinite(L)) || L < 1e-6, L = 1.0; end
          edges(end+1,:) = {ni, nj, L, 'mesh'}; %#ok<AGROW>
        end
      end
    end
  end

  % ---- Package topology ----
  topo.edges    = edges;
  topo.sinks    = sinks;
  topo.nodes_xy = nodes_xy;
  topo.taps     = taps;
  topo.Csink_r  = Csink_r;   % NEW
  topo.weights  = w_r;       % NEW
end

% --------- helpers ----------
function val = getfield_with_default(S, name, def)
  if isstruct(S) && isfield(S, name), val = S.(name); else, val = def; end
end
