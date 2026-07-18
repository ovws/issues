$ErrorActionPreference = 'Continue'
foreach ($service in @('chatgpt-image', 'gemini', 'grok')) {
    & (Join-Path $PSScriptRoot 'stop-service.ps1') -Service $service
}

