# PowerShell Environment Setup for DAVIDSONSFX TRADING COPIER
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  DAVIDSONSFX TRADING COPIER - ENVIRONMENT INITIALIZER   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "[!] Python 3.10+ was not found on your PATH." -ForegroundColor Yellow
    Write-Host "[*] Please install Python from https://www.python.org/downloads/ (Make sure to check 'Add Python to PATH')" -ForegroundColor White
    exit 1
}

Write-Host "[+] Python detected: $($pythonCmd.Source)" -ForegroundColor Green

# 2. Create Virtual Environment
$venvPath = Join-Path $PSScriptRoot "..\.venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "[*] Creating virtual environment at .venv..." -ForegroundColor Cyan
    & $pythonCmd.Source -m venv $venvPath
} else {
    Write-Host "[+] Existing virtual environment found." -ForegroundColor Green
}

# 3. Install Requirements
$pipPath = Join-Path $venvPath "Scripts\pip.exe"
$reqPath = Join-Path $PSScriptRoot "..\backend\requirements.txt"

Write-Host "[*] Installing backend dependencies..." -ForegroundColor Cyan
& $pipPath install -r $reqPath

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  SETUP COMPLETE! You can now start the server with:     " -ForegroundColor Green
Write-Host "  scripts\start_davidsonsfx.bat                          " -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green

