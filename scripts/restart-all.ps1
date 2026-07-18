param(
    [ValidateSet('all', 'grok', 'gemini', 'chatgpt-image')]
    [string]$Service = 'all'
)

if ($Service -eq 'all') {
    & (Join-Path $PSScriptRoot 'stop-all.ps1')
    & (Join-Path $PSScriptRoot 'start-all.ps1')
} else {
    & (Join-Path $PSScriptRoot 'stop-service.ps1') -Service $Service
    & (Join-Path $PSScriptRoot 'start-service.ps1') -Service $Service
}

