param(
    [Parameter(Mandatory)]
    [string]$PublicBaseUrl,
    [switch]$RebuildFrontend
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-ProjectLayout

if ($PublicBaseUrl -notmatch '^https?://[^/]+(?::\d+)?$') {
    throw 'PublicBaseUrl must be an HTTP(S) origin without /v1.'
}

$chatgptRoot = Join-Path $script:ProjectRoot 'upstream\chatgpt2api'
if (-not (Test-Path -LiteralPath (Join-Path $chatgptRoot 'pyproject.toml'))) {
    throw 'ChatGPT2API checkout is missing. Run scripts\install.ps1 first.'
}

$uv = Join-Path $script:ProjectRoot '.venv\Scripts\uv.exe'
if (-not (Test-Path -LiteralPath $uv)) {
    throw 'uv is missing from the root environment.'
}

function New-RandomSecret {
    $bytes = [byte[]]::new(48)
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([Convert]::ToBase64String($bytes)).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Read-EnvLines {
    if (Test-Path -LiteralPath $script:EnvFile) {
        return @(Get-Content -LiteralPath $script:EnvFile -Encoding UTF8)
    }
    return @(Get-Content -LiteralPath (Join-Path $script:ProjectRoot '.env.example') -Encoding UTF8)
}

function Get-EnvLineValue([string[]]$Lines, [string]$Name) {
    foreach ($line in $Lines) {
        if ($line -match "^$([regex]::Escape($Name))=(.*)$") { return $Matches[1].Trim() }
    }
    return ''
}

function Set-EnvLine([Collections.Generic.List[string]]$Lines, [string]$Name, [string]$Value) {
    for ($index = 0; $index -lt $Lines.Count; $index++) {
        if ($Lines[$index] -match "^$([regex]::Escape($Name))=") {
            $Lines[$index] = "$Name=$Value"
            return
        }
    }
    $Lines.Add("$Name=$Value")
}

$envLines = Read-EnvLines
$masterKey = Get-EnvLineValue $envLines 'CHATGPT_IMAGE_UPSTREAM_API_KEY'
if (-not $masterKey -or $masterKey.StartsWith('replace-')) { $masterKey = New-RandomSecret }

$updatedEnv = [Collections.Generic.List[string]]::new()
foreach ($line in $envLines) { $updatedEnv.Add($line) }
Set-EnvLine $updatedEnv 'CHATGPT_IMAGE_PORT' '8003'
Set-EnvLine $updatedEnv 'CHATGPT_IMAGE_UPSTREAM_URL' 'http://127.0.0.1:18003'
Set-EnvLine $updatedEnv 'CHATGPT_IMAGE_UPSTREAM_API_KEY' $masterKey
Set-EnvLine $updatedEnv 'CHATGPT_IMAGE_PUBLIC_BASE_URL' $PublicBaseUrl.TrimEnd('/')
Set-EnvLine $updatedEnv 'CHATGPT_IMAGE_FAILURE_THRESHOLD' '3'
$updatedEnv | Set-Content -LiteralPath $script:EnvFile -Encoding UTF8

$configPath = Join-Path $chatgptRoot 'config.json'
$config = Get-Content -Raw -Encoding UTF8 -LiteralPath $configPath | ConvertFrom-Json
$config.'auth-key' = ''
$config.base_url = $PublicBaseUrl.TrimEnd('/')
$config.image_account_concurrency = 1
$config.image_parallel_generation = $false
$config.auto_remove_rate_limited_accounts = $false
$config.auto_remove_invalid_accounts = $false
$config.auto_relogin_after_refresh = $false
$config.proxy_runtime.enabled = $false
$config.proxy_runtime.egress_mode = 'direct'
$config.proxy_runtime.proxy_url = ''
$config.proxy_runtime.resource_proxy_url = ''
$config.proxy_runtime.skip_ssl_verify = $false
$config.proxy_runtime.clearance.enabled = $false
$config.proxy_runtime.clearance.mode = 'none'
$config.proxy_runtime.clearance.cf_cookies = ''
$config.proxy_runtime.clearance.cf_clearance = ''
$config.proxy_runtime.clearance.flaresolverr_url = ''
$config.proxy_runtime.clearance.warm_up_on_start = $false
$config.third_party_apps.infinite_canvas.enabled = $false
$config | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $configPath -Encoding UTF8

New-Item -ItemType Directory -Force -Path (Join-Path $chatgptRoot 'data') | Out-Null
[Environment]::SetEnvironmentVariable(
    'UV_CACHE_DIR', (Join-Path $script:ProjectRoot '.uv-cache'), 'Process'
)
[Environment]::SetEnvironmentVariable(
    'UV_PYTHON_INSTALL_DIR', (Join-Path $script:ProjectRoot '.uv-python'), 'Process'
)
[Environment]::SetEnvironmentVariable(
    'npm_config_cache', (Join-Path $script:ProjectRoot '.npm-cache'), 'Process'
)
[Environment]::SetEnvironmentVariable('NEXT_TELEMETRY_DISABLED', '1', 'Process')

Push-Location $chatgptRoot
try {
    & $uv sync --frozen --python 3.13 --no-dev
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install ChatGPT2API Python dependencies.' }
} finally { Pop-Location }

$webDist = Join-Path $chatgptRoot 'web_dist'
if ($RebuildFrontend -or -not (Test-Path -LiteralPath (Join-Path $webDist 'index.html'))) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw 'npm is required to build the local-only management frontend.'
    }
    $web = Join-Path $chatgptRoot 'web'
    Push-Location $web
    try {
        npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw 'Failed to install ChatGPT2API frontend packages.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Failed to build ChatGPT2API frontend.' }
    } finally { Pop-Location }
    New-Item -ItemType Directory -Force -Path $webDist | Out-Null
    Copy-Item -Path (Join-Path $web 'out\*') -Destination $webDist -Recurse -Force
}

Write-Host 'ChatGPT image native runtime is ready.'
Write-Host "Public API origin: $($PublicBaseUrl.TrimEnd('/'))"
Write-Host 'The upstream master key was stored in .env and was not printed.'
