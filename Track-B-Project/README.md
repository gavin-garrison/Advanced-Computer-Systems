Overview

Clock distribution is a dominant contributor to power consumption, timing uncertainty, and robustness challenges in modern multi-GHz system-on-chip designs. Traditional clock distribution topologies represent two opposing extremes. H-trees are power-efficient and geometrically simple but increasingly sensitive to resistive imbalance and process variation. Clock meshes provide excellent skew robustness by averaging delays across many paths, but they incur significant dynamic power and routing overhead.

This project investigates a hybrid clock distribution architecture that combines a global H-tree backbone with localized clock meshes inside tiled regions of the die. The density of the local mesh is controlled by a single parameter, p_r ∈ [0, 1], which allows the design to smoothly interpolate between a pure tree and a dense mesh. In addition to uniform hybrid designs, this framework supports region-adaptive meshing, where local mesh density is redistributed based on clock arrival lateness while maintaining a fixed global budget.

The goal of this work is to quantify the skew, power, and robustness tradeoffs of hybrid clock networks using a reproducible analytical RC modeling framework, and to determine how much meshing is actually required to achieve near-optimal performance.

Motivation and Fit with Track B

Clock networks are a canonical example of a system where architectural decisions directly interact with physical effects. Choices made at the architectural level strongly influence clock power, skew, and robustness long before detailed physical design or signoff analysis begins.

This project aligns strongly with Track B by emphasizing:

Architectural modeling of clock distribution topologies

Quantitative performance analysis of skew, power, and robustness

Algorithmic exploration of mesh density allocation

Reproducible simulation methodology using analytical modeling

The work focuses on extracting architectural insight rather than signoff-level accuracy, making it suitable for early-stage design space exploration.

Research Plan and Scope
Background Research

Reviewed classical clock tree and clock mesh architectures

Studied hybrid clock networks used in high-performance processors

Surveyed analytical RC modeling techniques for clock simulation

Used open IRDS/ITRS-style parameters for advanced-node interconnect resistance and capacitance

Modeling and Simulation

Implemented an analytical RC clock network simulator using Modified Nodal Analysis (MNA)

Modeled a global H-tree feeding tiled regions across the die

Implemented local grid meshes within each region with tunable density p_r

Performed transient simulation to extract clock arrival times and skew

Estimated dynamic clock power using a CV²f formulation

Introduced Monte Carlo variation on interconnect R′, C′, and driver resistance

Analysis and Optimization

Swept uniform mesh density p_r ∈ [0, 1]

Evaluated region-adaptive meshing under a fixed average mesh budget

Generated skew–power Pareto fronts

Analyzed robustness using p95 and p99 skew metrics

Visualized spatial clock arrival behavior using heatmaps

Repository Structure
.
├── params.m              # Central configuration file
├── htree_build.m         # Global H-tree construction
├── gen_topology.m        # Full clock network topology generator
├── build_mna.m           # MNA matrix assembly
├── sim_transient.m       # Transient RC simulation
├── monte_carlo.m         # Monte Carlo robustness analysis
├── adaptive_policy.m     # Region-adaptive mesh allocation
├── sweep_pr.m            # Main experiment driver
├── run_all.m             # One-command execution script
└── out/                  # Generated figures and result tables

Script Descriptions
params.m

Defines all global parameters used throughout the project, including clock frequency, supply voltage, driver resistance, interconnect resistance and capacitance per unit length, die dimensions, number of regions, simulation timestep, Monte Carlo variation magnitudes, and output directories. This file serves as the single configuration point for all experiments and enables reproducibility.

htree_build.m

Constructs the global H-tree backbone. The function recursively generates the hierarchical branching structure and computes the coordinates of regional tap points. These tap points define the interface between the global clock distribution and the regional meshes.

gen_topology.m

Generates the complete clock network topology given a vector of mesh density values p_r. The script instantiates H-tree edges and, for each region, builds a local grid mesh whose density scales with p_r. Clock sinks are placed and connected to the appropriate nodes. The output is a full list of nodes, edges, and sink definitions.

build_mna.m

Assembles the Modified Nodal Analysis system from the generated topology. The function builds sparse conductance and capacitance matrices by stamping resistive and capacitive elements for each wire segment. A Thevenin-equivalent driver is added at the root, and sink capacitances are attached at sink nodes. The resulting system captures the linear RC behavior of the clock network.

sim_transient.m

Performs implicit-Euler transient simulation of the clock network. At each timestep, the linear system is solved to obtain node voltages. Clock arrival times are extracted when sink voltages cross a fixed threshold corresponding to 50 percent of VDD. Clock skew is computed as the difference between the earliest and latest arrivals. Average dynamic clock power is also reported. Early-exit logic is used to improve runtime efficiency.

monte_carlo.m

Evaluates robustness under variation by repeatedly perturbing interconnect resistance, capacitance, and driver resistance. Each Monte Carlo trial runs a full transient simulation. The function collects skew samples and computes statistical metrics including mean, standard deviation, p95, and p99 skew.

adaptive_policy.m

Implements a region-adaptive mesh allocation policy. Nominal clock arrival lateness is used as a proxy for criticality, and mesh density is redistributed across regions while enforcing a fixed average mesh budget. This enables evaluation of adaptive hybrid designs without introducing circuit-level tuning.

sweep_pr.m

The main experiment driver. This script sweeps uniform mesh density values, runs nominal and Monte Carlo simulations, evaluates region-adaptive designs, and generates all tables and figures used in the analysis. Results are written to CSV, MAT, and PNG files in the output directory.

Key Figures

All figures are generated automatically and saved in the out/ directory.

Skew–Power Pareto (Annotated)

File: pareto_annotated.png

Shows the tradeoff between dynamic clock power and p99 skew for H-tree, uniform hybrid, full mesh, and region-adaptive hybrid designs. Demonstrates orders-of-magnitude skew reduction with modest power increase and highlights diminishing returns beyond sparse meshing.

Skew vs Mesh Density

File: skew_vs_pr.png

Plots p99 skew as a function of uniform mesh density. Reveals a clear knee around p_r ≈ 0.25, indicating that most skew reduction is achieved at low mesh density.

Robustness Under Variation

File: robustness_skew_cdf.png

Shows cumulative distribution functions of skew under Monte Carlo variation. Highlights long skew tails for H-trees and tightly bounded distributions for hybrid designs.

Spatial Arrival Heatmaps

Files:

heat_uniform_pr0.25.png

heat_adapt_avgpr0.25.png

Visualize clock arrival offsets across the die for representative uniform and adaptive hybrid designs, confirming spatially uniform arrival behavior.

How This Project Meets Track B Requirements
Architectural Modeling

Explicit modeling of clock topology and hierarchy

Parameterized hybrid architecture

Clear separation between global and local distribution

Evidence: topology generation, architecture figures, modeling framework

Performance Analysis

Quantitative skew measurement

Dynamic power estimation

Robustness analysis using p95 and p99 metrics

Evidence: Pareto plots, skew distributions, Monte Carlo results

Algorithmic Design

Mesh density sweep

Region-adaptive allocation policy

Budget-constrained optimization

Evidence: adaptive policy implementation and comparisons

Reproducible Methodology

Centralized configuration

Modular scripts

One-command execution

Evidence: params.m, run_all.m, structured outputs

Key Findings

Sparse hybrid meshing reduces clock skew by more than three orders of magnitude relative to an H-tree

Most skew reduction occurs at low mesh density (p_r ≈ 0.25)

Dense meshing yields diminishing returns while increasing power

Hybrid designs strongly suppress skew tails under variation

Region-adaptive meshing matches uniform hybrid performance in symmetric layouts

Adaptivity is most promising for asymmetric or heterogeneous designs
