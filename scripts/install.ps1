param(
    [switch]$SkipGrokBuild,
    [switch]$SkipChatGPTFrontend
)

. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-ProjectLayout

# Keep downloaded runtimes and build caches inside this project as required by WK-80.
[Environment]::SetEnvironmentVariable('UV_CACHE_DIR', (Join-Path $script:ProjectRoot '.uv-cache'), 'Process')
[Environment]::SetEnvironmentVariable('UV_PYTHON_INSTALL_DIR', (Join-Path $script:ProjectRoot '.uv-python'), 'Process')
[Environment]::SetEnvironmentVariable('npm_config_cache', (Join-Path $script:ProjectRoot '.npm-cache'), 'Process')
[Environment]::SetEnvironmentVariable('GOCACHE', (Join-Path $script:ProjectRoot '.go-cache'), 'Process')
[Environment]::SetEnvironmentVariable('GOMODCACHE', (Join-Path $script:ProjectRoot '.go-mod-cache'), 'Process')

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required. Install it from https://docs.astral.sh/uv/ and rerun this script.'
}

$manifestPath = Join-Path $script:ProjectRoot 'config\upstreams.json'
$repositories = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
foreach ($repository in $repositories) {
    $path = Join-Path $script:ProjectRoot $repository.path
    if (-not $repository.vendored) {
        throw "$($repository.name) is not marked as vendored in config\upstreams.json."
    }
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        throw "Vendored source is missing: $($repository.path). Restore it from this repository."
    }
    if (Test-Path -LiteralPath (Join-Path $path '.git')) {
        throw "Unexpected nested Git metadata in vendored source: $($repository.path)\.git"
    }
}

Push-Location $script:ProjectRoot
try {
    uv sync --frozen --python 3.13 --extra dev
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install the root Python environment.' }
} finally { Pop-Location }

$chatgptRoot = Join-Path $script:ProjectRoot 'upstream\chatgpt2api'
Push-Location $chatgptRoot
try {
    uv sync --python 3.13 --no-dev
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install ChatGPT2API.' }
} finally { Pop-Location }

if (-not $SkipChatGPTFrontend) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw 'npm is required to build the ChatGPT2API local admin frontend.'
    }
    $chatgptWeb = Join-Path $chatgptRoot 'web'
    Push-Location $chatgptWeb
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw 'Failed to install ChatGPT2API frontend packages.' }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Failed to build ChatGPT2API frontend.' }
    } finally { Pop-Location }
    $webDist = Join-Path $chatgptRoot 'web_dist'
    New-Item -ItemType Directory -Force -Path $webDist | Out-Null
    Copy-Item -Path (Join-Path $chatgptWeb 'out\*') -Destination $webDist -Recurse -Force
}

$grokRoot = Join-Path $script:ProjectRoot 'upstream\grok2api'
$grokConfig = Join-Path $grokRoot 'config.yaml'
if (-not (Test-Path -LiteralPath $grokConfig)) {
    $content = Get-Content -Raw -Encoding UTF8 (Join-Path $grokRoot 'config.example.yaml')
    $content.Replace('127.0.0.1:8000', '127.0.0.1:18001') |
        Set-Content -LiteralPath $grokConfig -Encoding UTF8
    Write-Warning 'Created upstream\grok2api\config.yaml. Replace every required secret before starting.'
}

if (-not $SkipGrokBuild) {
    if (-not (Get-Command go -ErrorAction SilentlyContinue)) {
        throw 'Grok2API currently requires Go 1.26. Install Go and rerun, or use -SkipGrokBuild.'
    }
    $frontend = Join-Path $grokRoot 'frontend'
    Push-Location $frontend
    try {
        if (Get-Command pnpm -ErrorAction SilentlyContinue) {
            pnpm install --frozen-lockfile --store-dir (Join-Path $script:ProjectRoot '.pnpm-store')
            pnpm build
        } else {
            throw 'pnpm is required to build the Grok admin frontend.'
        }
    } finally { Pop-Location }
    $bin = Join-Path $grokRoot 'bin'
    New-Item -ItemType Directory -Force -Path $bin | Out-Null
    Push-Location (Join-Path $grokRoot 'backend')
    try {
        go build -o (Join-Path $bin 'grok2api.exe') ./cmd/grok2api
        if ($LASTEXITCODE -ne 0) { throw 'Failed to build Grok2API.' }
    } finally { Pop-Location }
}

if (-not (Test-Path -LiteralPath $script:EnvFile)) {
    Copy-Item -LiteralPath (Join-Path $script:ProjectRoot '.env.example') -Destination $script:EnvFile
    Write-Warning 'Created .env. Replace upstream keys and Gemini cookie values before starting.'
}

Write-Host 'Installation complete. Next: edit .env and local credential files, then run scripts\start-all.ps1.'
