param(
    [Parameter(Mandatory)]
    [ValidateSet('grok', 'gemini', 'chatgpt-image')]
    [string]$Service
)

. (Join-Path $PSScriptRoot 'common.ps1')

if ($Service -eq 'grok') {
    Stop-ManagedProcess 'grok-gateway'
    Stop-ManagedProcess 'grok-upstream'
}
if ($Service -eq 'gemini') { Stop-ManagedProcess 'gemini-gateway' }
if ($Service -eq 'chatgpt-image') {
    Stop-ManagedProcess 'chatgpt-image-gateway'
    Stop-ManagedProcess 'chatgpt-image-upstream'
}

