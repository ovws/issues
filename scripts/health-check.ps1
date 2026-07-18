. (Join-Path $PSScriptRoot 'common.ps1')

$services = @(
    @{ Name = 'grok'; Port = (Get-Setting 'GROK_PORT' '8001') },
    @{ Name = 'gemini'; Port = (Get-Setting 'GEMINI_PORT' '8002') },
    @{ Name = 'chatgpt-image'; Port = (Get-Setting 'CHATGPT_IMAGE_PORT' '8003') }
)
$failed = 0
foreach ($service in $services) {
    $uri = "http://127.0.0.1:$($service.Port)/health"
    try {
        $result = Invoke-RestMethod -Uri $uri -TimeoutSec 5
        Write-Host "$($service.Name): $($result.status), queued=$($result.queue.queued), running=$($result.queue.running)"
        if ($result.status -notin @('ok', 'degraded')) { $failed++ }
    } catch {
        Write-Error "$($service.Name): unavailable at $uri"
        $failed++
    }
}
if ($failed) { exit 1 }

