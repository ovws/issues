Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:EnvFile = Join-Path $script:ProjectRoot '.env'

function Get-EnvMap {
    $result = @{}
    if (Test-Path -LiteralPath $script:EnvFile) {
        foreach ($line in Get-Content -LiteralPath $script:EnvFile -Encoding UTF8) {
            $trimmed = $line.Trim()
            if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) { continue }
            $name, $value = $trimmed.Split('=', 2)
            $result[$name.Trim()] = $value.Trim().Trim('"').Trim("'")
        }
    }
    return $result
}

function Get-Setting([string]$Name, [string]$Default = '') {
    $processValue = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ($processValue) { return $processValue }
    $values = Get-EnvMap
    if ($values.ContainsKey($Name)) { return $values[$Name] }
    return $Default
}

function Initialize-ProjectLayout {
    foreach ($relative in @('data', 'logs', 'run', 'config', 'upstream')) {
        $path = Join-Path $script:ProjectRoot $relative
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
}

function Get-RootPython {
    $python = Join-Path $script:ProjectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Root virtual environment is missing. Run scripts\install.ps1 first."
    }
    return $python
}

function Start-ManagedProcess {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][string]$LogDirectory
    )
    $pidFile = Join-Path $script:ProjectRoot "run\$Name.pid.json"
    if (Test-Path -LiteralPath $pidFile) {
        $record = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
        $recordedProcess = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
        if ($recordedProcess) {
            $actualStart = $recordedProcess.StartTime.ToUniversalTime().ToString('o')
            if ($actualStart -eq $record.startedAt) {
                Write-Host "$Name is already running (PID $($record.pid))."
                return
            }
        }
        Remove-Item -LiteralPath $pidFile -Force
    }
    New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null

    # Some launchers provide both `Path` and `PATH`. Windows accepts that
    # environment block, but Windows PowerShell 5.1 Start-Process rejects it
    # as a duplicate-key dictionary. Normalize it before spawning services.
    $processPath = [Environment]::GetEnvironmentVariable('Path', 'Process')
    if ($processPath) {
        [Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
        [Environment]::SetEnvironmentVariable('Path', $processPath, 'Process')
    }
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $LogDirectory "$Name.out.log") `
        -RedirectStandardError (Join-Path $LogDirectory "$Name.err.log")
    $record = [ordered]@{
        name = $Name
        pid = $process.Id
        startedAt = $process.StartTime.ToUniversalTime().ToString('o')
        executable = $FilePath
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
    Write-Host "Started $Name (PID $($process.Id))."
}

function Set-ManagedProcessListenerPid([string]$Name, [int]$Port) {
    $pidFile = Join-Path $script:ProjectRoot "run\$Name.pid.json"
    if (-not (Test-Path -LiteralPath $pidFile)) { throw "Missing PID file for $Name." }
    $record = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
    $listenerPid = $null
    foreach ($line in (& netstat.exe -ano -p tcp)) {
        if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            $listenerPid = [int]$Matches[1]
            break
        }
    }
    if (-not $listenerPid) { throw "Cannot identify the listener PID for $Name on port $Port." }
    if ($listenerPid -eq $record.pid) { return }
    $listener = Get-Process -Id $listenerPid -ErrorAction Stop
    $updated = [ordered]@{
        name = $Name
        pid = $listenerPid
        startedAt = $listener.StartTime.ToUniversalTime().ToString('o')
        executable = $record.executable
        rootPid = $record.pid
        rootStartedAt = $record.startedAt
        listenerPort = $Port
    }
    $updated | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
}

function Stop-ManagedProcess([string]$Name) {
    $pidFile = Join-Path $script:ProjectRoot "run\$Name.pid.json"
    if (-not (Test-Path -LiteralPath $pidFile)) {
        Write-Host "$Name is not recorded as running."
        return
    }
    $record = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
    $process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
    if ($process) {
        $actualStart = $process.StartTime.ToUniversalTime().ToString('o')
        if ($actualStart -ne $record.startedAt) {
            throw "Refusing to stop PID $($record.pid): stale PID file for $Name."
        }
        Stop-Process -Id $process.Id
        if (-not $process.WaitForExit(15000)) {
            throw "$Name did not stop within 15 seconds."
        }
        Write-Host "Stopped $Name."
    }
    if ($record.PSObject.Properties.Name -contains 'rootPid') {
        $rootProcess = Get-Process -Id $record.rootPid -ErrorAction SilentlyContinue
        if ($rootProcess) {
            $rootStart = $rootProcess.StartTime.ToUniversalTime().ToString('o')
            if ($rootStart -eq $record.rootStartedAt) {
                Stop-Process -Id $rootProcess.Id
                $rootProcess.WaitForExit(15000) | Out-Null
            }
        }
    }
    Remove-Item -LiteralPath $pidFile -Force
}

function Wait-TcpPort([int]$Port, [int]$TimeoutSeconds = 30) {
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        $client = [Net.Sockets.TcpClient]::new()
        try {
            $task = $client.ConnectAsync('127.0.0.1', $Port)
            if ($task.Wait(500) -and $client.Connected) { return $true }
        } catch { }
        finally { $client.Dispose() }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

