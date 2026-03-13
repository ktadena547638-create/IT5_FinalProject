# ==============================================================================
# INVENTORY SYSTEM - Build Script
# Version: 1.0.0
# 
# USAGE:
#   .\build.ps1                    # Full build
#   .\build.ps1 -Clean             # Clean build (removes previous artifacts)
#   .\build.ps1 -SkipDeps          # Skip dependency installation
#   .\build.ps1 -Debug             # Build with console window for debugging
#
# ==============================================================================

param(
    [switch]$Clean,
    [switch]$SkipDeps,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

# Configuration
$AppName = "Inventory System"
$Version = "1.0.0"
$SpecFile = "Inventory_System.spec"
$MainScript = "main.py"
$DistDir = "dist"
$BuildDir = "build"

# Colors for output
function Write-Header { param($msg) Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan; Write-Host "║ $msg" -ForegroundColor Cyan; Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan }
function Write-Step { param($msg) Write-Host "→ $msg" -ForegroundColor Yellow }
function Write-Success { param($msg) Write-Host "✓ $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "✗ $msg" -ForegroundColor Red }

# ==============================================================================
# HEADER
# ==============================================================================

Write-Header "$AppName v$Version - BUILD SYSTEM"

# ==============================================================================
# PREREQUISITES CHECK
# ==============================================================================

Write-Step "Checking prerequisites..."

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python: $pythonVersion"
} catch {
    Write-Error "Python not found! Please install Python 3.9+ and add to PATH."
    exit 1
}

# Check if main script exists
if (-not (Test-Path $MainScript)) {
    Write-Error "Main script not found: $MainScript"
    exit 1
}
Write-Success "Main script found: $MainScript"

# ==============================================================================
# CLEAN (Optional)
# ==============================================================================

if ($Clean) {
    Write-Step "Cleaning previous build artifacts..."
    
    if (Test-Path $DistDir) {
        Remove-Item -Recurse -Force $DistDir
        Write-Success "Removed: $DistDir"
    }
    
    if (Test-Path $BuildDir) {
        Remove-Item -Recurse -Force $BuildDir
        Write-Success "Removed: $BuildDir"
    }
    
    # Clean PyInstaller cache
    $cacheDir = "__pycache__"
    if (Test-Path $cacheDir) {
        Remove-Item -Recurse -Force $cacheDir
    }
}

# ==============================================================================
# DEPENDENCIES
# ==============================================================================

if (-not $SkipDeps) {
    Write-Step "Installing/Updating dependencies..."
    
    # Core dependencies
    $packages = @(
        "pyinstaller>=6.0",
        "pillow>=10.0",
        "bcrypt>=4.0"
    )
    
    foreach ($pkg in $packages) {
        Write-Host "  Installing: $pkg" -ForegroundColor Gray
        pip install $pkg --quiet --upgrade
    }
    
    Write-Success "All dependencies installed"
}

# ==============================================================================
# ASSETS CHECK
# ==============================================================================

Write-Step "Checking assets..."

$assetsDir = "assets"
if (-not (Test-Path $assetsDir)) {
    New-Item -ItemType Directory -Path $assetsDir -Force | Out-Null
    Write-Success "Created: $assetsDir"
}

$iconPath = "$assetsDir/icon.ico"
if (-not (Test-Path $iconPath)) {
    Write-Host "  ⚠ No icon found at: $iconPath" -ForegroundColor Yellow
    Write-Host "    The build will continue without a custom icon." -ForegroundColor Yellow
}

# ==============================================================================
# BUILD CONFIGURATION
# ==============================================================================

Write-Step "Configuring build..."

if ($Debug) {
    Write-Host "  Mode: DEBUG (console window enabled)" -ForegroundColor Yellow
    
    # Modify spec for debug build
    if (Test-Path $SpecFile) {
        $specContent = Get-Content $SpecFile -Raw
        $specContent = $specContent -replace "console=False", "console=True"
        $specContent | Set-Content "$SpecFile.debug" -Encoding UTF8
        $buildSpec = "$SpecFile.debug"
    } else {
        $buildSpec = $null
    }
} else {
    Write-Host "  Mode: RELEASE (no console)" -ForegroundColor Gray
    $buildSpec = $SpecFile
}

# ==============================================================================
# PYINSTALLER BUILD
# ==============================================================================

Write-Header "BUILDING EXECUTABLE"

Write-Step "Running PyInstaller..."
Write-Host "  This may take 1-3 minutes..." -ForegroundColor Gray
Write-Host ""

try {
    if ($buildSpec -and (Test-Path $buildSpec)) {
        Write-Host "  Using spec file: $buildSpec" -ForegroundColor Gray
        pyinstaller $buildSpec --clean --noconfirm
    } else {
        Write-Host "  Building with command line options" -ForegroundColor Gray
        $buildArgs = @(
            $MainScript,
            "--name", $AppName,
            "--onefile",
            "--noconsole",
            "--clean",
            "--noconfirm",
            "--add-data", "assets;assets",
            "--hidden-import", "bcrypt",
            "--hidden-import", "PIL._tkinter_finder"
        )
        
        if (Test-Path $iconPath) {
            $buildArgs += "--icon"
            $buildArgs += $iconPath
        }
        
        pyinstaller @buildArgs
    }
    
    Write-Success "PyInstaller completed successfully"
} catch {
    Write-Error "PyInstaller failed: $_"
    exit 1
}

# ==============================================================================
# POST-BUILD
# ==============================================================================

$exePath = "$DistDir/$AppName.exe"

if (Test-Path $exePath) {
    $exeInfo = Get-Item $exePath
    $sizeMB = [math]::Round($exeInfo.Length / 1MB, 2)
    
    Write-Header "BUILD SUCCESSFUL"
    
    Write-Host "  Executable: $exePath" -ForegroundColor Green
    Write-Host "  Size: $sizeMB MB" -ForegroundColor Green
    Write-Host "  Created: $($exeInfo.LastWriteTime)" -ForegroundColor Green
    Write-Host ""
    
    # Clean up debug spec if created
    if ($Debug -and (Test-Path "$SpecFile.debug")) {
        Remove-Item "$SpecFile.debug" -Force
    }
    
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║ NEXT STEPS                                                   ║" -ForegroundColor Cyan
    Write-Host "╠══════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║ 1. Test the executable:                                      ║" -ForegroundColor Cyan
    Write-Host "║    .\dist\Inventory System.exe                               ║" -ForegroundColor White
    Write-Host "║                                                              ║" -ForegroundColor Cyan
    Write-Host "║ 2. Create desktop shortcut:                                  ║" -ForegroundColor Cyan
    Write-Host "║    .\create_shortcut.ps1                                     ║" -ForegroundColor White
    Write-Host "║                                                              ║" -ForegroundColor Cyan
    Write-Host "║ 3. User data location:                                       ║" -ForegroundColor Cyan
    Write-Host "║    %LOCALAPPDATA%\InventorySystem\                           ║" -ForegroundColor White
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    
} else {
    Write-Error "Executable not found at expected location: $exePath"
    exit 1
}
