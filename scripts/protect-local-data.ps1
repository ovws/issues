$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name

$directories = @(
    (Join-Path $projectRoot 'config'),
    (Join-Path $projectRoot 'data'),
    (Join-Path $projectRoot 'logs'),
    (Join-Path $projectRoot 'upstream\grok2api\data'),
    (Join-Path $projectRoot 'upstream\chatgpt2api\data')
)
$files = @(
    (Join-Path $projectRoot '.env'),
    (Join-Path $projectRoot 'config\gemini-cookies.local.json'),
    (Join-Path $projectRoot 'upstream\grok2api\config.yaml')
)

foreach ($path in $directories) {
    if (-not (Test-Path -LiteralPath $path)) { continue }
    & icacls.exe $path /inheritance:r /grant:r `
        "${currentUser}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' /T /C | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to protect directory: $path" }
}
foreach ($path in $files) {
    if (-not (Test-Path -LiteralPath $path)) { continue }
    & icacls.exe $path /inheritance:r /grant:r `
        "${currentUser}:F" '*S-1-5-18:F' '*S-1-5-32-544:F' /C | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to protect file: $path" }
}
Write-Host 'Restricted local credentials, data and logs to the current user, SYSTEM and Administrators.'

