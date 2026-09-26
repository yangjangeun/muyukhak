# 보조 트리거: PC가 켜져 있으면 07:25에 워크플로를 한 번 더 시작한다.
# 오늘 이미 보냈으면 워크플로의 gate가 알아서 건너뛴다.
$ErrorActionPreference = "Stop"

$logDir = "d:\muyukhak\.trigger-logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("trigger-{0:yyyyMMdd}.log" -f (Get-Date))

function Write-Log([string]$msg) {
    $line = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg
    Add-Content -Path $log -Value $line -Encoding UTF8
    Write-Output $line
}

$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) { $gh = (Get-Command gh -ErrorAction Stop).Source }

try {
    & $gh workflow run "Daily Trade Study" --repo yangjangeun/muyukhak
    if ($LASTEXITCODE -ne 0) { throw "workflow run failed: $LASTEXITCODE" }
    Write-Log "Dispatched"
    exit 0
}
catch {
    Write-Log "ERROR: $_"
    exit 1
}
