Write-Host "Student Budget Tracker sync diagnostics" -ForegroundColor Cyan
Write-Host ""

Write-Host "Network profiles"
Get-NetConnectionProfile |
  Format-Table -Auto Name, InterfaceAlias, NetworkCategory, IPv4Connectivity

Write-Host ""
Write-Host "IPv4 adapters"
Get-NetIPConfiguration |
  Where-Object { $_.IPv4Address } |
  ForEach-Object {
    [pscustomobject]@{
      InterfaceAlias = $_.InterfaceAlias
      IPv4 = ($_.IPv4Address.IPAddress -join ", ")
      Gateway = ($_.IPv4DefaultGateway.NextHop -join ", ")
    }
  } |
  Format-Table -Auto

Write-Host ""
Write-Host "Running app process"
Get-Process -Name StudentBudgetTracker -ErrorAction SilentlyContinue |
  Format-Table -Auto Id, ProcessName, Path

Write-Host ""
Write-Host "Expected listeners"
Write-Host "UDP 38255 is discovery. TCP 38256 is direct sync."
Get-NetUDPEndpoint -LocalPort 38255 -ErrorAction SilentlyContinue |
  Format-Table -Auto LocalAddress, LocalPort, OwningProcess
Get-NetTCPConnection -LocalPort 38256 -ErrorAction SilentlyContinue |
  Format-Table -Auto LocalAddress, LocalPort, State, OwningProcess

Write-Host ""
Write-Host "UDP bind test"
try {
  $udp = [System.Net.Sockets.UdpClient]::new(0)
  Write-Host "Ephemeral UDP bind: OK on port $($udp.Client.LocalEndPoint.Port)" -ForegroundColor Green
  $udp.Close()
} catch {
  Write-Host "Ephemeral UDP bind failed: $($_.Exception.Message)" -ForegroundColor Red
}

try {
  $udpFixed = [System.Net.Sockets.UdpClient]::new(38255)
  Write-Host "UDP 38255 bind: available, so the app is not listening on discovery" -ForegroundColor Yellow
  $udpFixed.Close()
} catch {
  Write-Host "UDP 38255 bind: unavailable, likely already used by the app or another process" -ForegroundColor Green
}

Write-Host ""
Write-Host "Firewall rules mentioning Student Budget Tracker"
netsh advfirewall firewall show rule name=all |
  Select-String -Pattern "StudentBudgetTracker|Student Budget Tracker|38255|38256" -Context 2, 3

Write-Host ""
Write-Host "If detection fails:"
Write-Host "1. Install the latest release on both computers."
Write-Host "2. Fully close and reopen the app on both computers."
Write-Host "3. Use Private network profile for Wi-Fi/Ethernet."
Write-Host "4. Allow inbound UDP 38255 and TCP 38256 for StudentBudgetTracker.exe."
Write-Host "5. Temporarily disable VPN to test local discovery."
