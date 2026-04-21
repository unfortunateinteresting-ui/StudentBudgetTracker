param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $projectRoot "dist-web"
$releaseDir = Join-Path $projectRoot "src-tauri\target\release"
$bundleDir = Join-Path $releaseDir "bundle\nsis"
$releaseCandidates = @(
    (Join-Path $releaseDir "StudentBudgetTracker.exe"),
    (Join-Path $releaseDir "student-budget-tracker.exe")
)

if ($Clean) {
    foreach ($target in @($distDir, $releaseDir)) {
        if (Test-Path $target) {
            Remove-Item -LiteralPath $target -Recurse -Force
        }
    }
}

Push-Location $projectRoot
try {
    corepack pnpm tauri:build

    $builtExe = $releaseCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    $installer = Get-ChildItem -LiteralPath $bundleDir -Filter *.exe -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    Write-Host ""
    Write-Host "Build complete:"
    if (Test-Path $builtExe) {
        Write-Host "  EXE: $builtExe"
    }
    if ($installer) {
        Write-Host "  Installer: $($installer.FullName)"
    }
}
finally {
    Pop-Location
}
