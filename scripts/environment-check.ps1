$ErrorActionPreference = 'Continue'
$projectRoot = Split-Path -Parent $PSScriptRoot

Write-Host 'Project root:' $projectRoot
try {
    Get-CimInstance Win32_OperatingSystem |
        Select-Object Caption, Version, OSArchitecture, TotalVisibleMemorySize, FreePhysicalMemory |
        Format-List
} catch { Write-Warning "Cannot query Windows details: $($_.Exception.Message)" }

try {
    Get-CimInstance Win32_Processor |
        Select-Object Name, NumberOfCores, NumberOfLogicalProcessors |
        Format-List
} catch { Write-Warning "Cannot query CPU details: $($_.Exception.Message)" }

Get-Volume -DriveLetter ([IO.Path]::GetPathRoot($projectRoot).Substring(0, 1)) |
    Select-Object DriveLetter, FileSystem, Size, SizeRemaining |
    Format-List

foreach ($command in @('git', 'python', 'py', 'uv', 'node', 'pnpm', 'go')) {
    $resolved = Get-Command $command -ErrorAction SilentlyContinue
    if (-not $resolved) {
        Write-Host "${command}: NOT FOUND"
        continue
    }
    $versionArgs = if ($command -eq 'go') { @('version') } else { @('--version') }
    Write-Host -NoNewline "${command}: "
    & $resolved.Source @versionArgs
}

Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { -not $_.IPAddress.StartsWith('127.') -and $_.AddressState -eq 'Preferred' } |
    Select-Object InterfaceAlias, IPAddress, PrefixLength, PrefixOrigin |
    Format-Table -AutoSize

Write-Host 'Reserve the selected LAN address in DHCP or configure it according to company IT policy.'
