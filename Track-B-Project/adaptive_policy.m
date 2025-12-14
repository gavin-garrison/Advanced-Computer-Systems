function pr_map = adaptive_policy(P, topo0, arr0, pr_avg)
% BUDGETED adaptive allocation:
%  - same average p_r as uniform (pr_avg)
%  - minimize phase variance (weighted) as a proxy for p99 skew
%  - respect global budgets on clock C, wire area, stitch length

  nR = numel(topo0.sinks);
  pr_map = max(P.adapt_min, min(1, pr_avg*ones(nR,1)));

  % Baseline budgets from uniform at pr_avg
  topoU = gen_topology(P, pr_map);
  costU = topo_cost(P, topoU);
  C_cap = P.clockC_budget_factor * costU.C_total;    % allow ×factor of tree? can also lock to costU
  A_cap = P.wire_area_budget     * costU.A_wire;
  L_cap = P.stitch_budget_um;

  % Fast-sim settings for inner loops
  Pf = P; Pf.Nmc = 0; Pf.use_power_wave = false; Pf.Tstop = 2.5/P.freq;

  K = 6;                     % outer iterations
  delta = 0.12;              % step in pr per move
  for it = 1:K
    % Evaluate proxy objective: weighted variance of arrivals
    topo = gen_topology(Pf, pr_map);
    net  = build_mna(Pf, topo);
    out  = sim_transient(Pf, net);
    w    = topo.weights(:); w = w/sum(w);
    obj0 = sum( w .* (out.arr(:) - sum(w.*out.arr(:))) .^ 2 );

    % For each region, estimate gradient d(obj)/d(pr_r) by +delta
    g = zeros(nR,1); dC = zeros(nR,1); dA = zeros(nR,1);
    parfor r = 1:nR          % parfor OK; if no PCT, MATLAB will run serially
      pr_try = pr_map; pr_try(r) = min(1, pr_try(r)+delta);
      topoT = gen_topology(Pf, pr_try);
      netT  = build_mna(Pf, topoT);
      outT  = sim_transient(Pf, netT);
      wT    = topoT.weights(:); wT = wT/sum(wT);
      objT  = sum( wT .* (outT.arr(:) - sum(wT.*outT.arr(:))) .^ 2 );
      g(r)  = (objT - obj0)/delta;
      costT = topo_cost(P, topoT);
      dC(r) = costT.C_total - costU.C_total;
      dA(r) = costT.A_wire  - costU.A_wire;
    end

    % Rank by "benefit per added cap/area" (more negative grad is better)
    score = -g ./ max(1e-18, (abs(dC)+0.5*abs(dA)));   % tunable weighting

    % Move density from worst to best while keeping average & budgets
    [~, idx_gain] = sort(score, 'descend');
    [~, idx_lose] = sort(score, 'ascend');
    moves = min(ceil(nR/3), 6);                        % move a subset each iter
    pr_new = pr_map;

    for k = 1:moves
      i = idx_gain(k);  j = idx_lose(k);
      step = delta;
      pr_new(i) = min(1, pr_new(i) + step);
      pr_new(j) = max(P.adapt_min, pr_new(j) - step);
    end

    % Re-center to exactly match avg budget
    s = mean(pr_new) - pr_avg;
    if abs(s) > 1e-6
      pr_new = pr_new - s;
      pr_new = max(P.adapt_min, min(1, pr_new));
    end

    % Enforce global budgets (softly): if over, scale down toward uniform
    topoN = gen_topology(P, pr_new);
    costN = topo_cost(P, topoN);
    overC = costN.C_total > C_cap;
    overA = costN.A_wire  > A_cap;
    overL = costN.L_stitch> L_cap;
    if overC || overA || overL
      pr_new = 0.7*pr_new + 0.3*(pr_avg*ones(nR,1));  % pull back
    end

    pr_map = pr_new;
  end
end
