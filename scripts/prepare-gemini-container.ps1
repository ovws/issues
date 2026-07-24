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
if (-not $repository.vendored) {
    throw 'gemini-api is not marked as vendored in config\upstreams.json.'
}
if (-not (Test-Path -LiteralPath $path -PathType Container)) {
    throw "Vendored Gemini source is missing: $path"
}
if (Test-Path -LiteralPath (Join-Path $path '.git')) {
    throw "Unexpected nested Git metadata in vendored Gemini source: $path\.git"
}

Write-Host "Gemini container source is ready from vendored revision $($repository.commit)."
