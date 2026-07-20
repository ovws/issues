$ErrorActionPreference = 'Continue'
& (Join-Path $PSScriptRoot 'stop-admin.ps1')
foreach ($service in @('chatgpt-image', 'gemini', 'grok')) {
    & (Join-Path $PSScriptRoot 'stop-service.ps1') -Service $service
}
