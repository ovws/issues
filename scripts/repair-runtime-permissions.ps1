#Requires -RunAsAdministrator

param(
    [Parameter(Mandatory)]
    [string]$RuntimeRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)

$resolvedRoot = (Resolve-Path -LiteralPath $RuntimeRoot -ErrorAction Stop).Path
$rootPath = [IO.Path]::GetPathRoot($resolvedRoot)
if ($resolvedRoot.TrimEnd('\') -eq $rootPath.TrimEnd('\')) {
    throw 'RuntimeRoot cannot be a drive root.'
}
if (-not (Test-Path -LiteralPath (Join-Path $resolvedRoot '.env') -PathType Leaf)) {
    throw "RuntimeRoot does not contain .env: $resolvedRoot"
}

$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$targets = @(
    [pscustomobject]@{ Relative = 'data'; Recursive = $true }
    [pscustomobject]@{ Relative = 'logs'; Recursive = $true }
    [pscustomobject]@{ Relative = 'run'; Recursive = $true }
    [pscustomobject]@{ Relative = 'upstream\grok2api\data'; Recursive = $true }
    [pscustomobject]@{ Relative = 'upstream\chatgpt2api\data'; Recursive = $true }
)

foreach ($target in $targets) {
    $path = Join-Path $resolvedRoot $target.Relative
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "[跳过] 不存在：$($target.Relative)"
        continue
    }

    $resolvedTarget = (Resolve-Path -LiteralPath $path).Path
    $expectedPrefix = $resolvedRoot.TrimEnd('\') + '\'
    if (-not $resolvedTarget.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to change permissions outside RuntimeRoot: $resolvedTarget"
    }

    Write-Host "[修复] $($target.Relative)"
    if ($target.Recursive) {
        & takeown.exe /F $resolvedTarget /R /D Y | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "takeown failed: $($target.Relative)" }
        # Re-enable inheritance on every child first. Some historical runtime files
        # can have a protected, empty DACL that a folder-only grant cannot repair.
        & icacls.exe $resolvedTarget /inheritance:e /T /C | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "icacls inheritance repair failed: $($target.Relative)" }
        # Protect the runtime root from broad repository ACLs. Descendants now
        # inherit only these three explicit, inheritable full-control entries.
        & icacls.exe $resolvedTarget /inheritance:r | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "icacls root protection failed: $($target.Relative)" }
        & icacls.exe $resolvedTarget /grant:r `
            "${currentUser}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' `
            '*S-1-5-32-544:(OI)(CI)F' /C | Out-Null
    } else {
        & takeown.exe /F $resolvedTarget | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "takeown failed: $($target.Relative)" }
        & icacls.exe $resolvedTarget /inheritance:r /grant:r `
            "${currentUser}:F" '*S-1-5-18:F' '*S-1-5-32-544:F' /C | Out-Null
    }
    if ($LASTEXITCODE -ne 0) { throw "icacls failed: $($target.Relative)" }
}

Write-Host 'data、logs、run 与 Grok/ChatGPT 上游数据目录权限已修复；未删除、替换或读取任何运行内容。' -ForegroundColor Green
