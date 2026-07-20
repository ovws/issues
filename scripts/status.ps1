. (Join-Path $PSScriptRoot 'common.ps1')

$targets = @(
    @{ Name = 'internal-ai-admin'; Port = (Get-Setting 'INTERNAL_AI_ADMIN_PORT' '8090'); Health = "http://127.0.0.1:$(Get-Setting 'INTERNAL_AI_ADMIN_PORT' '8090')/health" },
    @{ Name = 'grok-upstream'; Port = 18001; Health = 'http://127.0.0.1:18001/healthz' },
    @{ Name = 'grok-gateway'; Port = (Get-Setting 'GROK_PORT' '8001'); Health = "http://127.0.0.1:$(Get-Setting 'GROK_PORT' '8001')/health" },
    @{ Name = 'gemini-gateway'; Port = (Get-Setting 'GEMINI_PORT' '8002'); Health = "http://127.0.0.1:$(Get-Setting 'GEMINI_PORT' '8002')/health" },
    @{ Name = 'chatgpt-image-upstream'; Port = 18003; Health = '' },
    @{ Name = 'chatgpt-image-gateway'; Port = (Get-Setting 'CHATGPT_IMAGE_PORT' '8003'); Health = "http://127.0.0.1:$(Get-Setting 'CHATGPT_IMAGE_PORT' '8003')/health" }
)

$rows = foreach ($target in $targets) {
    $pidFile = Join-Path $script:ProjectRoot "run\$($target.Name).pid.json"
    $pidValue = $null
    $running = $false
    if (Test-Path -LiteralPath $pidFile) {
        $record = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
        $pidValue = $record.pid
        $running = [bool](Get-Process -Id $pidValue -ErrorAction SilentlyContinue)
    }
    $health = 'n/a'
    if ($target.Health -and $running) {
        try {
            $result = Invoke-RestMethod -Uri $target.Health -TimeoutSec 3
            $statusProperty = $result.PSObject.Properties['status']
            $health = if ($statusProperty -and $statusProperty.Value) {
                [string]$statusProperty.Value
            } else {
                'ok'
            }
        } catch { $health = 'unreachable' }
    }
    [pscustomobject]@{
        Name = $target.Name
        PID = $pidValue
        Running = $running
        Port = $target.Port
        Health = $health
    }
}
$rows | Format-Table -AutoSize
