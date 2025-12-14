function net = build_mna(P, topo)
%BUILD_MNA Assemble sparse G, C, and b from topology and parameters.

  % ---- Build a complete, ordered name list ----
  nameSet = containers.Map('KeyType','char','ValueType','logical');

  % from nodes_xy
  nk = topo.nodes_xy.keys;
  for i = 1:numel(nk), nameSet(nk{i}) = true; end

  % ensure root exists
  if ~isKey(topo.nodes_xy,'root')
      topo.nodes_xy('root') = [P.die_um/2, P.die_um/2];
      nameSet('root') = true;
  else
      nameSet('root') = true;
  end

  % from edges
  for e = 1:size(topo.edges,1)
    nameSet(topo.edges{e,1}) = true;
    nameSet(topo.edges{e,2}) = true;
  end

  % from sinks (aliases)
  for r = 1:numel(topo.sinks)
    nameSet(topo.sinks{r}) = true;
  end

  % finalize ordered names (stable sort)
  allNames = nameSet.keys;
  [~,ord]  = sort(allNames);
  names    = allNames(ord);
  N        = numel(names);
  index    = containers.Map(names, num2cell(1:N));

  % ---- Stamp G and C ----
  I = []; J = []; Vg = [];
  Ic = []; Jc = []; Vc = [];

  C_total = 0;  % accumulate total switching capacitance

  function add_res(a,b,R)
    if R <= 0, return; end
    g = 1/R;
    I  = [I,  a,  b,  a,  b]; %#ok<AGROW>
    J  = [J,  a,  b,  b,  a]; %#ok<AGROW>
    Vg = [Vg, g,  g, -g, -g]; %#ok<AGROW>
  end

  function add_cap(a,C)
    if C <= 0, return; end
    Ic = [Ic, a]; %#ok<AGROW>
    Jc = [Jc, a]; %#ok<AGROW>
    Vc = [Vc, C]; %#ok<AGROW>
    C_total = C_total + C;
  end

  % per-layer R', C'
  for e = 1:size(topo.edges,1)
    a     = index(topo.edges{e,1});
    b     = index(topo.edges{e,2});
    L     = topo.edges{e,3};   % µm
    layer = topo.edges{e,4};

    if strcmp(layer,'tree')
      Rp = P.Rp_tree; Cp = P.Cp_tree;
    else
      Rp = P.Rp_mesh; Cp = P.Cp_mesh;
    end

    if L > 0
      R    = Rp * L;
      Cseg = Cp * L;
      add_res(a,b,R);
      add_cap(a, 0.5*Cseg);
      add_cap(b, 0.5*Cseg);
    end
  end

  % Sinks: attach Csink; prefer per-region Csink_r if available
  use_per_region = isfield(topo,'Csink_r') && ...
                   numel(topo.Csink_r) == numel(topo.sinks);

  for r = 1:numel(topo.sinks)
    sname = topo.sinks{r};
    if isKey(index, sname)
      sidx = index(sname);
    else
      sidx = index(sprintf('tap_r%d', r));
    end
    if use_per_region, Cs = topo.Csink_r(r); else, Cs = P.Csink; end
    add_cap(sidx, Cs);
  end

  % Build sparse matrices
  G = sparse(I,J,Vg,N,N);
  C = sparse(Ic,Jc,Vc,N,N);

  % Thevenin driver at root
  b    = sparse(N,1);
  root = index('root');
  gdrv = 1/max(P.Rdrv, eps);
  G(root,root) = G(root,root) + gdrv;
  b(root)      = b(root) + gdrv*P.VDD;

  % Package
  net.G          = G;
  net.C          = C;
  net.b          = b;
  net.index      = index;
  net.names      = names;
  net.root       = root;
  net.sink_indices = sink_indices(index, topo);
  net.Csw        = C_total;   % <--- used by sim_transient
end

function sidx = sink_indices(index, topo)
  sidx = zeros(numel(topo.sinks),1);
  for r = 1:numel(topo.sinks)
    sname = topo.sinks{r};
    if isKey(index, sname)
      sidx(r) = index(sname);
    else
      sidx(r) = index(sprintf('tap_r%d', r));
    end
  end
end
