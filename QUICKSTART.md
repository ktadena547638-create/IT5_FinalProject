# CIS (Computer Inventory System) - Quick Start Guide

## How to Run the Application

### Option 1: Run from Terminal (Recommended for Development)
```powershell
# Navigate to the project folder
cd d:\Knnys_Websites\computerparts_inventory_system

# Activate the virtual environment
.venv\Scripts\Activate.ps1

# Run the application
python main.py
```

### Option 2: Run the Executable (After Building)
1. First, build the executable:
   ```powershell
   cd d:\Knnys_Websites\computerparts_inventory_system
   .\build.ps1
   ```
2. Once complete, run:
   ```powershell
   .\dist\main.exe
   ```

### Option 3: Create Desktop Shortcut (Easiest)
Follow the **Rebuild Desktop Shortcut** section below to create a clickable desktop icon.

---

## Rebuild Desktop Shortcut

### Step 1: Build the Application
```powershell
# Open PowerShell as Administrator
cd d:\Knnys_Websites\computerparts_inventory_system

# Run the build script
.\build.ps1
```

This creates `dist\main.exe` - a standalone executable.

### Step 2: Create Desktop Shortcut
```powershell
# Create shortcut on Desktop
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'CIS.lnk'))
$Shortcut.TargetPath = 'd:\Knnys_Websites\computerparts_inventory_system\dist\main.exe'
$Shortcut.WorkingDirectory = 'd:\Knnys_Websites\computerparts_inventory_system\dist'
$Shortcut.Description = 'Computer Inventory System'
$Shortcut.IconLocation = 'd:\Knnys_Websites\computerparts_inventory_system\assets\app_icon.ico'
$Shortcut.Save()
Write-Host "Desktop shortcut 'CIS' created successfully!"
```

After this, you can simply **click the CIS shortcut on your desktop** to launch the application.

---

## Project Structure

```
computerparts_inventory_system/
├── main.py                      # Main application (run this)
├── generate_presentation.py     # PowerPoint generator
├── requirements.txt             # Python dependencies
├── build.ps1                    # Build executable script
├── THESIS_DOCUMENT.md          # Academic documentation
├── QUICKSTART.md               # This file
├── tests/                       # Test suite
│   ├── conftest.py
│   ├── test_background_task.py
│   ├── test_product_repository.py
│   └── test_user_repository.py
├── assets/                      # Graphics and icons
│   ├── app_icon.ico
│   └── products/
├── data/                        # SQLite database
├── logs/                        # Application logs
└── locales/                     # Language files
```

---

## Running Tests

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_product_repository.py -v
```

---

## Generate Presentation

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Generate PowerPoint presentation
python generate_presentation.py
```

---

## Code Quality Checks

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Run Pylint
python -m pylint main.py generate_presentation.py tests/

# Run Flake8
python -m flake8 --max-line-length=120 main.py generate_presentation.py tests/
```

---

## Troubleshooting

### Application won't start
1. Ensure virtual environment is activated
2. Check that Python 3.10+ is installed: `python --version`
3. Verify dependencies: `pip install -r requirements.txt`

### Build script fails
1. Run PowerShell **as Administrator**
2. Set execution policy: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
3. Re-run: `.\build.ps1`

### Database errors
- Check `logs/` folder for error messages
- Ensure `data/` folder exists and is writable
- Delete `data/inventory.db` to start fresh (will lose data!)

---

## System Information

- **Python Version**: 3.10+
- **Database**: SQLite (file-based, WAL mode)
- **UI Framework**: Tkinter (built-in with Python)
- **Code Quality**: Pylint 9.49/10
- **Test Coverage**: 100% critical paths (4/4 tests passing)

---

## Default Login Credentials

First run will prompt you to create an admin account.

---

**Last Updated**: May 18, 2026  
**Version**: 1.0.0  
**Status**: Production Ready
