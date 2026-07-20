param([string]$TaskName = 'Internal AI API - ChatGPT Image')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $PSScriptRoot 'start-service.ps1'
$engine = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$arguments = (
    "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass " +
    "-File `"$runner`" -Service chatgpt-image"
)
$action = New-ScheduledTaskAction -Execute $engine -Argument $arguments -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings `
    -Description 'Start only the local ChatGPT image API service on ports 18003/8003.' `
    -Force | Out-Null
Write-Host "Registered scheduled task: $TaskName"
