param(
    [Parameter(Mandatory)]
    [string]$LanCidr
)

$ErrorActionPreference = 'Stop'
if ($LanCidr -notmatch '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)\d{1,3}\.\d{1,3}/([8-9]|[12]\d|3[0-2])$') {
    throw 'LanCidr must be an RFC1918 IPv4 CIDR, for example 192.168.10.0/24.'
}

$ports = @(8001, 8002, 8003)
foreach ($port in $ports) {
    $name = "Internal AI API TCP $port"
    $existing = Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue
    if ($existing) { Remove-NetFirewallRule -DisplayName $name }
    New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort $port -RemoteAddress $LanCidr -Profile Domain,Private | Out-Null
    Write-Host "Allowed $LanCidr -> TCP $port on Domain/Private profiles."
}

