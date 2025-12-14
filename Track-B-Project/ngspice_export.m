
function ngspice_export(sub_edges, P, fname)
%NGSPICE_EXPORT Export a small subgraph to NGSPICE netlist for validation.
% sub_edges: cell {n1,n2,Lum,layer}
% Writes an RC-only netlist with Vsrc + Rdrv -> root.

  fid = fopen(fname,'w');
  fprintf(fid, '* RC subgraph exported for NGSPICE\n');
  fprintf(fid, 'V1 root 0 %.3f\n', P.VDD);
  fprintf(fid, 'Rdrv root root_in %.3f\n', P.Rdrv);

  node_map = containers.Map();
  next = 1;
  function idx = idx_of(name)
    if ~isKey(node_map,name)
      node_map(name) = next; next=next+1;
    end
    idx = node_map(name);
  end

  for k=1:size(sub_edges,1)
    a = sub_edges{k,1}; b = sub_edges{k,2}; L=sub_edges{k,3}; layer=sub_edges{k,4};
    ia = idx_of(a); ib = idx_of(b);
    if strcmp(layer,'tree'), Rp=P.Rp_tree; Cp=P.Cp_tree; else, Rp=P.Rp_mesh; Cp=P.Cp_mesh; end
    R = Rp*L; C = Cp*L;
    fprintf(fid,'R%d n%d n%d %.6f\n', k, ia, ib, R);
    fprintf(fid,'C%da n%d 0 %.6ea\n', k, ia, 0.5*C);
    fprintf(fid,'C%db n%d 0 %.6ea\n', k, ib, 0.5*C);
  end
  fclose(fid);
end
