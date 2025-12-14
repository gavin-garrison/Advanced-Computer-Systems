function out = sim_transient(P, net)
%SIM_TRANSIENT Implicit Euler transient with early-exit and optional waveforms.
%   - Fast mode (default): only computes arrival times, skew, latency, Pavg.
%   - Full mode (P.store_waveforms=true): also stores t, Vroot, Vs for plotting.

  N = size(net.G,1);

  % --------- Options ---------
  store_waveforms = isfield(P,'store_waveforms') && P.store_waveforms;

  % Max extra time beyond P.Tstop for very slow sinks
  max_extra_time = 10.0 / P.freq;

  % Total max time horizon and steps (no dynamic growth)
  Tmax   = P.Tstop + max_extra_time;
  nsteps = max(2, ceil(Tmax / P.dt));
  t_vec  = (1:nsteps).' * P.dt;

  % --------- Pre-factorization (SPD -> chol, else LU) ---------
  Cd = net.C * (1/P.dt);
  A  = Cd + net.G;

  try
      F = decomposition(A,'chol');   % faster if A is SPD
  catch
      F = decomposition(A,'lu');     % fallback if not
  end

  v = zeros(N,1);

  root     = net.root;
  sink_idx = net.sink_indices(:);   % column
  nsinks   = numel(sink_idx);

  % Preallocate if storing waveforms
  if store_waveforms
      Vroot  = zeros(nsteps,1);
      Vsinks = zeros(nsteps,nsinks);
  else
      Vroot  = [];
      Vsinks = [];
  end

  % For arrival detection
  arr        = NaN(nsinks,1);        % column for convenience
  crossed    = false(nsinks,1);      % *** column, matches vs ***
  prev_vs    = zeros(nsinks,1);
  prev_t     = 0;

  guard_after_all = 100;
  guard_counter   = 0;
  last_step       = nsteps;

  % --------- Main transient loop ---------
  for k = 1:nsteps
      rhs = Cd*v + net.b;
      v   = F \ rhs;

      tk  = t_vec(k);
      vs  = v(sink_idx);            % nsinks x 1

      if store_waveforms
          Vroot(k)    = v(root);
          Vsinks(k,:) = vs.';       % row
      end

      % Arrival detection (per sink, linear interpolation)
      newly_crossed = (vs >= P.vth) & ~crossed;   % all column vectors
      idx_new       = find(newly_crossed);

      if ~isempty(idx_new)
          for ii = 1:numel(idx_new)
              s  = idx_new(ii);
              v0 = prev_vs(s);
              v1 = vs(s);
              if v1 == v0
                  arr(s) = tk;
              else
                  t0     = prev_t;
                  t1     = tk;
                  arr(s) = t0 + (P.vth - v0) * (t1 - t0) / (v1 - v0);
              end
          end
      end

      crossed = crossed | newly_crossed;

      % Update previous for next step
      prev_vs = vs;
      prev_t  = tk;

      % Early exit once *all* sinks have arrival times
      if all(crossed)
          guard_counter = guard_counter + 1;
          if guard_counter >= guard_after_all
              last_step = k;
              break;
          end
      end
  end

  % Trim waveforms if we exited early
  if store_waveforms
      t_out  = t_vec(1:last_step);
      Vroot  = Vroot(1:last_step,:);
      Vsinks = Vsinks(1:last_step,:);
  else
      t_out  = [];
  end

  % --------- Skew / latency ---------
  finite = arr(isfinite(arr));
  if isempty(finite)
      skew    = NaN;
      latency = NaN;
  else
      skew    = max(finite) - min(finite);
      latency = mean(finite);
  end

  % --------- Power (CV^2f) ---------
  if isfield(net,'Csw')
      Csw = net.Csw;
  else
      Csw = full(sum(diag(net.C)));
  end
  Pavg = Csw * P.VDD^2 * P.freq;

  % --------- Outputs ---------
  out.t       = t_out;
  out.Vroot   = Vroot;
  out.Vs      = Vsinks;
  out.arr     = arr.';      % return as row, like before
  out.skew    = skew;
  out.latency = latency;
  out.Pavg    = Pavg;
end
