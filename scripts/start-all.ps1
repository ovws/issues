$ErrorActionPreference = 'Stop'
foreach ($service in @('grok', 'gemini', 'chatgpt-image')) {
    & (Join-Path $PSScriptRoot 'start-service.ps1') -Service $service
}
& (Join-Path $PSScriptRoot 'start-admin.ps1')
