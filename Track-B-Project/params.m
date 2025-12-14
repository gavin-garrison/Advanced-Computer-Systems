function P = params()
%PARAMS Central configuration for the hybrid clock model (3 nm-ish).
% Units: length = µm, cap = F, resistance = Ω, freq = Hz.

  % ===== Mesh density settings =====
  % Keep some range, but avoid super-dense meshes while developing
  P.mesh_Nmin = 5;                 % allow coarse meshes
  P.mesh_Nmax = 11;                % was 13 → slightly fewer nodes

  % ===== Technology & clock =====
  P.VDD   = 0.65;                  % V
  P.freq  = 3.2e9;                 % Hz
  P.vth   = 0.5*P.VDD;             % 50% VDD arrival threshold

  % Use cheap CV²f power in sim_transient (no waveform integration)
  P.use_power_wave = false;        % was true → faster

  % ===== Effective interconnect per-µm =====
  P.Rp_tree = 0.055;               % Ω/µm
  P.Cp_tree = 0.20e-15;            % F/µm
  P.Rp_mesh = 0.030;               % Ω/µm
  P.Cp_mesh = 0.18e-15;            % F/µm

  % Width multipliers (area accounting only)
  P.k_tree = 4;
  P.k_mesh = 3;

  % ===== Drivers & sinks =====
  P.Rdrv   = 7;                    % Ω
  P.Csink  = 12e-15;               % F per sink

  % ===== Geometry & topology =====
  P.die_mm     = 10;
  P.die_um     = P.die_mm*1000;
  P.levels     = 3;                % 64 regions
  P.grid_n     = 4;                % for heatmaps
  P.pitch_min  = 40;               % µm
  P.pitch_max  = 350;              % µm
  P.staple_tap = true;

  % ===== “3 nm” variation (1-sigma) =====
  P.sig_Rp_global = 0.08;
  P.sig_Rp_reg    = 0.06;
  P.sig_Rp_local  = 0.05;
  P.sig_Cp_global = 0.04;
  P.sig_Cp_reg    = 0.03;
  P.sig_Cp_local  = 0.02;
  P.sig_Rdrv      = 0.12;

  % ===== Non-uniform sinks & criticality =====
  P.Csink_map    = 'lognormal';
  P.Csink_mu     = log(12e-15);
  P.Csink_sigma  = 0.5;
  P.weight_map   = 'hotspot';

  % ===== Budgets =====
  P.clockC_budget_factor = 1.80;
  P.wire_area_budget     = 1.15;
  P.stitch_budget_um     = 3.0e4;

  % ===== Time stepping (BIG speed lever) =====
  % Old: dt = 1e-13 (0.1 ps), Tstop = 6/f → ~50k steps / transient.
  % New: dt = 1e-12 (1 ps), Tstop = 2/f → ~3.7k steps / transient.
  P.dt    = 1e-12;                 % 1 ps (10× fewer steps than 0.1 ps)
  P.Tstop = 2.0 / P.freq;          % ~2 cycles; sim_transient can still extend if needed

  % ===== Monte-Carlo & sweeps (OTHER big lever) =====
  % Full accuracy setting:
  P.Nmc   = 200;                   % keep as your "final" target

  % Fast dev override (used by monte_carlo.m if present):
  P.Nmc_eff = 60;                  % ~60 samples per p_r for sweep_pr (3× faster MC)

  % Keep 5 p_r points for shape; Nmc reduction + dt/Tstop do the heavy lifting.
  P.pr_values  = linspace(0,1,5);  % uniform pr sweep

  P.adaptive     = true;
  P.adapt_alpha  = 1.2;
  P.adapt_min    = 0.05;
  P.adapt_budget = 1.0;

  % Stitching between regions is the winning knob
  P.stitch_mesh = true;

  % ===== Waveform storage flag (for sim_transient) =====
  % FAST: don't store waveforms during run_all / MC.
  P.store_waveforms = false;

  % When you want nice plots for ONE config:
  %   set P.store_waveforms = true; P.Nmc_eff = 1; P.Nmc = 1; and call sim_transient once.

  % ===== Plots & export =====
  P.outdir = 'out';
  if ~exist(P.outdir,'dir'), mkdir(P.outdir); end
end
