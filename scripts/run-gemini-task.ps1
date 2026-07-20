Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$python = Get-RootPython
$hostAddress = Get-Setting 'INTERNAL_AI_HOST' '0.0.0.0'
$port = Get-Setting 'GEMINI_PORT' '8002'
$logDirectory = Join-Path $script:ProjectRoot 'logs\gemini'
$bootstrapLog = Join-Path $logDirectory 'task-bootstrap.log'

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
Set-Location -LiteralPath $script:ProjectRoot
try {
    Add-Content -LiteralPath $bootstrapLog -Encoding UTF8 `
        -Value "[$([DateTime]::UtcNow.ToString('o'))] Starting Gemini task as $env:USERNAME."
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $python -m uvicorn internal_ai_api.gemini_app:app `
        --host $hostAddress --port $port --env-file $script:EnvFile --no-access-log `
        1>> $bootstrapLog 2>&1
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorActionPreference
    Add-Content -LiteralPath $bootstrapLog -Encoding UTF8 `
        -Value "[$([DateTime]::UtcNow.ToString('o'))] Gemini task exited with code $exitCode."
    exit $exitCode
} catch {
    Add-Content -LiteralPath $bootstrapLog -Encoding UTF8 `
        -Value "[$([DateTime]::UtcNow.ToString('o'))] Gemini task failed: $($_.Exception.Message)"
    exit 1
}
