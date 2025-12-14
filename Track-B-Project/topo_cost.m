function cost = topo_cost(P, topo)
% Return clock capacitance, wire area, and stitch length for budget checks.
  totalC = 0; area  = 0; Lstitch = 0;
  for e = 1:size(topo.edges,1)
    L = topo.edges{e,3}; layer = topo.edges{e,4};
    if strcmp(layer,'tree')
      totalC = totalC + P.Cp_tree*L;
      area   = area   + (P.k_tree)*L;   % width units (relative)
    else
      totalC = totalC + P.Cp_mesh*L;
      area   = area   + (P.k_mesh)*L;
      % Heuristic: stitches are mesh edges whose endpoints are in different regions
      a = topo.edges{e,1}; b = topo.edges{e,2};
      if startsWith(a,'tap_r') && startsWith(b,'tap_r') && ~strcmp(a,b)
        Lstitch = Lstitch + L;
      end
    end
  end
  % include sink caps
  if isfield(topo,'Csink_r')
    totalC = totalC + sum(topo.Csink_r);
  else
    totalC = totalC + numel(topo.sinks)*P.Csink;
  end
  cost.C_total   = totalC;
  cost.A_wire    = area;
  cost.L_stitch  = Lstitch;
end
