# Inventory System - Deployment Guide
## Version 1.0.0

---

## 📁 Project Structure

```
computerparts_inventory_system/
├── main.py                 # Main application source
├── Inventory_System.spec   # PyInstaller specification file
├── build.ps1               # Automated build script
├── create_shortcut.ps1     # Desktop shortcut creator
├── requirements.txt        # Python dependencies
├── version_info.txt        # Windows version metadata
│
├── assets/
│   ├── icon.ico            # Application icon (optional)
│   ├── README_ICON.txt     # Icon creation instructions
│   └── products/           # Product images
│
├── data/                   # Database files (auto-created)
├── logs/                   # Log files
├── reports/                # Generated reports
│
├── dist/                   # Build output (created by PyInstaller)
│   └── Inventory System.exe
│
└── build/                  # Temporary build files
```

---

## 🚀 Quick Start Build

### Option 1: One-Command Build (Recommended)

```powershell
# Navigate to project directory
cd "d:\Knnys_Websites\computerparts_inventory_system"

# Run the build script
.\build.ps1
```

### Option 2: Manual PyInstaller Command

```powershell
# Install dependencies
pip install pyinstaller pillow bcrypt

# Build with spec file
pyinstaller Inventory_System.spec --clean --noconfirm

# OR build directly
pyinstaller main.py --name "Inventory System" --onefile --noconsole --add-data "assets;assets"
```

---

## 🎨 Adding a Custom Icon

1. **Create your icon** (256x256 recommended) using:
   - [IcoConvert](https://icoconvert.com/) (free online)
   - [Convertico](https://convertico.com/) (free online)
   - GIMP → Export As → .ico

2. **Save as:** `assets/icon.ico`

3. **Rebuild:** `.\build.ps1 -Clean`

---

## 📦 Build Options

| Command | Description |
|---------|-------------|
| `.\build.ps1` | Standard release build |
| `.\build.ps1 -Clean` | Clean build (removes old artifacts) |
| `.\build.ps1 -Debug` | Debug build (shows console window) |
| `.\build.ps1 -SkipDeps` | Skip dependency installation |

---

## 📍 User Data Locations

When running as an executable, user data is stored in:

```
%LOCALAPPDATA%\InventorySystem\
├── inventory.db          # SQLite database
├── products/             # Product images
└── logs/                 # Application logs
```

---

## 🔑 Default Login Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Administrator |

**Important:** Change the default password after first login!

---

## 🔧 Troubleshooting

### "Python not found" error
- Install Python 3.9+ from [python.org](https://python.org)
- Ensure "Add Python to PATH" is checked during installation

### "Module not found" errors
```powershell
pip install -r requirements.txt
```

### Build produces large executable
- This is normal for PyInstaller one-file builds
- Expected size: 30-50 MB

### Application won't start after build
- Run with debug mode: `.\build.ps1 -Debug`
- Check the console output for errors

---

## 📋 Features

- **Inventory Management:** Add, edit, delete products
- **Business Intelligence:** Health scores, profit margins, aging alerts
- **Security:** BCrypt password hashing, role-based access
- **Reports:** CSV export, inventory reports
- **Dark Theme:** Professional modern UI
