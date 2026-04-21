$ErrorActionPreference = "Stop"

$defaultLegacyPath = Join-Path $env:APPDATA "OfflineBudgetTracker\budget.db"
$legacyPath = if ($env:REAL_LEGACY_DB_PATH) { $env:REAL_LEGACY_DB_PATH } else { $defaultLegacyPath }

if (-not (Test-Path $legacyPath)) {
    throw "Legacy database not found at $legacyPath"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:REAL_LEGACY_DB_PATH = (Resolve-Path $legacyPath).Path

Push-Location $repoRoot
try {
    cargo test --manifest-path src-tauri/Cargo.toml manual_real_legacy_db_validation -- --ignored --nocapture
}
finally {
    Pop-Location
}
