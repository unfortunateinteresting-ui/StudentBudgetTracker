$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$runnerScript = Join-Path $PSScriptRoot "run-windows-e2e.ps1"

$scenarios = @(
    @{
        Name = "desktop-smoke"
        Spec = ".\\e2e-tests\\specs\\desktop-smoke.e2e.mjs"
        Seed = $null
    },
    @{
        Name = "legacy-migration"
        Spec = ".\\e2e-tests\\specs\\legacy-migration.e2e.mjs"
        Seed = "legacy_fixture"
    },
    @{
        Name = "backup-undo"
        Spec = ".\\e2e-tests\\specs\\backup-undo.e2e.mjs"
        Seed = $null
    },
    @{
        Name = "recurring-catchup"
        Spec = ".\\e2e-tests\\specs\\recurring-catchup.e2e.mjs"
        Seed = "missed_recurring"
    },
    @{
        Name = "recovery"
        Spec = ".\\e2e-tests\\specs\\recovery.e2e.mjs"
        Seed = "corrupt_with_backup"
    }
)

Push-Location $repoRoot
try {
    $first = $true
    foreach ($scenario in $scenarios) {
        Write-Host "Running E2E scenario: $($scenario.Name)"

        $env:E2E_SPEC_GLOB = $scenario.Spec
        if ($scenario.Seed) {
            $env:E2E_SEED_MODE = $scenario.Seed
        }
        else {
            Remove-Item Env:E2E_SEED_MODE -ErrorAction SilentlyContinue
        }

        if ($first) {
            Remove-Item Env:E2E_SKIP_BUILD -ErrorAction SilentlyContinue
        }
        else {
            $env:E2E_SKIP_BUILD = "1"
        }

        powershell -ExecutionPolicy Bypass -File $runnerScript

        if ($LASTEXITCODE -ne 0) {
            throw "Scenario failed: $($scenario.Name)"
        }

        $first = $false
    }
}
finally {
    Remove-Item Env:E2E_SPEC_GLOB -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_SEED_MODE -ErrorAction SilentlyContinue
    Remove-Item Env:E2E_SKIP_BUILD -ErrorAction SilentlyContinue
    Pop-Location
}
