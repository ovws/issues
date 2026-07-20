param(
    [ValidateRange(10, 900)]
    [int]$StartupTimeoutSeconds = 120,

    [ValidateRange(1, 30)]
    [int]$HealthIntervalSeconds = 3,

    [string]$RuntimeRoot,

    [switch]$PreflightOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)

$sourceRoot = Split-Path -Parent $PSScriptRoot

function Test-RuntimeRoot {
    param([Parameter(Mandatory)][string]$Path)

    return (
        (Test-Path -LiteralPath (Join-Path $Path '.env') -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $Path '.venv\Scripts\python.exe') -PathType Leaf)
    )
}

function Resolve-RuntimeRoot {
    $requestedRoot = $RuntimeRoot
    if (-not $requestedRoot) {
        $requestedRoot = [Environment]::GetEnvironmentVariable('AI_API_RUNTIME_ROOT', 'Process')
    }
    if ($requestedRoot) {
        $resolved = Resolve-Path -LiteralPath $requestedRoot -ErrorAction Stop
        return $resolved.Path
    }

    if (Test-RuntimeRoot -Path $sourceRoot) { return $sourceRoot }

    $git = Get-Command git.exe -ErrorAction SilentlyContinue
    if (-not $git) { $git = Get-Command git -ErrorAction SilentlyContinue }
    if ($git) {
        $commonDirectory = & $git.Source -C $sourceRoot rev-parse `
            --path-format=absolute --git-common-dir 2>$null
        if ($LASTEXITCODE -eq 0 -and $commonDirectory) {
            $candidate = Split-Path -Parent ([string]$commonDirectory).Trim()
            if (Test-RuntimeRoot -Path $candidate) { return $candidate }
        }
    }

    return $sourceRoot
}

$projectRoot = Resolve-RuntimeRoot

$services = @(
    [pscustomobject]@{
        Name = 'Grok API'
        Key = 'grok'
        Port = 8001
        PortSetting = 'GROK_PORT'
        BasePath = '/v1'
        HealthPaths = @('/health', '/v1/models')
        RequiredFiles = @(
            '.env'
            '.venv\Scripts\python.exe'
            'upstream\grok2api\bin\grok2api.exe'
            'upstream\grok2api\config.yaml'
        )
        RequiredDirectories = @('data', 'logs', 'run')
        WritableDirectories = @('data', 'logs\grok', 'run')
        WritableFiles = @()
        LogLocation = 'logs\grok'
        HealthKeyEnvironment = 'AI_API_GROK_HEALTH_KEY'
    }
    [pscustomobject]@{
        Name = 'Gemini API'
        Key = 'gemini'
        Port = 8002
        PortSetting = 'GEMINI_PORT'
        BasePath = '/v1'
        HealthPaths = @('/health', '/v1/models')
        RequiredFiles = @(
            '.env'
            '.venv\Scripts\python.exe'
            'config\gemini-cookies.local.json'
            'upstream\gemini-api\pyproject.toml'
        )
        RequiredDirectories = @('data', 'logs', 'run')
        WritableDirectories = @('data\media\gemini', 'logs\gemini', 'run')
        WritableFiles = @()
        LogLocation = 'logs\gemini'
        HealthKeyEnvironment = 'AI_API_GEMINI_HEALTH_KEY'
    }
    [pscustomobject]@{
        Name = 'ChatGPT Image'
        Key = 'chatgpt-image'
        Port = 8003
        PortSetting = 'CHATGPT_IMAGE_PORT'
        BasePath = '/v1'
        HealthPaths = @('/health', '/v1/models')
        RequiredFiles = @(
            '.env'
            '.venv\Scripts\python.exe'
            'upstream\chatgpt2api\.venv\Scripts\python.exe'
            'upstream\chatgpt2api\pyproject.toml'
        )
        RequiredDirectories = @('data', 'logs', 'run')
        WritableDirectories = @('upstream\chatgpt2api\data', 'logs\chatgpt-image', 'run')
        WritableFiles = @(
            'data\chatgpt-image.db'
            'upstream\chatgpt2api\data\accounts.db'
        )
        LogLocation = 'logs\chatgpt-image'
        HealthKeyEnvironment = 'AI_API_CHATGPT_IMAGE_HEALTH_KEY'
    }
    [pscustomobject]@{
        Name = 'Admin Console'
        Key = 'admin'
        Port = 8090
        PortSetting = 'INTERNAL_AI_ADMIN_PORT'
        BasePath = ''
        HealthPaths = @('/health')
        RequiredFiles = @(
            '.env'
            '.venv\Scripts\python.exe'
            'scripts\start-admin.ps1'
            'src\internal_ai_api\admin_app.py'
        )
        RequiredDirectories = @('data', 'logs', 'run')
        WritableDirectories = @('data', 'logs\admin', 'run')
        WritableFiles = @()
        LogLocation = 'logs\admin'
        HealthKeyEnvironment = $null
    }
)

function Get-EnvValue {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) {
            continue
        }
        $parts = $trimmed.Split('=', 2)
        if ($parts[0].Trim() -eq $Name) {
            return $parts[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Test-ConfiguredValue {
    param([AllowNull()][string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) { return $false }
    return $Value -notmatch '^(replace-|change-me|your-|example)'
}

function Test-DirectoryWritable {
    param([Parameter(Mandatory)][string]$Path)

    $probePath = $null
    try {
        if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
            New-Item -ItemType Directory -Force -Path $Path | Out-Null
        }
        $probePath = Join-Path $Path ('.ai-api-write-test-{0}.tmp' -f [Guid]::NewGuid())
        [IO.File]::WriteAllText($probePath, 'ok', [Text.UTF8Encoding]::new($false))
        return $true
    } catch {
        return $false
    } finally {
        if ($probePath -and (Test-Path -LiteralPath $probePath)) {
            Remove-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue
        }
    }
}

function Test-FileWritable {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $true }
    try {
        $stream = [IO.File]::Open(
            $Path,
            [IO.FileMode]::Open,
            [IO.FileAccess]::ReadWrite,
            [IO.FileShare]::ReadWrite
        )
        $stream.Dispose()
        return $true
    } catch {
        return $false
    }
}

function Get-ServiceConfigurationErrors {
    param([Parameter(Mandatory)]$Service)

    $errors = New-Object System.Collections.Generic.List[string]
    foreach ($relative in $Service.RequiredFiles) {
        $path = Join-Path $projectRoot $relative
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            $errors.Add("缺少文件：$relative")
        }
    }
    foreach ($relative in $Service.RequiredDirectories) {
        $path = Join-Path $projectRoot $relative
        if (-not (Test-Path -LiteralPath $path -PathType Container)) {
            $errors.Add("缺少目录：$relative")
        }
    }
    $hasPermissionError = $false
    foreach ($relative in $Service.WritableDirectories) {
        $path = Join-Path $projectRoot $relative
        if (-not (Test-DirectoryWritable -Path $path)) {
            $errors.Add("目录不可写：$relative")
            $hasPermissionError = $true
        }
    }
    foreach ($relative in $Service.WritableFiles) {
        $path = Join-Path $projectRoot $relative
        if (-not (Test-FileWritable -Path $path)) {
            $errors.Add("运行文件不可读写：$relative")
            $hasPermissionError = $true
        }
    }
    if ($hasPermissionError) {
        $repairScript = Join-Path $sourceRoot 'scripts\repair-runtime-permissions.ps1'
        $errors.Add(
            "请以管理员身份运行：powershell -ExecutionPolicy Bypass -File `"$repairScript`" " +
            "-RuntimeRoot `"$projectRoot`""
        )
    }

    $rootEnv = Join-Path $projectRoot '.env'
    if (Test-Path -LiteralPath $rootEnv -PathType Leaf) {
        $configuredPort = Get-EnvValue -Path $rootEnv -Name $Service.PortSetting
        if ($configuredPort -and $configuredPort -ne [string]$Service.Port) {
            $errors.Add("$($Service.PortSetting) 必须为 $($Service.Port)，当前配置不一致")
        }
    }

    if ($Service.Key -eq 'grok') {
        $envFile = Join-Path $projectRoot '.env'
        $key = Get-EnvValue -Path $envFile -Name 'GROK_UPSTREAM_API_KEY'
        if ((Test-Path -LiteralPath $envFile) -and -not (Test-ConfiguredValue $key)) {
            $errors.Add('`.env` 中的 GROK_UPSTREAM_API_KEY 尚未配置')
        }
    }

    if ($Service.Key -eq 'gemini') {
        $cookiePath = Join-Path $projectRoot 'config\gemini-cookies.local.json'
        if (Test-Path -LiteralPath $cookiePath -PathType Leaf) {
            try {
                $cookie = Get-Content -Raw -Encoding UTF8 -LiteralPath $cookiePath | ConvertFrom-Json
                if (-not (Test-ConfiguredValue $cookie.'__Secure-1PSID') -or
                    -not (Test-ConfiguredValue $cookie.'__Secure-1PSIDTS')) {
                    $errors.Add('Gemini Cookie 文件仍为空或包含占位值')
                }
            } catch {
                $errors.Add('Gemini Cookie 文件不是有效 JSON')
            }
        }
    }

    if ($Service.Key -eq 'chatgpt-image') {
        $envFile = Join-Path $projectRoot '.env'
        $gatewayKey = Get-EnvValue -Path $envFile -Name 'CHATGPT_IMAGE_UPSTREAM_API_KEY'
        $publicBaseUrl = Get-EnvValue -Path $envFile -Name 'CHATGPT_IMAGE_PUBLIC_BASE_URL'
        if ((Test-Path -LiteralPath $envFile) -and -not (Test-ConfiguredValue $gatewayKey)) {
            $errors.Add('ChatGPT Image 网关上游密钥尚未配置')
        }
        if ((Test-Path -LiteralPath $envFile) -and
            (-not (Test-ConfiguredValue $publicBaseUrl) -or $publicBaseUrl -match 'x\.x')) {
            $errors.Add('CHATGPT_IMAGE_PUBLIC_BASE_URL 尚未配置为服务器内网地址')
        }
    }

    return @($errors)
}

function Test-PortListening {
    param([Parameter(Mandatory)][int]$Port)

    $getNetTcp = Get-Command Get-NetTCPConnection -ErrorAction SilentlyContinue
    if ($getNetTcp) {
        $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -First 1
        return $null -ne $listener
    }

    foreach ($line in (& "$env:SystemRoot\System32\netstat.exe" -ano -p tcp 2>$null)) {
        if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+\d+\s*$") {
            return $true
        }
    }
    return $false
}

function Get-HttpStatusCode {
    param([Parameter(Mandatory)]$ErrorRecord)

    try {
        if ($ErrorRecord.Exception.Response -and $ErrorRecord.Exception.Response.StatusCode) {
            return [int]$ErrorRecord.Exception.Response.StatusCode
        }
    } catch { }
    return $null
}

function Invoke-ServiceHealthProbe {
    param([Parameter(Mandatory)]$Service)

    $baseUrl = "http://127.0.0.1:$($Service.Port)"
    $healthKey = $null
    if ($Service.HealthKeyEnvironment) {
        $healthKey = [Environment]::GetEnvironmentVariable(
            $Service.HealthKeyEnvironment,
            'Process'
        )
    }
    $headers = @{}
    if ($healthKey) { $headers['Authorization'] = "Bearer $healthKey" }

    foreach ($path in $Service.HealthPaths) {
        $uri = "$baseUrl$path"
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $uri -Headers $headers `
                -TimeoutSec 5 -ErrorAction Stop
        } catch {
            $statusCode = Get-HttpStatusCode -ErrorRecord $_
            if ($path -eq '/health' -and $statusCode -in @(401, 403, 404, 405)) {
                continue
            }
            if ($path -eq '/v1/models' -and $statusCode -in @(401, 403) -and -not $healthKey) {
                return [pscustomobject]@{
                    Healthy = $false
                    Detail = "健康端点不可用；/v1/models 需要通过 $($Service.HealthKeyEnvironment) 提供个人密钥"
                }
            }
            $detail = if ($statusCode) { "HTTP $statusCode" } else { '无法连接' }
            if ($path -eq '/health') { continue }
            return [pscustomobject]@{ Healthy = $false; Detail = "$path $detail" }
        }

        if ($path -eq '/health') {
            try {
                $payload = $response.Content | ConvertFrom-Json
                $status = [string]$payload.status
                if ($status -and $status -notin @('ok', 'degraded', 'healthy')) {
                    return [pscustomobject]@{ Healthy = $false; Detail = "/health 状态为 $status" }
                }
                $label = if ($status) { $status } else { "HTTP $($response.StatusCode)" }
                return [pscustomobject]@{ Healthy = $true; Detail = "/health $label" }
            } catch {
                return [pscustomobject]@{
                    Healthy = $true
                    Detail = "/health HTTP $($response.StatusCode)"
                }
            }
        }

        return [pscustomobject]@{
            Healthy = $true
            Detail = "/v1/models HTTP $($response.StatusCode)"
        }
    }

    return [pscustomobject]@{ Healthy = $false; Detail = '健康检查失败' }
}

function Start-ServiceWorkload {
    param([Parameter(Mandatory)]$Service)

    if ($Service.Key -eq 'admin') {
        & (Join-Path $projectRoot 'scripts\start-admin.ps1')
        return
    }
    & (Join-Path $projectRoot 'scripts\start-service.ps1') -Service $Service.Key
}

function Wait-ServiceHealthy {
    param([Parameter(Mandatory)]$Service)

    $deadline = [DateTime]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    do {
        $probe = Invoke-ServiceHealthProbe -Service $Service
        if ($probe.Healthy) { return $probe }
        Start-Sleep -Seconds $HealthIntervalSeconds
    } while ([DateTime]::UtcNow -lt $deadline)

    return [pscustomobject]@{
        Healthy = $false
        Detail = "等待 $StartupTimeoutSeconds 秒后超时；最后结果：$($probe.Detail)"
    }
}

function New-Result {
    param(
        [Parameter(Mandatory)]$Service,
        [Parameter(Mandatory)][bool]$Success,
        [Parameter(Mandatory)][string]$State,
        [Parameter(Mandatory)][string]$Detail
    )

    return [pscustomobject]@{
        Name = $Service.Name
        Success = $Success
        State = $State
        Detail = $Detail
        BaseUrl = "http://127.0.0.1:$($Service.Port)$($Service.BasePath)"
        LogLocation = $Service.LogLocation
    }
}

Write-Host '公司内网 AI API 一键启动（WK-81）'
Write-Host "脚本目录：$sourceRoot"
Write-Host "运行目录：$projectRoot"
Write-Host "启动超时：$StartupTimeoutSeconds 秒"
Write-Host ''

Write-Host '[运行模式] Windows 本地进程'

$results = New-Object System.Collections.Generic.List[object]
foreach ($service in $services) {
    Write-Host ''
    Write-Host "[$($service.Name)] 端口 $($service.Port)"

    $probe = Invoke-ServiceHealthProbe -Service $service
    if ($probe.Healthy) {
        Write-Host "  [已运行] $($probe.Detail)" -ForegroundColor Green
        $results.Add((New-Result -Service $service -Success $true -State '已运行' -Detail $probe.Detail))
        continue
    }

    try {
        $configurationErrors = @(Get-ServiceConfigurationErrors -Service $service)
        if (Test-PortListening -Port $service.Port) {
            $configurationErrors += "端口 $($service.Port) 已被非健康服务占用"
        }
    } catch {
        $preflightMessage = $_.Exception.Message -replace '(?i)(bearer|api[-_ ]?key|cookie|token)\s*[:=]\s*\S+', '$1=[REDACTED]'
        $configurationErrors = @("预检异常：$preflightMessage")
    }

    if ($configurationErrors.Count -gt 0) {
        foreach ($message in $configurationErrors) {
            Write-Host "  [失败] $message" -ForegroundColor Red
        }
        $results.Add((New-Result -Service $service -Success $false -State '预检失败' `
            -Detail ($configurationErrors -join '；')))
        continue
    }

    Write-Host '  [成功] 配置、目录和端口预检通过' -ForegroundColor Green
    if ($PreflightOnly) {
        $results.Add((New-Result -Service $service -Success $true -State '预检通过' `
            -Detail '未执行启动'))
        continue
    }

    try {
        Write-Host "  [启动] 正在启动 $($service.Name)..."
        Start-ServiceWorkload -Service $service
        $probe = Wait-ServiceHealthy -Service $service
        if ($probe.Healthy) {
            Write-Host "  [成功] $($probe.Detail)" -ForegroundColor Green
            $results.Add((New-Result -Service $service -Success $true -State '启动成功' `
                -Detail $probe.Detail))
        } else {
            Write-Host "  [超时] $($probe.Detail)" -ForegroundColor Red
            $results.Add((New-Result -Service $service -Success $false -State '启动超时' `
                -Detail $probe.Detail))
        }
    } catch {
        $safeMessage = $_.Exception.Message -replace '(?i)(bearer|api[-_ ]?key|cookie|token)\s*[:=]\s*\S+', '$1=[REDACTED]'
        Write-Host "  [失败] $safeMessage" -ForegroundColor Red
        $results.Add((New-Result -Service $service -Success $false -State '启动失败' `
            -Detail $safeMessage))
    }
}

Write-Host ''
Write-Host '==================== 启动结果 ===================='
foreach ($result in $results) {
    $color = if ($result.Success) { 'Green' } else { 'Red' }
    Write-Host ("{0,-18} {1,-10} {2}" -f $result.Name, $result.State, $result.Detail) -ForegroundColor $color
    Write-Host "  Base URL：$($result.BaseUrl)"
    Write-Host "  日志位置：$($result.LogLocation)"
}

$failed = @($results | Where-Object { -not $_.Success }).Count
if ($failed -gt 0) {
    Write-Host ''
    Write-Host "启动未全部成功：$failed 个服务失败。已正常运行的服务不会被停止。" -ForegroundColor Red
    exit 1
}

Write-Host ''
if ($PreflightOnly) { Write-Host '三套 API 与管理工具预检全部通过。' -ForegroundColor Green }
else { Write-Host '三套 API 与管理工具均已运行并通过健康检查。' -ForegroundColor Green }
exit 0
