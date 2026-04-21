$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$tauriDriverPath = Join-Path $HOME ".cargo\\bin\\tauri-driver.exe"
$edgeDriverAlias = Join-Path $env:LOCALAPPDATA "Microsoft\\WinGet\\Links\\msedgedriver.exe"

if (-not (Test-Path $tauriDriverPath)) {
    Write-Host "Installing tauri-driver..."
    cargo install tauri-driver --locked
}

if (-not (Test-Path $edgeDriverAlias)) {
    Write-Host "Installing Microsoft Edge WebDriver..."
    winget install --id Microsoft.EdgeDriver --silent --accept-package-agreements --accept-source-agreements
}

if (-not (Test-Path $edgeDriverAlias)) {
    throw "msedgedriver.exe was not found at $edgeDriverAlias after installation."
}

$env:TAURI_DRIVER_PATH = $tauriDriverPath
$env:MSEDGEDRIVER_PATH = $edgeDriverAlias

Push-Location $repoRoot
try {
    corepack.cmd pnpm wdio run .\\e2e-tests\\wdio.conf.mjs
    if ($LASTEXITCODE -ne 0) {
        throw "WDIO exited with code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
