# 매일 아침 GitHub Actions 워크플로를 강제 실행합니다.
# (GitHub 내장 cron이 누락되는 경우를 보완)

$ErrorActionPreference = "Stop"

$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
    $gh = (Get-Command gh -ErrorAction Stop).Source
}

$repo = "yangjangeun/muyukhak"
$workflow = "Daily Trade Study"
$logDir = Join-Path $PSScriptRoot "..\.trigger-logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("trigger-{0:yyyyMMdd}.log" -f (Get-Date))

function Write-Log([string]$msg) {
    $line = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg
    Add-Content -Path $log -Value $line -Encoding UTF8
    Write-Output $line
}

try {
    Write-Log "Trigger start: $workflow @ $repo"
    & $gh workflow run $workflow --repo $repo
    if ($LASTEXITCODE -ne 0) {
        throw "gh workflow run failed with exit $LASTEXITCODE"
    }
    Write-Log "Trigger OK"
    exit 0
}
catch {
    Write-Log "ERROR: $_"
    exit 1
}
