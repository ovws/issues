param(
    [string]$PublicBaseUrl = 'http://chatgpt-image.internal',
    [switch]$RefreshPinnedCommit,
    [switch]$ForceLocalConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-ProjectLayout

if ($PublicBaseUrl -notmatch '^https?://[^/]+(?::\d+)?$') {
    throw 'PublicBaseUrl must be an HTTP(S) origin without /v1, for example http://chatgpt-image.internal.'
}

$manifestPath = Join-Path $script:ProjectRoot 'config\upstreams.json'
$repositories = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
$repository = $repositories |
    Where-Object { $_.name -eq 'chatgpt2api' } |
    Select-Object -First 1
if (-not $repository) { throw 'chatgpt2api is missing from config\upstreams.json.' }

$path = Join-Path $script:ProjectRoot $repository.path
$safePath = $path.Replace('\', '/')
if (-not (Test-Path -LiteralPath (Join-Path $path '.git'))) {
    git clone --no-checkout $repository.url $path
    if ($LASTEXITCODE -ne 0) { throw "Failed to clone $($repository.url)." }
}

$dirty = git -c "safe.directory=$safePath" -C $path status --porcelain
if ($dirty) { throw "Refusing to change a dirty ChatGPT2API checkout: $path" }

git -c "safe.directory=$safePath" -C $path cat-file -e "$($repository.commit)^{commit}" 2>$null
if ($LASTEXITCODE -ne 0 -or $RefreshPinnedCommit) {
    git -c "safe.directory=$safePath" -C $path fetch --depth 1 origin $repository.commit
    if ($LASTEXITCODE -ne 0) { throw 'Failed to fetch the pinned ChatGPT2API commit.' }
}

$current = git -c "safe.directory=$safePath" -C $path rev-parse HEAD
if ($current -ne $repository.commit) {
    git -c "safe.directory=$safePath" -C $path checkout --detach $repository.commit
    if ($LASTEXITCODE -ne 0) { throw 'Failed to check out the pinned ChatGPT2API commit.' }
}

$upstreamEnv = Join-Path $script:ProjectRoot 'config\chatgpt2api.local.env'
$gatewayEnv = Join-Path $script:ProjectRoot 'config\chatgpt-image.gateway.local.env'
$localConfig = Join-Path $script:ProjectRoot 'config\chatgpt-config.local.json'
$existing = @(@($upstreamEnv, $gatewayEnv, $localConfig) | Where-Object {
    Test-Path -LiteralPath $_
})
if ($existing.Count -and -not $ForceLocalConfig) {
    throw "Local ChatGPT configuration already exists. Use -ForceLocalConfig to replace it: $($existing -join ', ')"
}

$bytes = [byte[]]::new(48)
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
$masterKey = ([Convert]::ToBase64String($bytes)).TrimEnd('=').Replace('+', '-').Replace('/', '_')

@(
    '# Upstream administrator/master credential. Never distribute this file or value.'
    "CHATGPT2API_AUTH_KEY=$masterKey"
    "CHATGPT2API_BASE_URL=$($PublicBaseUrl.TrimEnd('/'))"
) | Set-Content -LiteralPath $upstreamEnv -Encoding UTF8

@(
    '# Gateway-only configuration. Colleagues receive sk-internal keys, never this key.'
    'CHATGPT_IMAGE_PORT=8003'
    "CHATGPT_IMAGE_UPSTREAM_API_KEY=$masterKey"
    'CHATGPT_IMAGE_FAILURE_THRESHOLD=3'
    'INTERNAL_AI_QUEUE_CAPACITY=100'
    'INTERNAL_AI_MAX_REQUEST_BYTES=33554432'
    'INTERNAL_AI_TEXT_TIMEOUT_SECONDS=300'
    'INTERNAL_AI_IMAGE_TIMEOUT_SECONDS=900'
    'INTERNAL_AI_EDIT_TIMEOUT_SECONDS=1200'
    'INTERNAL_AI_RETENTION_DAYS=7'
) | Set-Content -LiteralPath $gatewayEnv -Encoding UTF8

$config = Get-Content -Raw -Encoding UTF8 -LiteralPath (
    Join-Path $script:ProjectRoot 'config\chatgpt-config.example.json'
) | ConvertFrom-Json
$config.base_url = $PublicBaseUrl.TrimEnd('/')
$config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $localConfig -Encoding UTF8

Write-Host "ChatGPT2API source is pinned at $($repository.commit)."
Write-Host 'Created three local credential/config files without printing the master key.'
Write-Host 'Run scripts\protect-local-data.ps1, then docker compose -f compose.chatgpt-image.yml up -d --build.'
