. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-ProjectLayout
$python = Get-RootPython
$port = Get-Setting 'INTERNAL_AI_ADMIN_PORT' '8090'

Start-ManagedProcess -Name 'internal-ai-admin' -FilePath $python `
    -Arguments @(
        '-m', 'uvicorn', 'internal_ai_api.admin_app:app',
        '--host', '127.0.0.1', '--port', $port,
        '--env-file', $script:EnvFile, '--no-access-log'
    ) `
    -WorkingDirectory $script:ProjectRoot `
    -LogDirectory (Join-Path $script:ProjectRoot 'logs\admin')

if (-not (Wait-TcpPort $port)) {
    throw 'Internal AI admin console did not open its loopback port. Check logs\admin.'
}
Set-ManagedProcessListenerPid -Name 'internal-ai-admin' -Port $port
