param(
    [string]$SdkDir = "$env:LOCALAPPDATA\Android\Sdk"
)

Write-Host "Installing Android Studio via winget..."
winget install --id Google.AndroidStudio --accept-source-agreements --accept-package-agreements --disable-interactivity

if (!(Test-Path $SdkDir)) {
    Write-Warning "Android SDK directory not found yet: $SdkDir"
    Write-Host "Open Android Studio once and install SDK Platform + Build Tools, then rerun this script."
    exit 0
}

$localProps = Join-Path $PSScriptRoot "local.properties"
$escaped = $SdkDir.Replace('\\', '\\\\').Replace(':', '\\:')
"sdk.dir=$escaped" | Set-Content -NoNewline $localProps

Write-Host "Created $localProps"
Write-Host "Now run: .\gradlew.bat assembleDebug"