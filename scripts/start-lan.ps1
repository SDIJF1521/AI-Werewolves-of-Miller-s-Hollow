param(
    [int]$Port = 8000,
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Dist = Join-Path $Frontend "dist\index.html"

Write-Host ""
Write-Host "  AI 狼人杀 · 局域网启动" -ForegroundColor Yellow
Write-Host "  --------------------------------"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "未找到 uv，请先安装：https://docs.astral.sh/uv/"
}

$env:UV_CACHE_DIR = Join-Path $Backend ".uv-cache"

if ($Rebuild -or -not (Test-Path $Dist)) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "前端尚未构建，且未找到 npm。请先安装 Node.js 20+。"
    }
    Push-Location $Frontend
    try {
        $env:TMP = Join-Path $Frontend ".tmp"
        $env:TEMP = $env:TMP
        New-Item -ItemType Directory -Force -Path $env:TMP | Out-Null
        $env:npm_config_cache = Join-Path $Frontend ".npm-cache"
        if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
            Write-Host "  安装前端依赖..." -ForegroundColor DarkGray
            npm install --ignore-scripts
        }
        Write-Host "  构建前端..." -ForegroundColor DarkGray
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "前端构建失败" }
    }
    finally {
        Pop-Location
    }
}

$ips = @()
try {
    $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.PrefixOrigin -ne "WellKnown"
        } |
        Select-Object -ExpandProperty IPAddress -Unique
} catch {
    try {
        $ips = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
            Where-Object { $_.AddressFamily -eq "InterNetwork" -and $_.ToString() -notlike "127.*" } |
            ForEach-Object { $_.ToString() }
    } catch {}
}

Write-Host ""
if ($ips.Count -gt 0) {
    Write-Host "  同一局域网的朋友可访问：" -ForegroundColor Green
    foreach ($ip in $ips) {
        Write-Host "    http://${ip}:$Port" -ForegroundColor Cyan
    }
} else {
    Write-Host "  未自动识别到局域网 IPv4，请用 ipconfig 查看本机 IP。" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  本机访问：http://127.0.0.1:$Port" -ForegroundColor DarkGray
Write-Host "  接口文档：http://127.0.0.1:$Port/docs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  如果局域网无法访问，请用管理员 PowerShell 放行端口：" -ForegroundColor Yellow
Write-Host "    New-NetFirewallRule -DisplayName 'AI Werewolf $Port' -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -Profile Any" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  注意：局域网 HTTP 可以使用文字/对局；浏览器麦克风需要 HTTPS。" -ForegroundColor Yellow
Write-Host "  要开语音，推荐另开一个终端运行：" -ForegroundColor Yellow
Write-Host "    cloudflared tunnel --url http://127.0.0.1:$Port" -ForegroundColor DarkGray
Write-Host ""

Push-Location $Backend
try {
    uv run uvicorn werewolf.interfaces.http.app:app `
        --app-dir src `
        --host 0.0.0.0 `
        --port $Port `
        --proxy-headers `
        --forwarded-allow-ips=*
}
finally {
    Pop-Location
}
