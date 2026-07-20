Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$runDirectory = Join-Path $projectRoot 'run'
$resultFile = Join-Path $runDirectory 'gemini-acl-setup.log'

New-Item -ItemType Directory -Force -Path $runDirectory | Out-Null

function Grant-ModifyAccess {
    param(
        [Parameter(Mandatory)][string]$Path,
        [switch]$Recursive
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Runtime path does not exist: $Path"
    }

    $item = Get-Item -LiteralPath $Path
    $grant = if ($item.PSIsContainer) {
        "${runtimeUser}:(OI)(CI)M"
    } else {
        "${runtimeUser}:M"
    }
    $arguments = @($Path, '/grant:r', $grant)
    if ($Recursive) { $arguments += @('/T', '/C') }
    $output = & icacls.exe @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "icacls failed for $Path`: $($output -join ' ')"
    }
}

try {
    Grant-ModifyAccess -Path (Join-Path $projectRoot 'data')
    Grant-ModifyAccess -Path (Join-Path $projectRoot 'data\media\gemini') -Recursive
    Grant-ModifyAccess -Path (Join-Path $projectRoot 'logs\gemini') -Recursive
    Grant-ModifyAccess -Path (Join-Path $projectRoot 'config\gemini-cookies.local.json')
    Set-Content -LiteralPath $resultFile -Encoding UTF8 `
        -Value "OK: runtime access granted to $runtimeUser"
    exit 0
} catch {
    Set-Content -LiteralPath $resultFile -Encoding UTF8 `
        -Value "ERROR: $($_.Exception.Message)"
    exit 1
}
