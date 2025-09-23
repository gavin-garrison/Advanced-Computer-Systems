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
$kernels = 'saxpy','dot','mul','stencil'
$dtypes  = 'f32','f64'
$strides = 1,2,4,8,16,32
foreach ($k in $kernels) {
  foreach ($t in $dtypes) {
    foreach ($b in $builds) {
      $exe,$mode = $b
      foreach ($s in $strides) {
        $line = & $exe --kernel $k --dtype $t --N 1048576 --reps 9 --warmup 3 --no-header `
                       --stride $s --misalign 0 --tail_jagged 0 --label stride
        if ($LASTEXITCODE -eq 0 -and $line) {
          [Text.Encoding]::ASCII.GetString([Text.Encoding]::ASCII.GetBytes($line)) |
            Tee-Object -Append $OutCsv | Out-Null
        }
      }
    }
  }
}
Write-Host "Stride sweep done. Output: $OutCsv" -ForegroundColor Cyan
