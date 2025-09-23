param([string]$OutCsv = ".\results_ascii.csv")
if (-not (Test-Path $OutCsv)) {
  'kernel,dtype,N,stride,misalign,tail,median_ms,p10_ms,p90_ms,gflops,gibps,cpe,label,hint,check' |
    Out-File -Encoding ascii $OutCsv
}
$builds = @(
  @('.\cmake-build-scalar\project_1.exe','SCALAR'),
  @('.\cmake-build-release\project_1.exe','AUTO'),
  @('.\cmake-build-avx2\project_1.exe','AVX2')
)
$kernels = 'saxpy','dot','mul'
$dtypes  = 'f32','f64'
foreach ($k in $kernels) {
  foreach ($t in $dtypes) {
    foreach ($b in $builds) {
      $exe,$mode = $b
      foreach ($tj in 0,1) {
        $line = & $exe --kernel $k --dtype $t --N 1048576 --reps 11 --warmup 3 --no-header `
                       --stride 1 --misalign 0 --tail_jagged $tj --label tail
        if ($LASTEXITCODE -eq 0 -and $line) {
          [Text.Encoding]::ASCII.GetString([Text.Encoding]::ASCII.GetBytes($line)) |
            Tee-Object -Append $OutCsv | Out-Null
        }
      }
    }
  }
}
Write-Host "Tail sweep done. Output: $OutCsv" -ForegroundColor Cyan
