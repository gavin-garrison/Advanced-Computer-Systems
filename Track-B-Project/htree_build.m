function [taps, edges] = htree_build(P)
%HTREE_BUILD
% Build 4^levels regions. Each tap is the region center.
% Edges: single Manhattan run from 'root' to each tap (positive length).

  die = P.die_um;
  taps  = [];
  edges = {};
  rid   = 0;

  function rec(x0,y0,w,h,lvl)
    if lvl==0
      rid = rid + 1;
      cx = x0 + w/2; cy = y0 + h/2;
      name = sprintf('tap_r%d', rid);
      taps = [taps; struct('name',name,'x',cx,'y',cy,'w',w,'h',h,'region_id',rid)]; %#ok<AGROW>
      Lmh = abs(cx - die/2) + abs(cy - die/2);
      if Lmh < 1e-6, Lmh = 1.0; end               % ensure positive length
      edges(end+1,:) = {'root', name, Lmh, 'tree'}; %#ok<AGROW>
      return
    end
    w2=w/2; h2=h/2;
    rec(x0,    y0,    w2,h2,lvl-1);
    rec(x0+w2, y0,    w2,h2,lvl-1);
    rec(x0,    y0+h2, w2,h2,lvl-1);
    rec(x0+w2, y0+h2, w2,h2,lvl-1);
  end

  rec(0,0, die, die, P.levels);
end
