param(
  [string]$OutCsv = ".\results_ascii.csv"
)

# 1) Ensure CSV header
if (-not (Test-Path $OutCsv)) {
  'kernel,dtype,N,stride,misalign,tail,median_ms,p10_ms,p90_ms,gflops,gibps,cpe,label,hint,check' |
    Out-File -Encoding ascii $OutCsv
}

# 2) Executables: SCALAR, AUTO (release), AVX2
$builds = @(
  @('.\cmake-build-scalar\project_1.exe','SCALAR'),
  @('.\cmake-build-release\project_1.exe','AUTO'),
  @('.\cmake-build-avx2\project_1.exe','AVX2')
)

# Sanity check exes exist
$missing = @()
foreach ($b in $builds) {
  if (-not (Test-Path $b[0])) { $missing += $b[0] }
}
if ($missing.Count -gt 0) {
  Write-Host "ERROR: missing exe(s):" -ForegroundColor Red
  $missing | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
  exit 1
}

# 3) Workloads & sizes (2^13 .. 2^23)
$kernels = 'saxpy','dot','mul','stencil'
$dtypes  = 'f32','f64'
$Ns = 13..23 | ForEach-Object { [int]([math]::Pow(2,$_)) }

# 4) Run & append ASCII-safe lines
foreach ($k in $kernels) {
  foreach ($t in $dtypes) {
    foreach ($b in $builds) {
      $exe,$mode = $b
      foreach ($N in $Ns) {
        $line = & $exe --kernel $k --dtype $t --N $N --reps 7 --warmup 2 --no-header `
                       --stride 1 --misalign 0 --tail_jagged 0 --label unit
        if ($LASTEXITCODE -eq 0 -and $line) {
          # force ASCII to kill weird characters
          [Text.Encoding]::ASCII.GetString([Text.Encoding]::ASCII.GetBytes($line)) |
            Tee-Object -Append $OutCsv | Out-Null
          Write-Host "$mode $k $t N=$N  => ok"
        } else {
          Write-Host "$mode $k $t N=$N  => FAILED ($LASTEXITCODE)" -ForegroundColor Yellow
        }
      }
    }
  }
}
Write-Host "Locality sweep done. Output: $OutCsv" -ForegroundColor Cyan
