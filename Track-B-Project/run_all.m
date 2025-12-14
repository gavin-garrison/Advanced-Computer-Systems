
% One-click pipeline
P = params();
T = sweep_pr(P);
disp('Uniform sweep results:');
disp(T);
fprintf('Outputs written to %s\n', P.outdir);
