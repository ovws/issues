param(
    [switch]$RefreshPinnedCommit
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Initialize-ProjectLayout

$manifestPath = Join-Path $script:ProjectRoot 'config\upstreams.json'
$repository = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath |
    ConvertFrom-Json |
    Where-Object { $_.name -eq 'gemini-api' } |
    Select-Object -First 1
if (-not $repository) { throw 'gemini-api is missing from config\upstreams.json.' }

$path = Join-Path $script:ProjectRoot $repository.path
$safePath = $path.Replace('\', '/')
if (-not (Test-Path -LiteralPath (Join-Path $path '.git'))) {
    git clone --no-checkout $repository.url $path
    if ($LASTEXITCODE -ne 0) { throw "Failed to clone $($repository.url)." }
}

$dirty = git -c "safe.directory=$safePath" -C $path status --porcelain
if ($dirty) {
    throw "Refusing to change a dirty Gemini checkout: $path"
}

$hasCommit = git -c "safe.directory=$safePath" -C $path cat-file -e "$($repository.commit)^{commit}" 2>$null
if ($LASTEXITCODE -ne 0 -or $RefreshPinnedCommit) {
    git -c "safe.directory=$safePath" -C $path fetch --depth 1 private $repository.commit
    if ($LASTEXITCODE -ne 0) {
        git -c "safe.directory=$safePath" -C $path fetch --depth 1 origin $repository.commit
    }
    if ($LASTEXITCODE -ne 0) { throw "Failed to fetch pinned Gemini commit." }
}

$current = git -c "safe.directory=$safePath" -C $path rev-parse HEAD
if ($current -ne $repository.commit) {
    git -c "safe.directory=$safePath" -C $path checkout --detach $repository.commit
    if ($LASTEXITCODE -ne 0) { throw "Failed to check out pinned Gemini commit." }
}

Write-Host "Gemini container source is ready at pinned commit $($repository.commit)."
