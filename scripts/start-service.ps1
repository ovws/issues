param(
    [Parameter(Mandatory)]
    [ValidateSet('grok', 'gemini', 'chatgpt-image')]
    [string]$Service
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-ProjectLayout
$python = Get-RootPython
$hostAddress = Get-Setting 'INTERNAL_AI_HOST' '0.0.0.0'

if ($Service -eq 'grok') {
    $grokRoot = Join-Path $script:ProjectRoot 'upstream\grok2api'
    $executable = Join-Path $grokRoot 'bin\grok2api.exe'
    $config = Join-Path $grokRoot 'config.yaml'
    if (-not (Test-Path -LiteralPath $executable)) { throw 'Grok binary missing; run scripts\install.ps1.' }
    if (-not (Test-Path -LiteralPath $config)) { throw 'Grok config missing; run scripts\install.ps1.' }
    Start-ManagedProcess -Name 'grok-upstream' -FilePath $executable `
        -Arguments @('--config', $config, '--listen', '127.0.0.1:18001') `
        -WorkingDirectory $grokRoot -LogDirectory (Join-Path $script:ProjectRoot 'logs\grok')
    # SQLite startup may need a little longer after a cold restart while the
    # upstream backend performs WAL recovery. Keep the process alive and wait
    # for the real listener before declaring startup failed.
    if (-not (Wait-TcpPort 18001 90)) { throw 'Grok upstream did not open port 18001. Check logs\grok.' }
    Set-ManagedProcessListenerPid -Name 'grok-upstream' -Port 18001
    $port = Get-Setting 'GROK_PORT' '8001'
    Start-ManagedProcess -Name 'grok-gateway' -FilePath $python `
        -Arguments @('-m', 'uvicorn', 'internal_ai_api.grok_app:app', '--host', $hostAddress, '--port', $port, '--env-file', $script:EnvFile, '--no-access-log') `
        -WorkingDirectory $script:ProjectRoot -LogDirectory (Join-Path $script:ProjectRoot 'logs\grok')
}

if ($Service -eq 'gemini') {
    $port = Get-Setting 'GEMINI_PORT' '8002'
    Start-ManagedProcess -Name 'gemini-gateway' -FilePath $python `
        -Arguments @('-m', 'uvicorn', 'internal_ai_api.gemini_app:app', '--host', $hostAddress, '--port', $port, '--env-file', $script:EnvFile, '--no-access-log') `
        -WorkingDirectory $script:ProjectRoot -LogDirectory (Join-Path $script:ProjectRoot 'logs\gemini')
}

if ($Service -eq 'chatgpt-image') {
    $chatgptRoot = Join-Path $script:ProjectRoot 'upstream\chatgpt2api'
    $upstreamPython = Join-Path $chatgptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $upstreamPython)) { throw 'ChatGPT2API environment missing; run scripts\install.ps1.' }
    $upstreamKey = Get-Setting 'CHATGPT_IMAGE_UPSTREAM_API_KEY'
    if (-not $upstreamKey -or $upstreamKey.StartsWith('replace-')) { throw 'Set CHATGPT_IMAGE_UPSTREAM_API_KEY in .env.' }
    $publicBaseUrl = Get-Setting 'CHATGPT_IMAGE_PUBLIC_BASE_URL'
    if (-not $publicBaseUrl -or $publicBaseUrl.Contains('x.x')) { throw 'Set CHATGPT_IMAGE_PUBLIC_BASE_URL to the LAN gateway URL in .env.' }
    [Environment]::SetEnvironmentVariable('CHATGPT2API_AUTH_KEY', $upstreamKey, 'Process')
    [Environment]::SetEnvironmentVariable('CHATGPT2API_BASE_URL', $publicBaseUrl.TrimEnd('/'), 'Process')
    [Environment]::SetEnvironmentVariable('STORAGE_BACKEND', 'sqlite', 'Process')
    Start-ManagedProcess -Name 'chatgpt-image-upstream' -FilePath $upstreamPython `
        -Arguments @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '18003', '--no-access-log') `
        -WorkingDirectory $chatgptRoot -LogDirectory (Join-Path $script:ProjectRoot 'logs\chatgpt-image')
    if (-not (Wait-TcpPort 18003)) { throw 'ChatGPT2API did not open port 18003. Check logs\chatgpt-image.' }
    Set-ManagedProcessListenerPid -Name 'chatgpt-image-upstream' -Port 18003
    $port = Get-Setting 'CHATGPT_IMAGE_PORT' '8003'
    Start-ManagedProcess -Name 'chatgpt-image-gateway' -FilePath $python `
        -Arguments @('-m', 'uvicorn', 'internal_ai_api.chatgpt_image_app:app', '--host', $hostAddress, '--port', $port, '--env-file', $script:EnvFile, '--no-access-log') `
        -WorkingDirectory $script:ProjectRoot -LogDirectory (Join-Path $script:ProjectRoot 'logs\chatgpt-image')
    if (-not (Wait-TcpPort $port)) { throw 'ChatGPT image gateway did not open its port. Check logs\chatgpt-image.' }
    Set-ManagedProcessListenerPid -Name 'chatgpt-image-gateway' -Port $port
}
