# ==============================================================================
# CIS (Computer Inventory System) - Build Script
# Version: 1.0.1
# ==============================================================================

param(
    [switch]$Clean,
    [switch]$SkipDeps,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

# Configuration
$AppName = "CIS"
$Version = "1.0.1"
$MainScript = "main.py"
$DistDir = "dist"
$BuildDir = "build"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CIS v$Version - BUILD SYSTEM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ==============================================================================
# PREREQUISITES CHECK
# ==============================================================================

Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "  [OK] Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Python not found" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $MainScript)) {
    Write-Host "  [ERROR] Main script not found: $MainScript" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Main script found: $MainScript" -ForegroundColor Green

# ==============================================================================
# CLEAN (Optional)
# ==============================================================================

if ($Clean) {
    Write-Host "[2/6] Cleaning previous artifacts..." -ForegroundColor Yellow

    if (Test-Path $DistDir) {
        Remove-Item -Recurse -Force $DistDir
        Write-Host "  [OK] Removed: $DistDir" -ForegroundColor Green
    }

    if (Test-Path $BuildDir) {
        Remove-Item -Recurse -Force $BuildDir
        Write-Host "  [OK] Removed: $BuildDir" -ForegroundColor Green
    }

    if (Test-Path "__pycache__") {
        Remove-Item -Recurse -Force "__pycache__"
    }
} else {
    Write-Host "[2/6] Skipping clean (use -Clean to rebuild from scratch)" -ForegroundColor Gray
}

# ==============================================================================
# DEPENDENCIES
# ==============================================================================

Write-Host "[3/6] Installing dependencies..." -ForegroundColor Yellow

if (-not $SkipDeps) {
    $packages = @(
        "pyinstaller>=6.0",
        "pillow>=10.0",
        "bcrypt>=4.0"
    )

    foreach ($pkg in $packages) {
        pip install $pkg --quiet --upgrade 2>$null
    }
    Write-Host "  [OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Skipping dependency installation" -ForegroundColor Yellow
}

# ==============================================================================
# ASSETS CHECK
# ==============================================================================

Write-Host "[4/6] Checking assets..." -ForegroundColor Yellow

if (-not (Test-Path "assets")) {
    New-Item -ItemType Directory -Path "assets" -Force | Out-Null
}
Write-Host "  [OK] Assets directory ready" -ForegroundColor Green

# ==============================================================================
# PYINSTALLER BUILD
# ==============================================================================

Write-Host "[5/6] Building executable with PyInstaller..." -ForegroundColor Yellow
Write-Host "  (This may take 1-3 minutes...)" -ForegroundColor Gray
Write-Host ""

$buildArgs = @(
    $MainScript,
    "--name=$AppName",
    "--onefile",
    "--noconsole",
    "--clean",
    "--noconfirm",
    "--add-data=assets;assets"
)

if ($Debug) {
    Write-Host "  Command: pyinstaller $($buildArgs -join ' ')" -ForegroundColor DarkGray
}

try {
    python -m PyInstaller @buildArgs
    Write-Host ""
    Write-Host "  [OK] Build completed" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Build failed: $_" -ForegroundColor Red
    exit 1
}

# ==============================================================================
# POST-BUILD VERIFICATION
# ==============================================================================

Write-Host "[6/6] Verifying executable..." -ForegroundColor Yellow

$exePath = Join-Path $DistDir "$AppName.exe"

if (Test-Path $exePath) {
    $exeInfo = Get-Item $exePath
    $sizeMB = [math]::Round($exeInfo.Length / 1MB, 2)

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "BUILD SUCCESSFUL" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Executable: $exePath" -ForegroundColor Green
    Write-Host "Size: $sizeMB MB" -ForegroundColor Green
    Write-Host ""
    Write-Host "NEXT STEPS:" -ForegroundColor Cyan
    Write-Host "  1. Create desktop shortcut: .\create_shortcut.ps1" -ForegroundColor White
    Write-Host "  2. Run the application: .\dist\CIS.exe" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "BUILD FAILED" -ForegroundColor Red
    Write-Host "Executable not found at: $exePath" -ForegroundColor Red
    exit 1
}

Write-Host ""
