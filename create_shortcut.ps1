# Create Desktop Shortcut for CIS (Computer Inventory System)
# This script creates a clickable desktop shortcut for the application

$ErrorActionPreference = "Stop"

try {
    # First, check if the executable exists
    $exePath = "d:\Knnys_Websites\computerparts_inventory_system\dist\main.exe"
    
    if (-not (Test-Path $exePath)) {
        Write-Host "❌ Executable not found: $exePath" -ForegroundColor Red
        Write-Host "Please run build.ps1 first to create the executable" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Run this command in PowerShell:" -ForegroundColor Cyan
        Write-Host "  .\build.ps1" -ForegroundColor Green
        exit 1
    }

    # Create the shortcut
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcutPath = [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'CIS.lnk')
    
    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $exePath
    $Shortcut.WorkingDirectory = "d:\Knnys_Websites\computerparts_inventory_system\dist"
    $Shortcut.Description = "Computer Inventory System - Manage your product inventory with ease"
    
    # Try to set icon if it exists
    $iconPath = "d:\Knnys_Websites\computerparts_inventory_system\assets\app_icon.ico"
    if (Test-Path $iconPath) {
        $Shortcut.IconLocation = $iconPath
    }
    
    $Shortcut.Save()
    
    Write-Host ""
    Write-Host "✅ Desktop shortcut created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📁 Location: $shortcutPath" -ForegroundColor Cyan
    Write-Host "🚀 You can now click 'CIS' on your desktop to launch the application!" -ForegroundColor Cyan
    Write-Host ""

} catch {
    Write-Host "❌ Error creating shortcut: $_" -ForegroundColor Red
    exit 1
}
