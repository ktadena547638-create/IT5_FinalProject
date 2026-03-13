# ==============================================================================
# INVENTORY SYSTEM - Enterprise Inventory Management System
# ==============================================================================
# 
# Course:       IT5L (2868)
# Professor:    Modesto C. Tarrazona
# Student:      Kenny Ray M. Tadena
# Date:         February 2026
# 
# Version:      1.0
# 
# Architecture: MVC Pattern with Repository Layer
# Security:     BCrypt Password Hashing (12 rounds), Role-Based Access Control
# Database:     SQLite with WAL Mode & Connection Pooling
# UI:           Tkinter with Professional Dark Theme
# 
# ==============================================================================

from __future__ import annotations
import sqlite3
import os
import sys
import csv
import shutil
import random
import logging
import weakref
import gc
import json
import time
import threading
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Optional, List, Callable, Dict, Any, ClassVar, Final, Protocol, Tuple
from contextlib import contextmanager
from abc import ABC, abstractmethod
from tkinter import messagebox, filedialog, ttk
import tkinter as tk
from PIL import Image, ImageTk
import bcrypt

# Optional database drivers (installed if available)
try:
    import psycopg2
    from psycopg2 import pool as pg_pool
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

try:
    import mysql.connector
    from mysql.connector import pooling as mysql_pool
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False


# ==============================================================================
# SQLITE3 DATETIME ADAPTERS (Python 3.12+ Compatibility)
# ==============================================================================
# Register adapters/converters to handle datetime objects natively in SQLite.
# This eliminates DeprecationWarning for default datetime handling.

def _adapt_datetime(dt: datetime) -> str:
    """Convert datetime to ISO format string for SQLite storage."""
    return dt.isoformat()

def _convert_datetime(data: bytes) -> datetime:
    """Convert ISO format string from SQLite to datetime object."""
    return datetime.fromisoformat(data.decode())

sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_converter("TIMESTAMP", _convert_datetime)


# ==============================================================================
# PYINSTALLER PATH RESOLUTION & CROSS-PLATFORM DPI AWARENESS
# ==============================================================================

def get_base_path() -> Path:
    """Get base path for bundled resources (PyInstaller compatible)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def get_app_data_path() -> Path:
    """
    Get portable application data directory.
    
    Uses relative pathing so data/, logs/, and assets/ folders are created
    in the same directory as the executable or script—making the app fully
    portable across different machines with zero manual configuration.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller exe: use the directory containing the .exe
        app_dir = Path(sys.executable).parent
    else:
        # Running as script: use the script's directory
        app_dir = Path(__file__).parent
    
    return app_dir


def get_screen_scale_factor() -> float:
    """
    Cross-platform screen scale factor detection.
    Returns a multiplier for font sizes and paddings (1.0 = 96 DPI baseline).
    """
    try:
        if sys.platform == 'win32':
            import ctypes
            # Get DPI from system metrics
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return dpi / 96.0
        
        elif sys.platform == 'darwin':  # macOS
            # macOS typically uses 2x scaling for Retina
            try:
                from AppKit import NSScreen
                return NSScreen.mainScreen().backingScaleFactor()
            except ImportError:
                return 2.0 if os.popen('system_profiler SPDisplaysDataType | grep -i retina').read() else 1.0
        
        else:  # Linux/BSD
            # Try Xorg xdpyinfo or GDK
            try:
                import subprocess
                result = subprocess.run(['xdpyinfo'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'resolution' in line.lower():
                        dpi_match = re.search(r'(\d+)x\d+ dots', line)
                        if dpi_match:
                            return int(dpi_match.group(1)) / 96.0
            except (FileNotFoundError, subprocess.SubprocessError):
                pass
            
            # Fallback: Check GDK_SCALE environment variable
            gdk_scale = os.environ.get('GDK_SCALE', '1')
            return float(gdk_scale)
    
    except Exception:
        pass
    
    return 1.0


def setup_dpi_awareness() -> float:
    """
    Enable DPI awareness across all platforms for crisp rendering.
    
    Returns the detected scale factor for UI scaling.
    Must be called BEFORE creating any Tk windows.
    """
    scale = 1.0
    
    if sys.platform == 'win32':
        try:
            import ctypes
            # SetProcessDpiAwareness levels:
            # 0 = DPI unaware
            # 1 = System DPI aware
            # 2 = Per-monitor DPI aware (best quality)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            scale = get_screen_scale_factor()
        except (AttributeError, OSError):
            # Fallback for older Windows versions (pre-Windows 8.1)
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                scale = get_screen_scale_factor()
            except (AttributeError, OSError):
                pass
    
    elif sys.platform == 'darwin':
        # macOS handles DPI automatically, but we detect scale for fonts
        scale = get_screen_scale_factor()
    
    else:  # Linux/BSD
        # Tk on Linux respects system DPI settings
        scale = get_screen_scale_factor()
    
    return scale


# Global scale factor for UI elements
SCALE_FACTOR: float = 1.0

# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================

class Config:
    """Centralized configuration management"""
    APP_NAME: Final[str] = "Inventory System"
    APP_VERSION: Final[str] = "1.0.0"
    
    # Portable application data paths (relative to exe/script location)
    _APP_DATA: ClassVar[Path] = get_app_data_path()
    DB_PATH: ClassVar[Path] = _APP_DATA / "data" / "inventory.db"
    ASSETS_PATH: ClassVar[Path] = _APP_DATA / "assets" / "products"
    LOG_PATH: ClassVar[Path] = _APP_DATA / "logs" / "app.log"
    LOCALES_PATH: ClassVar[Path] = _APP_DATA / "locales"
    CONFIG_FILE: ClassVar[Path] = _APP_DATA / "config.json"
    
    # Bundled resources path (for PyInstaller internal resources)
    RESOURCES_PATH: ClassVar[Path] = get_base_path() / "assets"
    
    # ==== DATABASE CONFIGURATION (Multi-Driver Support) ====
    # Supported drivers: sqlite, postgresql, mysql
    # Default: SQLite (portable, single-machine)
    # For cloud: Set DB_DRIVER and DB_CONNECTION_STRING
    DB_DRIVER: str = "sqlite"  # "sqlite" | "postgresql" | "mysql"
    DB_CONNECTION_STRING: str = ""  # e.g., "host=localhost dbname=inventory user=admin password=secret"
    DB_POOL_SIZE: int = 5  # Connection pool size for PostgreSQL/MySQL
    
    # ==== PAGINATION (Scalability for 100k+ products) ====
    PAGE_SIZE: int = 100  # Products per page in Treeview
    LAZY_LOAD_THRESHOLD: int = 1000  # Enable lazy-loading above this count
    
    # ==== BARCODE SCANNER SETTINGS ====
    BARCODE_DETECTION_MS: int = 50  # Max ms between keystrokes for scanner detection
    BARCODE_MIN_LENGTH: int = 6  # Minimum characters for valid barcode
    
    # ==== INTERNATIONALIZATION ====
    DEFAULT_LANGUAGE: str = "en"  # Default language code
    
    # Business Intelligence Thresholds
    LOW_STOCK_THRESHOLD: Final[int] = 5
    CRITICAL_STOCK_THRESHOLD: Final[int] = 2
    AGING_THRESHOLD_DAYS: Final[int] = 90  # Depreciation alert threshold
    LOW_MARGIN_THRESHOLD: Final[float] = 15.0  # Minimum acceptable margin %
    SLOW_MOVER_DAYS: Final[int] = 60  # Days without sale = slow mover
    MAX_IMAGE_SIZE_MB = 5
    SUPPORTED_IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".webp")
    
    # UI Theme - Professional Dark Theme
    THEME = {
        "bg_primary": "#0f172a",      # Slate 900
        "bg_secondary": "#1e293b",     # Slate 800
        "bg_tertiary": "#334155",      # Slate 700
        "bg_card": "#1e293b",
        "fg_primary": "#f8fafc",       # Slate 50
        "fg_secondary": "#94a3b8",     # Slate 400
        "fg_muted": "#64748b",         # Slate 500
        "accent": "#3b82f6",           # Blue 500
        "accent_hover": "#2563eb",     # Blue 600
        "success": "#10b981",          # Emerald 500
        "warning": "#f59e0b",          # Amber 500
        "danger": "#ef4444",           # Red 500
        "border": "#334155",
        "input_bg": "#0f172a",
        "table_stripe": "#1a2332",
    }
    
    CATEGORIES = [
        "Processors (CPU)",
        "Graphics Cards (GPU)", 
        "Motherboards",
        "Memory (RAM)",
        "Storage (SSD/HDD)",
        "Power Supplies (PSU)",
        "PC Cases",
        "Cooling Solutions",
        "Peripherals",
        "Networking",
        "Monitors",
        "Accessories",
    ]

# Setup logging with fallback if file logging fails
try:
    Config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_PATH),
            logging.StreamHandler()
        ]
    )
except (PermissionError, OSError):
    # Fallback to console-only logging if file access fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[logging.StreamHandler()]
    )
logger = logging.getLogger(__name__)

# ==============================================================================
# INTERNATIONALIZATION (i18n) SYSTEM
# ==============================================================================

class I18n:
    """
    Multilingual architecture with JSON-based language dictionaries.
    
    Usage:
        i18n = I18n()
        print(i18n.t("login.title"))  # "Sign In"
        print(i18n.t("messages.saved", name="Widget"))  # "Product 'Widget' saved successfully."
    """
    
    _instance: Optional['I18n'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._current_lang: str = Config.DEFAULT_LANGUAGE
        self._translations: Dict[str, Any] = {}
        self._fallback: Dict[str, Any] = {}
        
        # Load default language
        self._load_language(self._current_lang)
        self._initialized = True
    
    def _load_language(self, lang_code: str) -> bool:
        """Load language file from locales directory."""
        lang_file = Config.LOCALES_PATH / f"{lang_code}.json"
        
        # Also check bundled resources for PyInstaller
        if not lang_file.exists():
            lang_file = Config.RESOURCES_PATH / "locales" / f"{lang_code}.json"
        
        if not lang_file.exists():
            # Generate default English if not found
            self._generate_default_locale()
            lang_file = Config.LOCALES_PATH / f"{lang_code}.json"
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
            
            # Store English as fallback
            if lang_code == 'en':
                self._fallback = self._translations.copy()
            
            logger.info(f"Loaded language: {lang_code}")
            return True
        
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load language '{lang_code}': {e}")
            return False
    
    def _generate_default_locale(self) -> None:
        """Generate default English locale if not found."""
        Config.LOCALES_PATH.mkdir(parents=True, exist_ok=True)
        
        default_translations = {
            "meta": {"language": "English", "code": "en", "version": "1.0.0"},
            "app": {"name": "INVENTORY", "name_sub": "SYSTEM", "tagline": "Enterprise Inventory Management"},
            "login": {"title": "Sign In", "username": "Username", "password": "Password", "submit": "Sign In"},
            "dashboard": {"title": "Inventory Dashboard", "refresh": "Refresh", "clear": "Clear"},
            "messages": {"success": "Success", "error": "Error", "warning": "Warning"}
        }
        
        with open(Config.LOCALES_PATH / "en.json", 'w', encoding='utf-8') as f:
            json.dump(default_translations, f, indent=4)
    
    def t(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language.
        
        Args:
            key: Dot-notation key (e.g., "login.title", "messages.saved")
            **kwargs: Formatting arguments (e.g., name="Widget")
        
        Returns:
            Translated string, or key if not found.
        """
        parts = key.split('.')
        value = self._translations
        
        # Navigate through nested keys
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                # Try fallback
                value = self._fallback
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return key  # Key not found
                break
        
        if isinstance(value, str):
            # Format with kwargs
            try:
                return value.format(**kwargs) if kwargs else value
            except KeyError:
                return value
        
        return key
    
    def set_language(self, lang_code: str) -> bool:
        """Switch to a different language."""
        if self._load_language(lang_code):
            self._current_lang = lang_code
            return True
        return False
    
    def get_available_languages(self) -> List[str]:
        """Get list of available language codes."""
        languages = []
        
        for path in [Config.LOCALES_PATH, Config.RESOURCES_PATH / "locales"]:
            if path.exists():
                for file in path.glob("*.json"):
                    lang_code = file.stem
                    if lang_code not in languages:
                        languages.append(lang_code)
        
        return languages
    
    @property
    def current_language(self) -> str:
        return self._current_lang


# Global i18n instance
i18n = I18n()


# ==============================================================================
# BACKGROUND TASK EXECUTOR (UI Responsiveness)
# ==============================================================================

class BackgroundTask:
    """
    Thread-safe background task executor for heavy operations.
    
    Prevents UI lag by running database queries, report generation,
    and file I/O in separate threads while providing progress feedback.
    
    Usage:
        task = BackgroundTask(
            target=heavy_function,
            args=(arg1, arg2),
            on_complete=lambda result: update_ui(result),
            on_error=lambda e: show_error(e)
        )
        task.start()
    """
    
    _active_tasks: ClassVar[List['BackgroundTask']] = []
    
    def __init__(
        self,
        target: Callable[..., Any],
        args: tuple = (),
        kwargs: dict = None,
        on_complete: Callable[[Any], None] = None,
        on_error: Callable[[Exception], None] = None,
        master: tk.Tk = None
    ):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.on_complete = on_complete
        self.on_error = on_error
        self.master = master
        self._thread: Optional[threading.Thread] = None
        self._result: Any = None
        self._error: Optional[Exception] = None
    
    def start(self) -> None:
        """Start the background task."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        BackgroundTask._active_tasks.append(self)
        self._thread.start()
    
    def _run(self) -> None:
        """Execute the task and handle callbacks."""
        try:
            self._result = self.target(*self.args, **self.kwargs)
            if self.on_complete and self.master:
                # Schedule callback on main thread
                self.master.after(0, lambda: self.on_complete(self._result))
            elif self.on_complete:
                self.on_complete(self._result)
        except Exception as e:
            self._error = e
            logger.error(f"Background task failed: {e}")
            if self.on_error and self.master:
                self.master.after(0, lambda: self.on_error(e))
            elif self.on_error:
                self.on_error(e)
        finally:
            if self in BackgroundTask._active_tasks:
                BackgroundTask._active_tasks.remove(self)
    
    @classmethod
    def wait_all(cls, timeout: float = None) -> None:
        """Wait for all active background tasks to complete."""
        for task in list(cls._active_tasks):
            if task._thread and task._thread.is_alive():
                task._thread.join(timeout=timeout)


def run_in_background(
    target: Callable[..., Any],
    args: tuple = (),
    on_complete: Callable[[Any], None] = None,
    on_error: Callable[[Exception], None] = None,
    master: tk.Tk = None
) -> BackgroundTask:
    """
    Convenience function to run a callable in the background.
    
    Args:
        target: Function to execute
        args: Arguments to pass to target
        on_complete: Callback with result on success
        on_error: Callback with exception on failure
        master: Tk root for thread-safe UI updates
    
    Returns:
        BackgroundTask instance
    """
    task = BackgroundTask(
        target=target,
        args=args,
        on_complete=on_complete,
        on_error=on_error,
        master=master
    )
    task.start()
    return task


# ==============================================================================
# MULTI-DATABASE DRIVER ABSTRACTION
# ==============================================================================

class DatabaseDriver(ABC):
    """Abstract base class for database drivers."""
    
    @abstractmethod
    def connect(self):
        """Establish database connection."""
        pass
    
    @abstractmethod
    def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a query with parameters."""
        pass
    
    @abstractmethod
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        """Execute a query with multiple parameter sets."""
        pass
    
    @abstractmethod
    def fetchone(self) -> Optional[Dict[str, Any]]:
        """Fetch one result row."""
        pass
    
    @abstractmethod
    def fetchall(self) -> List[Dict[str, Any]]:
        """Fetch all result rows."""
        pass
    
    @abstractmethod
    def commit(self):
        """Commit transaction."""
        pass
    
    @abstractmethod
    def rollback(self):
        """Rollback transaction."""
        pass
    
    @abstractmethod
    def close(self):
        """Close connection."""
        pass


class SQLiteDriver(DatabaseDriver):
    """SQLite database driver with WAL mode."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
    
    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            check_same_thread=False,
            isolation_level=None,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        return self
    
    def execute(self, query: str, params: tuple = ()) -> Any:
        # Convert PostgreSQL/MySQL placeholders to SQLite
        query = self._normalize_query(query)
        self.cursor = self.conn.execute(query, params)
        return self.cursor
    
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        query = self._normalize_query(query)
        self.cursor = self.conn.executemany(query, params_list)
        return self.cursor
    
    def executescript(self, script: str) -> Any:
        return self.conn.executescript(script)
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        if self.cursor:
            row = self.cursor.fetchone()
            return dict(row) if row else None
        return None
    
    def fetchall(self) -> List[Dict[str, Any]]:
        if self.cursor:
            return [dict(row) for row in self.cursor.fetchall()]
        return []
    
    def commit(self):
        if self.conn:
            self.conn.execute("COMMIT")
    
    def rollback(self):
        if self.conn:
            try:
                self.conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def begin(self):
        if self.conn:
            self.conn.execute("BEGIN")
    
    def _normalize_query(self, query: str) -> str:
        """Convert %s placeholders to ? for SQLite."""
        return query.replace('%s', '?')
    
    @property
    def lastrowid(self) -> int:
        return self.cursor.lastrowid if self.cursor else 0


class PostgreSQLDriver(DatabaseDriver):
    """PostgreSQL database driver with connection pooling."""
    
    def __init__(self, connection_string: str, pool_size: int = 5):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.pool = None
        self.conn = None
        self.cursor = None
    
    def connect(self):
        if not HAS_POSTGRES:
            raise ImportError("psycopg2 is required for PostgreSQL. Install with: pip install psycopg2-binary")
        
        # Parse connection string to dict
        params = dict(item.split('=') for item in self.connection_string.split() if '=' in item)
        
        self.pool = pg_pool.ThreadedConnectionPool(1, self.pool_size, **params)
        self.conn = self.pool.getconn()
        self.conn.autocommit = False
        return self
    
    def execute(self, query: str, params: tuple = ()) -> Any:
        self.cursor = self.conn.cursor()
        self.cursor.execute(query, params)
        return self.cursor
    
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        self.cursor = self.conn.cursor()
        self.cursor.executemany(query, params_list)
        return self.cursor
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        if self.cursor:
            row = self.cursor.fetchone()
            if row:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, row))
        return None
    
    def fetchall(self) -> List[Dict[str, Any]]:
        if self.cursor:
            rows = self.cursor.fetchall()
            if rows:
                columns = [desc[0] for desc in self.cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        return []
    
    def commit(self):
        if self.conn:
            self.conn.commit()
    
    def rollback(self):
        if self.conn:
            self.conn.rollback()
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn and self.pool:
            self.pool.putconn(self.conn)


class MySQLDriver(DatabaseDriver):
    """MySQL database driver with connection pooling."""
    
    def __init__(self, connection_string: str, pool_size: int = 5):
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.pool = None
        self.conn = None
        self.cursor = None
    
    def connect(self):
        if not HAS_MYSQL:
            raise ImportError("mysql-connector-python is required for MySQL. Install with: pip install mysql-connector-python")
        
        # Parse connection string to dict
        params = dict(item.split('=') for item in self.connection_string.split() if '=' in item)
        params['pool_size'] = self.pool_size
        params['pool_name'] = 'inventory_pool'
        
        self.pool = mysql_pool.MySQLConnectionPool(**params)
        self.conn = self.pool.get_connection()
        return self
    
    def execute(self, query: str, params: tuple = ()) -> Any:
        self.cursor = self.conn.cursor(dictionary=True)
        # Convert ? placeholders to %s for MySQL
        query = query.replace('?', '%s')
        self.cursor.execute(query, params)
        return self.cursor
    
    def executemany(self, query: str, params_list: List[tuple]) -> Any:
        self.cursor = self.conn.cursor(dictionary=True)
        query = query.replace('?', '%s')
        self.cursor.executemany(query, params_list)
        return self.cursor
    
    def fetchone(self) -> Optional[Dict[str, Any]]:
        if self.cursor:
            return self.cursor.fetchone()
        return None
    
    def fetchall(self) -> List[Dict[str, Any]]:
        if self.cursor:
            return self.cursor.fetchall()
        return []
    
    def commit(self):
        if self.conn:
            self.conn.commit()
    
    def rollback(self):
        if self.conn:
            self.conn.rollback()
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def create_database_driver() -> DatabaseDriver:
    """Factory function to create the appropriate database driver."""
    driver_type = Config.DB_DRIVER.lower()
    
    if driver_type == "postgresql":
        if not Config.DB_CONNECTION_STRING:
            raise ValueError("DB_CONNECTION_STRING required for PostgreSQL")
        return PostgreSQLDriver(Config.DB_CONNECTION_STRING, Config.DB_POOL_SIZE)
    
    elif driver_type == "mysql":
        if not Config.DB_CONNECTION_STRING:
            raise ValueError("DB_CONNECTION_STRING required for MySQL")
        return MySQLDriver(Config.DB_CONNECTION_STRING, Config.DB_POOL_SIZE)
    
    else:  # Default to SQLite
        return SQLiteDriver(Config.DB_PATH)


# ==============================================================================
# BARCODE SCANNER DETECTION
# ==============================================================================

class BarcodeListener:
    """
    Intelligent barcode scanner detection for SKU entry fields.
    
    Detects rapid keystroke input characteristic of barcode scanners
    (typically <50ms between characters) and triggers a callback.
    
    Usage:
        listener = BarcodeListener(on_barcode=lambda code: print(f"Scanned: {code}"))
        entry_widget.bind("<Key>", listener.on_key)
    """
    
    def __init__(self, 
                 on_barcode: Callable[[str], None],
                 detection_ms: int = Config.BARCODE_DETECTION_MS,
                 min_length: int = Config.BARCODE_MIN_LENGTH):
        self.on_barcode = on_barcode
        self.detection_ms = detection_ms
        self.min_length = min_length
        
        self._buffer: str = ""
        self._last_keystroke: float = 0
        self._is_scanning: bool = False
    
    def on_key(self, event) -> Optional[str]:
        """
        Handle key event. Returns 'break' if barcode detected to prevent default handling.
        """
        current_time = time.time() * 1000  # Convert to ms
        
        # Check if this is a rapid keystroke (scanner behavior)
        time_diff = current_time - self._last_keystroke
        
        if event.keysym == 'Return' or event.keysym == 'Tab':
            # End of barcode scan
            if self._is_scanning and len(self._buffer) >= self.min_length:
                barcode = self._buffer
                self._reset()
                self.on_barcode(barcode)
                return "break"
            self._reset()
            return None
        
        if event.char and event.char.isprintable():
            if time_diff < self.detection_ms or self._last_keystroke == 0:
                # Rapid input detected - likely a scanner
                self._buffer += event.char
                self._is_scanning = True
            else:
                # Slow input - human typing
                self._reset()
                self._buffer = event.char
            
            self._last_keystroke = current_time
        
        return None
    
    def _reset(self):
        """Reset the scanner state."""
        self._buffer = ""
        self._is_scanning = False
        self._last_keystroke = 0


# ==============================================================================
# DATA MODELS
# ==============================================================================

class UserRole(Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"

@dataclass
class User:
    username: str
    password_hash: str
    role: UserRole
    full_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

@dataclass
class Product:
    sku: str
    name: str
    brand: str
    price: Decimal
    quantity: int
    category: str
    supplier: str
    image_path: str = ""
    min_stock: int = Config.LOW_STOCK_THRESHOLD
    cost_price: Decimal = Decimal("0")  # For profit margin calculation
    last_sold_at: Optional[datetime] = None  # For aging inventory
    total_sold: int = 0  # For velocity calculation
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_value(self) -> Decimal:
        return self.price * self.quantity
    
    @property
    def stock_status(self) -> str:
        if self.quantity <= Config.CRITICAL_STOCK_THRESHOLD:
            return "critical"
        elif self.quantity <= self.min_stock:
            return "low"
        return "normal"
    
    @property
    def profit_margin(self) -> float:
        """Calculate profit margin percentage."""
        if self.cost_price <= 0 or self.price <= 0:
            return 0.0
        return float((self.price - self.cost_price) / self.price * 100)
    
    @property
    def days_in_stock(self) -> int:
        """Days since product was added to inventory."""
        return (datetime.now() - self.created_at).days
    
    @property
    def days_since_last_sale(self) -> Optional[int]:
        """Days since last sale (None if never sold)."""
        if not self.last_sold_at:
            return None
        return (datetime.now() - self.last_sold_at).days
    
    @property
    def avg_daily_sales(self) -> float:
        """Average daily sales velocity."""
        days = max(self.days_in_stock, 1)
        return self.total_sold / days
    
    @property
    def days_of_inventory_remaining(self) -> Optional[int]:
        """Predictive: Days until stockout based on sales velocity."""
        if self.avg_daily_sales <= 0:
            return None  # Cannot predict without sales data
        return int(self.quantity / self.avg_daily_sales)
    
    @property
    def is_aging(self) -> bool:
        """Check if product is aging (>90 days without sale)."""
        if self.last_sold_at:
            return self.days_since_last_sale > Config.AGING_THRESHOLD_DAYS
        return self.days_in_stock > Config.AGING_THRESHOLD_DAYS
    
    @property
    def is_low_margin(self) -> bool:
        """Check if product has low profit margin."""
        return 0 < self.profit_margin < Config.LOW_MARGIN_THRESHOLD
    
    @property
    def health_score(self) -> int:
        """Overall product health score (0-100)."""
        score = 100
        
        # Stock health (-30 max)
        if self.stock_status == "critical":
            score -= 30
        elif self.stock_status == "low":
            score -= 15
        
        # Margin health (-25 max)
        if self.is_low_margin:
            score -= 25
        elif self.profit_margin < 25:
            score -= 10
        
        # Aging penalty (-25 max)
        if self.is_aging:
            score -= 25
        elif self.days_since_last_sale and self.days_since_last_sale > 30:
            score -= 10
        
        # Velocity bonus (+10 if selling well)
        if self.avg_daily_sales > 1:
            score = min(100, score + 10)
        
        return max(0, score)

@dataclass
class AuditLog:
    action: str
    entity_type: str
    entity_id: str
    details: str
    user: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SerialNumber:
    """Track unique serial numbers for high-value items."""
    serial: str
    sku: str
    status: str = "in_stock"  # in_stock, sold, returned, defective
    sold_at: Optional[datetime] = None
    sold_price: Optional[Decimal] = None
    customer_ref: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SaleRecord:
    """Enhanced sales record for POS integration and velocity tracking."""
    id: int
    sku: str
    product_name: str = ""
    quantity: int = 0
    unit_price: Decimal = Decimal("0")
    cost_price: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")
    customer_ref: str = ""
    payment_method: str = "cash"  # cash, card, credit
    user: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def profit_margin(self) -> float:
        """Calculate profit margin for this sale."""
        if self.total <= 0:
            return 0.0
        return float((self.profit / self.total) * 100)


@dataclass
class InventoryHealth:
    """Business Intelligence summary."""
    total_products: int
    total_value: Decimal
    total_units: int
    low_stock_count: int
    critical_stock_count: int
    aging_count: int
    low_margin_count: int
    avg_margin: float
    inventory_turnover: float
    days_of_inventory: float

# ==============================================================================
# DATABASE LAYER - Repository Pattern
# ==============================================================================

class DatabaseManager:
    """
    Thread-safe database connection manager with multi-driver support.
    
    Supports: SQLite (default), PostgreSQL, MySQL
    Configuration via Config.DB_DRIVER and Config.DB_CONNECTION_STRING
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._driver_type = Config.DB_DRIVER.lower()
        
        # For SQLite, ensure data directory exists
        if self._driver_type == "sqlite":
            Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        self._initialize_schema()
        self._initialized = True
        logger.info(f"Database initialized successfully (driver: {self._driver_type})")
    
    @contextmanager
    def get_connection(self):
        """Context manager for safe database connections with transactions."""
        driver = create_database_driver()
        driver.connect()
        
        if self._driver_type == "sqlite":
            driver.begin()
        
        try:
            yield driver
            driver.commit()
        except Exception as e:
            driver.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            driver.close()
    
    @contextmanager
    def get_autocommit_connection(self):
        """Context manager for schema initialization (autocommit mode)."""
        driver = create_database_driver()
        driver.connect()
        
        try:
            yield driver
        finally:
            driver.close()
    
    def _initialize_schema(self):
        """Initialize database schema with migrations support"""
        driver = create_database_driver()
        driver.connect()
        
        try:
            if self._driver_type == "sqlite":
                driver.executescript("""
                    -- Products Table with BI Fields
                    CREATE TABLE IF NOT EXISTS products (
                        sku TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        brand TEXT DEFAULT '',
                        price REAL NOT NULL CHECK(price >= 0),
                        cost_price REAL DEFAULT 0 CHECK(cost_price >= 0),
                        quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                        category TEXT DEFAULT '',
                        supplier TEXT DEFAULT '',
                        image_path TEXT DEFAULT '',
                        min_stock INTEGER DEFAULT 5,
                        total_sold INTEGER DEFAULT 0,
                        last_sold_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    -- Serial Numbers for High-Value Items
                    CREATE TABLE IF NOT EXISTS serial_numbers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sku TEXT NOT NULL,
                        serial_number TEXT NOT NULL UNIQUE,
                        status TEXT DEFAULT 'in_stock',
                        sold_at TIMESTAMP,
                        customer_info TEXT DEFAULT '',
                        notes TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sku) REFERENCES products(sku) ON DELETE CASCADE
                    );
                    
                    -- Sales History for POS Integration
                    CREATE TABLE IF NOT EXISTS sales_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sku TEXT NOT NULL,
                        product_name TEXT DEFAULT '',
                        quantity_sold INTEGER NOT NULL CHECK(quantity_sold > 0),
                        unit_price REAL NOT NULL,
                        cost_price REAL DEFAULT 0,
                        total REAL NOT NULL,
                        profit REAL DEFAULT 0,
                        customer_ref TEXT DEFAULT '',
                        payment_method TEXT DEFAULT 'cash',
                        user TEXT NOT NULL,
                        sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sku) REFERENCES products(sku) ON DELETE CASCADE
                    );
                    
                    -- Users Table with Secure Password Storage
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'staff',
                        full_name TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP
                    );
                    
                    -- Audit Log Table
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        entity_type TEXT NOT NULL,
                        entity_id TEXT,
                        details TEXT,
                        user TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    -- User Preferences Table (stores UI preferences per user)
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        username TEXT PRIMARY KEY,
                        theme TEXT DEFAULT 'dark',
                        language TEXT DEFAULT 'en',
                        dashboard_view TEXT DEFAULT 'default',
                        notifications_enabled INTEGER DEFAULT 1,
                        last_category_filter TEXT DEFAULT 'All Categories',
                        last_status_filter TEXT DEFAULT 'All Status',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
                    );
                    
                    -- Create indexes for performance (scalability for 100k+ products)
                    CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
                    CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier);
                    CREATE INDEX IF NOT EXISTS idx_products_health ON products(quantity, last_sold_at);
                    CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
                    CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
                    CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
                    CREATE INDEX IF NOT EXISTS idx_products_updated ON products(updated_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_products_quantity ON products(quantity);
                    CREATE INDEX IF NOT EXISTS idx_products_stock_status ON products(quantity, min_stock);
                    CREATE INDEX IF NOT EXISTS idx_serial_sku ON serial_numbers(sku);
                    CREATE INDEX IF NOT EXISTS idx_serial_status ON serial_numbers(status);
                    CREATE INDEX IF NOT EXISTS idx_sales_sku ON sales_history(sku);
                    CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_history(sold_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
                """)
            else:
                # PostgreSQL/MySQL schema
                self._initialize_sql_schema(driver)
            
            # Run migrations for existing databases (must run before certain indexes)
            self._run_migrations(driver)
            
            # Create indexes that depend on migrated columns
            if self._driver_type == "sqlite":
                try:
                    driver.execute("CREATE INDEX IF NOT EXISTS idx_sales_user ON sales_history(user)")
                    driver.commit()
                except Exception:
                    pass  # Index may already exist or column may not exist yet
            
            # Create default admin if not exists
            driver.execute("SELECT 1 FROM users WHERE username = ?", ('admin',))
            admin_exists = driver.fetchone()
            
            if not admin_exists:
                password_hash = bcrypt.hashpw(
                    "admin123".encode(), bcrypt.gensalt()
                ).decode()
                driver.execute(
                    "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
                    ("admin", password_hash, "admin", "System Administrator")
                )
                driver.commit()
                logger.info("Default admin user created")
        
        finally:
            driver.close()
    
    def _initialize_sql_schema(self, driver):
        """Initialize schema for PostgreSQL/MySQL."""
        # Note: This uses standard SQL that works across both PostgreSQL and MySQL
        tables = [
            """CREATE TABLE IF NOT EXISTS products (
                sku VARCHAR(50) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                brand VARCHAR(100) DEFAULT '',
                price DECIMAL(10,2) NOT NULL CHECK(price >= 0),
                cost_price DECIMAL(10,2) DEFAULT 0 CHECK(cost_price >= 0),
                quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                category VARCHAR(100) DEFAULT '',
                supplier VARCHAR(255) DEFAULT '',
                image_path VARCHAR(500) DEFAULT '',
                min_stock INTEGER DEFAULT 5,
                total_sold INTEGER DEFAULT 0,
                last_sold_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'staff',
                full_name VARCHAR(100) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS sales_history (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(50) NOT NULL,
                product_name VARCHAR(255) DEFAULT '',
                quantity_sold INTEGER NOT NULL CHECK(quantity_sold > 0),
                unit_price DECIMAL(10,2) NOT NULL,
                cost_price DECIMAL(10,2) DEFAULT 0,
                total DECIMAL(10,2) NOT NULL,
                profit DECIMAL(10,2) DEFAULT 0,
                customer_ref VARCHAR(100) DEFAULT '',
                payment_method VARCHAR(20) DEFAULT 'cash',
                user VARCHAR(50) NOT NULL,
                sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                action VARCHAR(50) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(100),
                details TEXT,
                user VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        ]
        
        for table_sql in tables:
            try:
                driver.execute(table_sql)
                driver.commit()
            except Exception as e:
                logger.debug(f"Table creation skipped (may exist): {e}")
    
    def _run_migrations(self, driver):
        """Run schema migrations for existing databases"""
        if self._driver_type != "sqlite":
            return  # Migrations only needed for SQLite upgrades
        
        # Check if products table needs BI columns
        driver.execute("PRAGMA table_info(products)")
        rows = driver.fetchall()
        columns = {row['name'] for row in rows}
        
        migrations = []
        if 'cost_price' not in columns:
            migrations.append("ALTER TABLE products ADD COLUMN cost_price REAL DEFAULT 0")
        if 'total_sold' not in columns:
            migrations.append("ALTER TABLE products ADD COLUMN total_sold INTEGER DEFAULT 0")
        if 'last_sold_at' not in columns:
            migrations.append("ALTER TABLE products ADD COLUMN last_sold_at TIMESTAMP")
        
        for sql in migrations:
            try:
                driver.execute(sql)
                driver.commit()
                logger.info(f"Migration executed: {sql}")
            except Exception as e:
                logger.debug(f"Migration skipped (may already exist): {e}")
        
        # Check if sales_history table needs new POS columns
        driver.execute("PRAGMA table_info(sales_history)")
        rows = driver.fetchall()
        sales_columns = {row['name'] for row in rows} if rows else set()
        
        sales_migrations = []
        if sales_columns:  # Only migrate if table exists
            if 'product_name' not in sales_columns:
                sales_migrations.append("ALTER TABLE sales_history ADD COLUMN product_name TEXT DEFAULT ''")
            if 'cost_price' not in sales_columns:
                sales_migrations.append("ALTER TABLE sales_history ADD COLUMN cost_price REAL DEFAULT 0")
            if 'profit' not in sales_columns:
                sales_migrations.append("ALTER TABLE sales_history ADD COLUMN profit REAL DEFAULT 0")
            if 'customer_ref' not in sales_columns:
                sales_migrations.append("ALTER TABLE sales_history ADD COLUMN customer_ref TEXT DEFAULT ''")
            if 'payment_method' not in sales_columns:
                sales_migrations.append("ALTER TABLE sales_history ADD COLUMN payment_method TEXT DEFAULT 'cash'")
            if 'user' not in sales_columns:
                sales_migrations.append("ALTER TABLE sales_history ADD COLUMN user TEXT DEFAULT ''")
        
        for sql in sales_migrations:
            try:
                driver.execute(sql)
                driver.commit()
                logger.info(f"Sales migration executed: {sql}")
            except Exception as e:
                logger.debug(f"Sales migration skipped (may already exist): {e}")


class SalesRepository:
    """
    Enterprise POS Integration Repository.
    
    Features:
    - record_sale(): Full transaction recording with auto-deduction
    - get_sales_velocity(): Demand forecasting for inventory planning
    - get_inventory_health(): Dashboard analytics
    - get_recent_sales(): Transaction history
    - get_daily_summary(): Daily revenue/profit report
    - calculate_real_time_profit(): Live P&L calculation
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def record_sale(
        self, 
        sku: str, 
        product_name: str,
        quantity: int, 
        unit_price: float, 
        cost_price: float, 
        customer_ref: str = "",
        payment_method: str = "cash",
        user: str = ""
    ) -> Tuple[bool, str]:
        """
        Record a sale with automatic stock deduction and profit calculation.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        total = unit_price * quantity
        profit = (unit_price - cost_price) * quantity
        
        with self.db.get_connection() as driver:
            # Check available stock first
            driver.execute("SELECT quantity FROM products WHERE sku = ?", (sku,))
            result = driver.fetchone()
            
            if not result:
                return False, f"Product '{sku}' not found"
            
            current_qty = result['quantity']
            if current_qty < quantity:
                return False, f"Insufficient stock. Available: {current_qty}"
            
            # Insert sale record
            driver.execute("""
                INSERT INTO sales_history 
                (sku, product_name, quantity_sold, unit_price, cost_price, total, profit, customer_ref, payment_method, user)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, product_name, quantity, unit_price, cost_price, total, profit, customer_ref, payment_method, user))
            
            # Update product stats (auto-deduct stock)
            driver.execute("""
                UPDATE products 
                SET quantity = quantity - ?,
                    total_sold = total_sold + ?,
                    last_sold_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE sku = ?
            """, (quantity, quantity, sku))
            
            return True, f"Sale recorded: {quantity}x {product_name} = ₱{total:,.2f} (Profit: ₱{profit:,.2f})"
    
    def get_sales_velocity(self, sku: str, days: int = 30) -> float:
        """Calculate average daily sales over given period"""
        with self.db.get_connection() as driver:
            driver.execute("""
                SELECT COALESCE(SUM(quantity_sold), 0) as total
                FROM sales_history 
                WHERE sku = ? AND sold_at >= datetime('now', ?)
            """, (sku, f'-{days} days'))
            result = driver.fetchone()
            return result['total'] / days if result else 0.0
    
    def get_recent_sales(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent sales transactions."""
        with self.db.get_connection() as driver:
            driver.execute("""
                SELECT * FROM sales_history 
                ORDER BY sold_at DESC 
                LIMIT ?
            """, (limit,))
            return driver.fetchall()
    
    def get_daily_summary(self, date: str = None) -> Dict[str, Any]:
        """
        Get daily sales summary.
        
        Args:
            date: Date in YYYY-MM-DD format (default: today)
        """
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.db.get_connection() as driver:
            driver.execute("""
                SELECT 
                    COUNT(*) as transaction_count,
                    COALESCE(SUM(quantity_sold), 0) as units_sold,
                    COALESCE(SUM(total), 0) as revenue,
                    COALESCE(SUM(profit), 0) as profit
                FROM sales_history 
                WHERE date(sold_at) = ?
            """, (date,))
            result = driver.fetchone()
            
            return {
                "date": date,
                "transaction_count": result['transaction_count'] if result else 0,
                "units_sold": result['units_sold'] if result else 0,
                "revenue": Decimal(str(result['revenue'])) if result else Decimal("0"),
                "profit": Decimal(str(result['profit'])) if result else Decimal("0"),
            }
    
    def calculate_real_time_profit(self) -> Dict[str, Decimal]:
        """Calculate real-time profit metrics."""
        with self.db.get_connection() as driver:
            # Today's stats
            driver.execute("""
                SELECT 
                    COALESCE(SUM(total), 0) as today_revenue,
                    COALESCE(SUM(profit), 0) as today_profit
                FROM sales_history 
                WHERE date(sold_at) = date('now')
            """)
            today = driver.fetchone()
            
            # This month's stats
            driver.execute("""
                SELECT 
                    COALESCE(SUM(total), 0) as month_revenue,
                    COALESCE(SUM(profit), 0) as month_profit
                FROM sales_history 
                WHERE strftime('%Y-%m', sold_at) = strftime('%Y-%m', 'now')
            """)
            month = driver.fetchone()
            
            return {
                "today_revenue": Decimal(str(today['today_revenue'])) if today else Decimal("0"),
                "today_profit": Decimal(str(today['today_profit'])) if today else Decimal("0"),
                "month_revenue": Decimal(str(month['month_revenue'])) if month else Decimal("0"),
                "month_profit": Decimal(str(month['month_profit'])) if month else Decimal("0"),
            }
    
    def get_inventory_health(self) -> List[Dict[str, Any]]:
        """Get inventory health metrics for all products"""
        with self.db.get_connection() as driver:
            driver.execute("""
                SELECT 
                    p.sku,
                    p.name,
                    p.quantity,
                    p.min_stock,
                    p.price,
                    p.cost_price,
                    p.total_sold,
                    p.last_sold_at,
                    p.created_at,
                    COALESCE(
                        (SELECT SUM(quantity_sold) FROM sales_history 
                         WHERE sku = p.sku AND sold_at >= datetime('now', '-30 days')),
                        0
                    ) as sales_30d,
                    CASE 
                        WHEN p.cost_price > 0 THEN ((p.price - p.cost_price) / p.price) * 100
                        ELSE 0
                    END as margin_pct
                FROM products p
                ORDER BY p.quantity ASC
            """)
            return driver.fetchall()


class SerialNumberRepository:
    """Repository for Serial Number tracking.
    
    BI infrastructure for serialized inventory management:
    - add_serial(): Register individual unit serial numbers
    - mark_sold(): Track sold units with customer info
    - get_by_sku(): View all serials for a product
    - search(): Lookup serials by number or customer
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def add_serial(self, sku: str, serial_number: str, notes: str = "") -> bool:
        with self.db.get_connection() as driver:
            driver.execute("""
                INSERT INTO serial_numbers (sku, serial_number, notes)
                VALUES (?, ?, ?)
            """, (sku, serial_number, notes))
            return True
    
    def mark_sold(self, serial_number: str, customer_info: str = "") -> bool:
        with self.db.get_connection() as driver:
            driver.execute("""
                UPDATE serial_numbers 
                SET status = 'sold', sold_at = CURRENT_TIMESTAMP, customer_info = ?
                WHERE serial_number = ?
            """, (customer_info, serial_number))
            return True
    
    def get_by_sku(self, sku: str) -> List[Dict[str, Any]]:
        with self.db.get_connection() as driver:
            driver.execute("""
                SELECT * FROM serial_numbers WHERE sku = ? ORDER BY created_at DESC
            """, (sku,))
            return driver.fetchall()
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        with self.db.get_connection() as driver:
            driver.execute("""
                SELECT sn.*, p.name as product_name
                FROM serial_numbers sn
                JOIN products p ON sn.sku = p.sku
                WHERE sn.serial_number LIKE ? OR sn.customer_info LIKE ?
                ORDER BY sn.created_at DESC
            """, (f'%{query}%', f'%{query}%'))
            return driver.fetchall()


class ProductRepository:
    """Repository for Product CRUD operations with pagination for scalability."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def get_count(self, search: str = "", category: str = "") -> int:
        """Get total product count for pagination."""
        with self.db.get_connection() as driver:
            conditions = []
            params = []
            
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    "(name LIKE ? OR sku LIKE ? OR brand LIKE ? OR category LIKE ? OR supplier LIKE ?)"
                )
                params.extend([search_term] * 5)
            
            if category and category not in ("All Categories", ""):
                conditions.append("category = ?")
                params.append(category)
            
            query = "SELECT COUNT(*) as count FROM products"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            driver.execute(query, tuple(params))
            result = driver.fetchone()
            return result['count'] if result else 0
    
    def get_all(self, search: str = "", category: str = "", status: str = "", 
                page: int = 1, page_size: int = None) -> List[Product]:
        """
        Get products with optional fuzzy search, filters, and pagination.
        
        Performance optimized for 100k+ products:
        - Stock status filter moved to SQL for index utilization
        - Pagination with LIMIT/OFFSET for lazy loading
        - Single query execution with combined conditions
        
        Args:
            search: Fuzzy search across SKU, name, brand, category, supplier
            category: Filter by exact category (empty = all)
            status: Filter by stock status: 'Critical Stock', 'Low Stock', 'In Stock'
            page: Page number (1-indexed) for pagination
            page_size: Items per page (default: Config.PAGE_SIZE)
        
        Returns:
            List of Product objects matching criteria
        """
        if page_size is None:
            page_size = Config.PAGE_SIZE
        
        with self.db.get_connection() as driver:
            conditions = []
            params = []
            
            # Fuzzy search across multiple columns (uses indexes on individual columns)
            if search:
                search_term = f"%{search}%"
                conditions.append(
                    "(name LIKE ? OR sku LIKE ? OR brand LIKE ? OR category LIKE ? OR supplier LIKE ?)"
                )
                params.extend([search_term] * 5)
            
            # Category filter (uses idx_products_category)
            if category and category not in ("All Categories", ""):
                conditions.append("category = ?")
                params.append(category)
            
            # Stock status filter - moved to SQL for performance (uses idx_products_stock_status)
            if status and status not in ("All Status", ""):
                status_map = {
                    "Critical Stock": f"quantity <= {Config.CRITICAL_STOCK_THRESHOLD}",
                    "Low Stock": f"quantity > {Config.CRITICAL_STOCK_THRESHOLD} AND quantity <= min_stock",
                    "In Stock": "quantity > min_stock"
                }
                status_condition = status_map.get(status)
                if status_condition:
                    conditions.append(f"({status_condition})")
            
            # Build optimized query
            query = "SELECT * FROM products"
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY updated_at DESC"
            
            # Add pagination for large datasets (LIMIT/OFFSET)
            total_count = self.get_count(search, category)
            if total_count > Config.LAZY_LOAD_THRESHOLD:
                offset = (page - 1) * page_size
                query += f" LIMIT {page_size} OFFSET {offset}"
            
            driver.execute(query, tuple(params))
            rows = driver.fetchall()
            
            return [self._row_to_product(row) for row in rows]
    
    def get_by_sku(self, sku: str) -> Optional[Product]:
        with self.db.get_connection() as driver:
            driver.execute("SELECT * FROM products WHERE sku = ?", (sku,))
            row = driver.fetchone()
            return self._row_to_product(row) if row else None
    
    def save(self, product: Product) -> bool:
        with self.db.get_connection() as driver:
            driver.execute("""
                INSERT INTO products (sku, name, brand, price, cost_price, quantity, category, supplier, image_path, min_stock, total_sold, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product.sku, product.name, product.brand, float(product.price),
                float(product.cost_price), product.quantity, product.category, 
                product.supplier, product.image_path, product.min_stock,
                product.total_sold, product.created_at, datetime.now()
            ))
            return True
    
    def update(self, product: Product) -> bool:
        with self.db.get_connection() as driver:
            driver.execute("""
                UPDATE products SET 
                    name=?, brand=?, price=?, cost_price=?, quantity=?, category=?, 
                    supplier=?, image_path=?, min_stock=?, updated_at=?
                WHERE sku=?
            """, (
                product.name, product.brand, float(product.price), float(product.cost_price),
                product.quantity, product.category, product.supplier, product.image_path, 
                product.min_stock, datetime.now(), product.sku
            ))
            return True
    
    def delete(self, sku: str) -> bool:
        with self.db.get_connection() as driver:
            driver.execute("DELETE FROM products WHERE sku = ?", (sku,))
            return True
    
    def get_statistics(self) -> dict:
        with self.db.get_connection() as driver:
            driver.execute("""
                SELECT 
                    COUNT(*) as total_products,
                    COALESCE(SUM(price * quantity), 0) as total_value,
                    COALESCE(SUM(quantity), 0) as total_units,
                    COUNT(CASE WHEN quantity <= 5 THEN 1 END) as low_stock_count,
                    COUNT(CASE WHEN quantity <= 2 THEN 1 END) as critical_stock_count
                FROM products
            """)
            stats = driver.fetchone()
            
            return {
                "total_products": stats["total_products"],
                "total_value": Decimal(str(stats["total_value"])),
                "total_units": stats["total_units"],
                "low_stock_count": stats["low_stock_count"],
                "critical_stock_count": stats["critical_stock_count"],
            }
    
    def _row_to_product(self, row: Dict[str, Any]) -> Product:
        """Convert database row to Product with BI metrics."""
        def _parse_datetime(value, default=None):
            """Parse datetime with automatic conversion fallback."""
            if value is None:
                return default
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    return default
            return default
        
        return Product(
            sku=row["sku"],
            name=row["name"],
            brand=row.get("brand") or "",
            price=Decimal(str(row["price"])),
            cost_price=Decimal(str(row.get("cost_price") or 0)),
            quantity=row["quantity"],
            category=row.get("category") or "",
            supplier=row.get("supplier") or "",
            image_path=row.get("image_path") or "",
            min_stock=row.get("min_stock") or Config.LOW_STOCK_THRESHOLD,
            total_sold=row.get("total_sold") or 0,
            last_sold_at=_parse_datetime(row.get("last_sold_at")),
            created_at=_parse_datetime(row.get("created_at"), datetime.now()),
            updated_at=_parse_datetime(row.get("updated_at"), datetime.now()),
        )

class UserRepository:
    """Repository for User authentication and management"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        with self.db.get_connection() as driver:
            driver.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            )
            row = driver.fetchone()
            
            if row and bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
                # Update last login
                driver.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (datetime.now(), username)
                )
                return User(
                    username=row["username"],
                    password_hash=row["password_hash"],
                    role=UserRole(row["role"]),
                    full_name=row.get("full_name") or "",
                    last_login=datetime.now()
                )
        return None
    
    def create_user(self, username: str, password: str, role: UserRole, full_name: str = "") -> bool:
        """Create a new user with bcrypt-hashed password."""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
        with self.db.get_connection() as driver:
            driver.execute(
                "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
                (username, password_hash, role.value, full_name)
            )
            # Initialize user preferences
            driver.execute(
                "INSERT OR IGNORE INTO user_preferences (username) VALUES (?)",
                (username,)
            )
            return True
    
    def get_all(self) -> List[User]:
        """Retrieve all users (Admin only)."""
        with self.db.get_connection() as driver:
            driver.execute(
                "SELECT username, password_hash, role, full_name, created_at, last_login FROM users ORDER BY created_at DESC"
            )
            rows = driver.fetchall()
            return [
                User(
                    username=row["username"],
                    password_hash=row["password_hash"],
                    role=UserRole(row["role"]),
                    full_name=row.get("full_name") or "",
                    created_at=row.get("created_at") if row.get("created_at") else datetime.now(),
                    last_login=row.get("last_login")
                )
                for row in rows
            ]
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Retrieve user by username."""
        with self.db.get_connection() as driver:
            driver.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            )
            row = driver.fetchone()
            if row:
                return User(
                    username=row["username"],
                    password_hash=row["password_hash"],
                    role=UserRole(row["role"]),
                    full_name=row.get("full_name") or ""
                )
        return None
    
    def update_user(self, username: str, role: Optional[UserRole] = None, full_name: Optional[str] = None) -> bool:
        """Update user details (Admin only)."""
        with self.db.get_connection() as driver:
            if role is not None:
                driver.execute(
                    "UPDATE users SET role = ? WHERE username = ?",
                    (role.value, username)
                )
            if full_name is not None:
                driver.execute(
                    "UPDATE users SET full_name = ? WHERE username = ?",
                    (full_name, username)
                )
            return True
    
    def update_password(self, username: str, new_password: str) -> bool:
        """Update user password with bcrypt hashing."""
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(12)).decode()
        with self.db.get_connection() as driver:
            driver.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (password_hash, username)
            )
            return True
    
    def delete_user(self, username: str) -> bool:
        """Delete user (Admin only, cannot delete self)."""
        with self.db.get_connection() as driver:
            driver.execute("DELETE FROM users WHERE username = ?", (username,))
            return True
    
    def username_exists(self, username: str) -> bool:
        """Check if username already exists."""
        with self.db.get_connection() as driver:
            driver.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)
            )
            row = driver.fetchone()
            return row is not None


class UserPreferencesRepository:
    """Repository for user-specific preferences."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def get(self, username: str) -> Dict[str, Any]:
        """Get user preferences."""
        with self.db.get_connection() as driver:
            driver.execute(
                "SELECT * FROM user_preferences WHERE username = ?", (username,)
            )
            row = driver.fetchone()
            if row:
                return dict(row)
            return {"theme": "dark", "language": "en", "dashboard_view": "default", "notifications_enabled": 1}
    
    def update(self, username: str, preferences: Dict[str, Any]) -> bool:
        """Update user preferences."""
        with self.db.get_connection() as driver:
            # Ensure record exists
            driver.execute(
                "INSERT OR IGNORE INTO user_preferences (username) VALUES (?)",
                (username,)
            )
            # Update each preference
            for key, value in preferences.items():
                if key in ("theme", "language", "dashboard_view", "last_category_filter", "last_status_filter"):
                    driver.execute(
                        f"UPDATE user_preferences SET {key} = ?, updated_at = ? WHERE username = ?",
                        (value, datetime.now(), username)
                    )
            return True


class AuditRepository:
    """Repository for audit logging"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def log(self, action: str, entity_type: str, entity_id: str, details: str, user: str):
        with self.db.get_connection() as driver:
            driver.execute(
                "INSERT INTO audit_logs (action, entity_type, entity_id, details, user) VALUES (?, ?, ?, ?, ?)",
                (action, entity_type, entity_id, details, user)
            )
        logger.info(f"AUDIT | {action} | {entity_type}:{entity_id} | {user} | {details}")

# ==============================================================================
# UI COMPONENTS - Modern Design System
# ==============================================================================

class UIComponents:
    """Reusable UI component factory"""
    
    @staticmethod
    def create_button(
        parent, 
        text: str, 
        command: Callable,
        variant: str = "primary",
        width: int = None,
        icon: str = ""
    ) -> tk.Button:
        """Create styled button with variants: primary, secondary, success, danger, ghost"""
        theme = Config.THEME
        
        styles = {
            "primary": {"bg": theme["accent"], "fg": "white", "active_bg": theme["accent_hover"]},
            "secondary": {"bg": theme["bg_tertiary"], "fg": theme["fg_primary"], "active_bg": theme["bg_secondary"]},
            "success": {"bg": theme["success"], "fg": "white", "active_bg": "#059669"},
            "danger": {"bg": theme["danger"], "fg": "white", "active_bg": "#dc2626"},
            "warning": {"bg": theme["warning"], "fg": "white", "active_bg": "#d97706"},
            "ghost": {"bg": theme["bg_secondary"], "fg": theme["fg_secondary"], "active_bg": theme["bg_tertiary"]},
        }
        
        style = styles.get(variant, styles["primary"])
        display_text = f"{icon} {text}".strip() if icon else text
        
        btn = tk.Button(
            parent,
            text=display_text,
            command=command,
            bg=style["bg"],
            fg=style["fg"],
            activebackground=style["active_bg"],
            activeforeground=style["fg"],
            font=("Segoe UI Semibold", 10),
            relief="flat",
            cursor="hand2",
            padx=16,
            pady=8,
            bd=0,
        )
        
        if width:
            btn.config(width=width)
        
        # Hover effects
        btn.bind("<Enter>", lambda e: btn.config(bg=style["active_bg"]))
        btn.bind("<Leave>", lambda e: btn.config(bg=style["bg"]))
        
        return btn
    
    @staticmethod
    def create_entry(
        parent,
        textvariable: tk.StringVar = None,
        placeholder: str = "",
        width: int = 30,
        show: str = ""
    ) -> tk.Entry:
        """Create styled entry field"""
        theme = Config.THEME
        
        entry = tk.Entry(
            parent,
            textvariable=textvariable,
            font=("Segoe UI", 11),
            bg=theme["input_bg"],
            fg=theme["fg_primary"],
            insertbackground=theme["fg_primary"],
            relief="flat",
            width=width,
            highlightthickness=1,
            highlightbackground=theme["border"],
            highlightcolor=theme["accent"],
        )
        
        if show:
            entry.config(show=show)
        
        # Placeholder functionality
        if placeholder and not textvariable:
            entry.insert(0, placeholder)
            entry.config(fg=theme["fg_muted"])
            
            def on_focus_in(e):
                if entry.get() == placeholder:
                    entry.delete(0, tk.END)
                    entry.config(fg=theme["fg_primary"])
            
            def on_focus_out(e):
                if not entry.get():
                    entry.insert(0, placeholder)
                    entry.config(fg=theme["fg_muted"])
            
            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)
        
        return entry
    
    @staticmethod
    def create_label(
        parent,
        text: str,
        size: int = 10,
        weight: str = "normal",
        color: str = None
    ) -> tk.Label:
        """Create styled label"""
        theme = Config.THEME
        
        font_weight = "bold" if weight == "bold" else ""
        font = ("Segoe UI", size, font_weight) if font_weight else ("Segoe UI", size)
        
        return tk.Label(
            parent,
            text=text,
            font=font,
            bg=theme["bg_secondary"],
            fg=color or theme["fg_primary"],
        )
    
    @staticmethod
    def create_stat_card(parent, title: str, value_var: tk.StringVar, color: str) -> tk.Frame:
        """Create dashboard statistic card"""
        theme = Config.THEME
        
        card = tk.Frame(parent, bg=theme["bg_card"], highlightthickness=1, highlightbackground=theme["border"])
        card.pack_propagate(False)
        card.config(width=160, height=90)
        
        # Color indicator bar
        indicator = tk.Frame(card, bg=color, height=3)
        indicator.pack(fill="x", side="top")
        
        # Content
        content = tk.Frame(card, bg=theme["bg_card"])
        content.pack(fill="both", expand=True, padx=10, pady=8)
        
        tk.Label(
            content, text=title.upper(), font=("Segoe UI", 8), 
            bg=theme["bg_card"], fg=theme["fg_muted"]
        ).pack(anchor="w")
        
        tk.Label(
            content, textvariable=value_var, font=("Segoe UI Semibold", 18),
            bg=theme["bg_card"], fg=color
        ).pack(anchor="w", pady=(2, 0))
        
        return card
    
    @staticmethod
    def show_loading(parent: tk.Widget, message: str = "Processing...") -> tk.Toplevel:
        """
        Show a modal loading indicator overlay.
        
        Args:
            parent: Parent widget to center over
            message: Loading message to display
            
        Returns:
            Toplevel window (call .destroy() when done)
        """
        theme = Config.THEME
        
        overlay = tk.Toplevel(parent)
        overlay.overrideredirect(True)
        overlay.configure(bg=theme["bg_secondary"])
        overlay.attributes("-alpha", 0.95)
        
        # Center over parent
        overlay.update_idletasks()
        parent.update_idletasks()
        
        w, h = 250, 100
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        overlay.geometry(f"{w}x{h}+{px}+{py}")
        
        # Content
        frame = tk.Frame(overlay, bg=theme["bg_secondary"])
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Spinner animation (using Unicode)
        spinner_var = tk.StringVar(value="⏳")
        spinner_label = tk.Label(
            frame, textvariable=spinner_var, font=("Segoe UI", 24),
            bg=theme["bg_secondary"], fg=theme["accent"]
        )
        spinner_label.pack()
        
        tk.Label(
            frame, text=message, font=("Segoe UI", 10),
            bg=theme["bg_secondary"], fg=theme["fg_primary"]
        ).pack(pady=(8, 0))
        
        # Animate spinner
        spinners = ["⏳", "⌛"]
        
        def animate(idx=0):
            if overlay.winfo_exists():
                spinner_var.set(spinners[idx % len(spinners)])
                overlay.after(500, lambda: animate(idx + 1))
        
        animate()
        overlay.grab_set()
        overlay.lift()
        
        return overlay

# ==============================================================================
# APPLICATION VIEWS
# ==============================================================================

class LoginView(tk.Frame):
    """Modern login screen with branding"""
    
    def __init__(self, master, on_login_success: Callable[[User], None]):
        super().__init__(master, bg=Config.THEME["bg_primary"])
        self.on_login_success = on_login_success
        self.db = DatabaseManager()
        self.user_repo = UserRepository(self.db)
        self._build_ui()
    
    def _build_ui(self):
        theme = Config.THEME
        
        # Center container
        container = tk.Frame(self, bg=theme["bg_secondary"], padx=50, pady=40)
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Logo/Brand
        tk.Label(
            container, text="INVENTORY", font=("Segoe UI Black", 32),
            bg=theme["bg_secondary"], fg=theme["accent"]
        ).pack(pady=(0, 5))
        
        tk.Label(
            container, text="SYSTEM", font=("Segoe UI Light", 18),
            bg=theme["bg_secondary"], fg=theme["fg_muted"]
        ).pack()
        
        tk.Label(
            container, text="Enterprise Inventory Management", font=("Segoe UI", 10),
            bg=theme["bg_secondary"], fg=theme["fg_secondary"]
        ).pack(pady=(5, 30))
        
        # Login Form
        form = tk.Frame(container, bg=theme["bg_secondary"])
        form.pack(fill="x")
        
        tk.Label(
            form, text="Username", font=("Segoe UI Semibold", 10),
            bg=theme["bg_secondary"], fg=theme["fg_primary"], anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.username_var = tk.StringVar()
        self.username_entry = UIComponents.create_entry(form, self.username_var, width=35)
        self.username_entry.pack(fill="x", ipady=8, pady=(0, 16))
        
        tk.Label(
            form, text="Password", font=("Segoe UI Semibold", 10),
            bg=theme["bg_secondary"], fg=theme["fg_primary"], anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.password_var = tk.StringVar()
        self.password_entry = UIComponents.create_entry(form, self.password_var, width=35, show="●")
        self.password_entry.pack(fill="x", ipady=8, pady=(0, 24))
        
        # Login Button
        login_btn = UIComponents.create_button(
            form, "Sign In", self._attempt_login, "primary"
        )
        login_btn.pack(fill="x", ipady=6)
        
        # Bind Enter key
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())
        
        # Version info
        tk.Label(
            container, text=f"Version {Config.APP_VERSION}", font=("Segoe UI", 8),
            bg=theme["bg_secondary"], fg=theme["fg_muted"]
        ).pack(pady=(30, 0))
        
        # Focus username field
        self.username_entry.focus()
    
    def _attempt_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showwarning("Validation Error", "Please enter both username and password.")
            return
        
        user = self.user_repo.authenticate(username, password)
        
        if user:
            logger.info(f"User '{username}' logged in successfully")
            self.on_login_success(user)
        else:
            logger.warning(f"Failed login attempt for user '{username}'")
            messagebox.showerror("Authentication Failed", "Invalid username or password.")
            self.password_var.set("")
            self.password_entry.focus()


class UserManagementWindow(tk.Toplevel):
    """
    Admin-Only User Management Window.
    
    Features "genius-level" validation: the Register button only activates
    when username, password, and role are all correctly filled.
    """
    
    def __init__(self, master, admin_user: User, audit_repo: 'AuditRepository'):
        super().__init__(master)
        self.admin_user = admin_user
        self.audit_repo = audit_repo
        self.db = DatabaseManager()
        self.user_repo = UserRepository(self.db)
        
        self.title("User Management - Admin Panel")
        
        # Hardware-adaptive sizing (50% of screen for modal)
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = max(800, min(int(screen_width * 0.50), 1000))
        window_height = max(550, min(int(screen_height * 0.60), 700))
        
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(700, 500)
        
        # Center on parent
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.configure(bg=Config.THEME["bg_primary"])
        self.transient(master)
        self.grab_set()
        
        # Form variables
        self.new_username = tk.StringVar()
        self.new_password = tk.StringVar()
        self.new_confirm_password = tk.StringVar()
        self.new_full_name = tk.StringVar()
        self.new_role = tk.StringVar(value="staff")
        
        # Button references
        self.register_btn: Optional[tk.Button] = None
        
        self._build_ui()
        self._setup_validation_traces()
        self._refresh_user_list()
    
    def _setup_validation_traces(self) -> None:
        """Setup real-time validation for the registration form."""
        self.new_username.trace_add("write", self._on_form_change)
        self.new_password.trace_add("write", self._on_form_change)
        self.new_confirm_password.trace_add("write", self._on_form_change)
        self.new_role.trace_add("write", self._on_form_change)
    
    def _on_form_change(self, *args: Any) -> None:
        """Genius validation: only enable Register when all fields are valid."""
        is_valid = self._is_form_valid()
        
        if self.register_btn:
            if is_valid:
                self.register_btn.config(
                    state="normal",
                    bg=Config.THEME["success"],
                    cursor="hand2"
                )
            else:
                self.register_btn.config(
                    state="disabled",
                    bg=Config.THEME["bg_tertiary"],
                    cursor="arrow"
                )
    
    def _is_form_valid(self) -> bool:
        """Check if all registration fields are valid."""
        username = self.new_username.get().strip()
        password = self.new_password.get()
        confirm = self.new_confirm_password.get()
        role = self.new_role.get()
        
        # Username must be 3+ characters, alphanumeric + underscore
        if len(username) < 3 or not username.replace("_", "").isalnum():
            return False
        
        # Password must be 6+ characters
        if len(password) < 6:
            return False
        
        # Passwords must match
        if password != confirm:
            return False
        
        # Role must be selected
        if role not in ("admin", "manager", "staff"):
            return False
        
        return True
    
    def _build_ui(self):
        theme = Config.THEME
        
        # Header
        header = tk.Frame(self, bg=theme["bg_secondary"])
        header.pack(fill="x")
        
        tk.Label(
            header, text="👥 User Management", font=("Segoe UI Semibold", 16),
            bg=theme["bg_secondary"], fg=theme["fg_primary"]
        ).pack(side="left", padx=20, pady=16)
        
        tk.Label(
            header, text="Admin Panel", font=("Segoe UI", 10),
            bg=theme["bg_secondary"], fg=theme["fg_muted"]
        ).pack(side="right", padx=20, pady=16)
        
        # Main content area
        content = tk.Frame(self, bg=theme["bg_primary"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # === LEFT: User List ===
        list_frame = tk.Frame(content, bg=theme["bg_card"])
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        tk.Label(
            list_frame, text="Registered Users", font=("Segoe UI Semibold", 12),
            bg=theme["bg_card"], fg=theme["fg_primary"]
        ).pack(anchor="w", padx=16, pady=12)
        
        # User list treeview
        columns = ("Username", "Full Name", "Role", "Last Login")
        self.user_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings",
            style="Custom.Treeview", selectmode="browse", height=12
        )
        
        col_widths = {"Username": 100, "Full Name": 120, "Role": 80, "Last Login": 130}
        for col in columns:
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=col_widths.get(col, 100), anchor="w")
        
        self.user_tree.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        
        # User actions
        action_frame = tk.Frame(list_frame, bg=theme["bg_card"])
        action_frame.pack(fill="x", padx=16, pady=(0, 12))
        
        UIComponents.create_button(
            action_frame, "Delete User", self._delete_selected_user, "danger"
        ).pack(side="right", padx=(8, 0))
        
        UIComponents.create_button(
            action_frame, "Refresh", self._refresh_user_list, "ghost", icon="🔄"
        ).pack(side="right")
        
        # === RIGHT: Register New User ===
        reg_frame = tk.Frame(content, bg=theme["bg_card"])
        reg_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        tk.Label(
            reg_frame, text="Register New User", font=("Segoe UI Semibold", 12),
            bg=theme["bg_card"], fg=theme["fg_primary"]
        ).pack(anchor="w", padx=16, pady=12)
        
        form = tk.Frame(reg_frame, bg=theme["bg_card"])
        form.pack(fill="both", expand=True, padx=16)
        
        # Username
        tk.Label(
            form, text="Username *", font=("Segoe UI", 10),
            bg=theme["bg_card"], fg=theme["fg_secondary"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        UIComponents.create_entry(form, self.new_username, width=30).pack(fill="x", pady=(0, 12))
        
        # Full Name
        tk.Label(
            form, text="Full Name", font=("Segoe UI", 10),
            bg=theme["bg_card"], fg=theme["fg_secondary"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        UIComponents.create_entry(form, self.new_full_name, width=30).pack(fill="x", pady=(0, 12))
        
        # Password
        tk.Label(
            form, text="Password * (min 6 chars)", font=("Segoe UI", 10),
            bg=theme["bg_card"], fg=theme["fg_secondary"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        UIComponents.create_entry(form, self.new_password, width=30, show="●").pack(fill="x", pady=(0, 12))
        
        # Confirm Password
        tk.Label(
            form, text="Confirm Password *", font=("Segoe UI", 10),
            bg=theme["bg_card"], fg=theme["fg_secondary"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        UIComponents.create_entry(form, self.new_confirm_password, width=30, show="●").pack(fill="x", pady=(0, 12))
        
        # Role
        tk.Label(
            form, text="Role *", font=("Segoe UI", 10),
            bg=theme["bg_card"], fg=theme["fg_secondary"], anchor="w"
        ).pack(fill="x", pady=(0, 4))
        
        role_frame = tk.Frame(form, bg=theme["bg_card"])
        role_frame.pack(fill="x", pady=(0, 16))
        
        for role_val, role_label in [("admin", "Admin"), ("manager", "Manager"), ("staff", "Staff")]:
            tk.Radiobutton(
                role_frame, text=role_label, variable=self.new_role, value=role_val,
                font=("Segoe UI", 10), bg=theme["bg_card"], fg=theme["fg_primary"],
                selectcolor=theme["bg_tertiary"], activebackground=theme["bg_card"],
                activeforeground=theme["fg_primary"]
            ).pack(side="left", padx=(0, 16))
        
        # Role descriptions
        role_desc = tk.Label(
            form, text="Admin: Full access  |  Manager: Can modify inventory  |  Staff: View only",
            font=("Segoe UI", 8), bg=theme["bg_card"], fg=theme["fg_muted"], anchor="w"
        )
        role_desc.pack(fill="x", pady=(0, 16))
        
        # Register button - disabled until form is valid (Genius feature)
        self.register_btn = UIComponents.create_button(
            form, "Register User", self._register_user, "success"
        )
        self.register_btn.config(state="disabled", bg=theme["bg_tertiary"], cursor="arrow")
        self.register_btn.pack(fill="x", pady=(8, 0))
        
        # Hint
        tk.Label(
            form, text="✨ Button activates when all fields are valid",
            font=("Segoe UI", 8), bg=theme["bg_card"], fg=theme["fg_muted"], anchor="center"
        ).pack(fill="x", pady=(8, 0))
    
    def _refresh_user_list(self):
        """Refresh the user list treeview."""
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)
        
        users = self.user_repo.get_all()
        for user in users:
            last_login = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
            self.user_tree.insert("", "end", values=(
                user.username,
                user.full_name or "-",
                user.role.value.title(),
                last_login
            ))
    
    def _register_user(self):
        """Register a new user."""
        username = self.new_username.get().strip().lower()
        password = self.new_password.get()
        full_name = self.new_full_name.get().strip()
        role = UserRole(self.new_role.get())
        
        # Check if username exists
        if self.user_repo.username_exists(username):
            messagebox.showerror("Registration Failed", f"Username '{username}' already exists.")
            return
        
        try:
            self.user_repo.create_user(username, password, role, full_name)
            self.audit_repo.log(
                "CREATE_USER", "user", username,
                f"Created user '{username}' with role '{role.value}'",
                self.admin_user.username
            )
            messagebox.showinfo("Success", f"User '{username}' registered successfully!")
            
            # Clear form
            self.new_username.set("")
            self.new_password.set("")
            self.new_confirm_password.set("")
            self.new_full_name.set("")
            self.new_role.set("staff")
            
            self._refresh_user_list()
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            messagebox.showerror("Error", f"Failed to create user: {e}")
    
    def _delete_selected_user(self):
        """Delete the selected user."""
        selection = self.user_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a user to delete.")
            return
        
        item = self.user_tree.item(selection[0])
        username = item["values"][0]
        
        # Cannot delete self
        if username == self.admin_user.username:
            messagebox.showerror("Cannot Delete", "You cannot delete your own account.")
            return
        
        # Cannot delete default admin
        if username == "admin":
            messagebox.showerror("Cannot Delete", "The default 'admin' account cannot be deleted.")
            return
        
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete user '{username}'?\n\nThis action cannot be undone."):
            return
        
        try:
            self.user_repo.delete_user(username)
            self.audit_repo.log(
                "DELETE_USER", "user", username,
                f"Deleted user '{username}'",
                self.admin_user.username
            )
            messagebox.showinfo("Success", f"User '{username}' deleted.")
            self._refresh_user_list()
            
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            messagebox.showerror("Error", f"Failed to delete user: {e}")


class SalesWindow(tk.Toplevel):
    """
    Enterprise POS (Point of Sale) Window.
    
    Features:
    - Record sales with automatic stock deduction
    - Real-time profit calculation
    - Customer reference tracking
    - Payment method selection
    - Quick barcode scanner support
    - Transaction history view
    """
    
    def __init__(self, master, user: User, product: Optional[Product] = None, 
                 on_sale_complete: Callable[[], None] = None):
        super().__init__(master)
        self.user = user
        self.product = product
        self.on_sale_complete = on_sale_complete
        
        self.db = DatabaseManager()
        self.sales_repo = SalesRepository(self.db)
        self.product_repo = ProductRepository(self.db)
        self.audit_repo = AuditRepository(self.db)
        
        self.title("Record Sale - POS Terminal")
        
        # Hardware-adaptive sizing
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = max(500, min(int(screen_width * 0.35), 600))
        window_height = max(500, min(int(screen_height * 0.55), 650))
        
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(450, 480)
        
        # Center on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.configure(bg=Config.THEME["bg_primary"])
        self.transient(master)
        self.grab_set()
        
        # Form variables
        self.sku_var = tk.StringVar(value=product.sku if product else "")
        self.product_name_var = tk.StringVar(value=product.name if product else "")
        self.available_qty_var = tk.StringVar(value=str(product.quantity) if product else "0")
        self.unit_price_var = tk.StringVar(value=str(product.price) if product else "0.00")
        self.sale_qty_var = tk.StringVar(value="1")
        self.total_var = tk.StringVar(value="₱0.00")
        self.profit_var = tk.StringVar(value="₱0.00")
        self.customer_ref_var = tk.StringVar()
        self.payment_method_var = tk.StringVar(value="cash")
        
        # Barcode listener for quick scanning
        self.barcode_listener = BarcodeListener(on_barcode=self._on_barcode_scan)
        
        self._build_ui()
        self._bind_events()
        self._calculate_total()
    
    def _build_ui(self):
        theme = Config.THEME
        
        # Header
        header = tk.Frame(self, bg=theme["bg_secondary"])
        header.pack(fill="x")
        
        tk.Label(
            header, text="💰 Record Sale", font=("Segoe UI Semibold", 16),
            bg=theme["bg_secondary"], fg=theme["fg_primary"]
        ).pack(side="left", padx=20, pady=16)
        
        tk.Label(
            header, text="POS Terminal", font=("Segoe UI", 10),
            bg=theme["bg_secondary"], fg=theme["fg_muted"]
        ).pack(side="right", padx=20, pady=16)
        
        # Main content
        content = tk.Frame(self, bg=theme["bg_primary"])
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Product Selection
        product_frame = tk.LabelFrame(
            content, text="Product", font=("Segoe UI Semibold", 10),
            bg=theme["bg_card"], fg=theme["fg_primary"],
            highlightthickness=1, highlightbackground=theme["border"]
        )
        product_frame.pack(fill="x", pady=(0, 12))
        
        inner = tk.Frame(product_frame, bg=theme["bg_card"])
        inner.pack(fill="x", padx=12, pady=12)
        
        # SKU with barcode scanner hint
        tk.Label(inner, text="SKU (scan barcode or type):", font=("Segoe UI", 9),
                 bg=theme["bg_card"], fg=theme["fg_secondary"]).pack(anchor="w")
        
        sku_entry = UIComponents.create_entry(inner, self.sku_var, width=20)
        sku_entry.pack(fill="x", pady=(2, 8))
        sku_entry.bind("<Key>", self.barcode_listener.on_key)
        sku_entry.bind("<Return>", lambda e: self._lookup_product())
        
        # Product info (read-only)
        tk.Label(inner, text="Product Name:", font=("Segoe UI", 9),
                 bg=theme["bg_card"], fg=theme["fg_secondary"]).pack(anchor="w")
        name_entry = UIComponents.create_entry(inner, self.product_name_var, width=30)
        name_entry.pack(fill="x", pady=(2, 8))
        name_entry.config(state="readonly")
        
        # Available qty and unit price
        info_row = tk.Frame(inner, bg=theme["bg_card"])
        info_row.pack(fill="x", pady=(0, 4))
        
        tk.Label(info_row, text="Available:", font=("Segoe UI", 9),
                 bg=theme["bg_card"], fg=theme["fg_secondary"]).pack(side="left")
        tk.Label(info_row, textvariable=self.available_qty_var, font=("Segoe UI Semibold", 10),
                 bg=theme["bg_card"], fg=theme["success"]).pack(side="left", padx=(4, 20))
        
        tk.Label(info_row, text="Unit Price: ₱", font=("Segoe UI", 9),
                 bg=theme["bg_card"], fg=theme["fg_secondary"]).pack(side="left")
        tk.Label(info_row, textvariable=self.unit_price_var, font=("Segoe UI Semibold", 10),
                 bg=theme["bg_card"], fg=theme["accent"]).pack(side="left")
        
        # Sale Details
        sale_frame = tk.LabelFrame(
            content, text="Sale Details", font=("Segoe UI Semibold", 10),
            bg=theme["bg_card"], fg=theme["fg_primary"],
            highlightthickness=1, highlightbackground=theme["border"]
        )
        sale_frame.pack(fill="x", pady=(0, 12))
        
        sale_inner = tk.Frame(sale_frame, bg=theme["bg_card"])
        sale_inner.pack(fill="x", padx=12, pady=12)
        
        # Quantity to sell
        qty_row = tk.Frame(sale_inner, bg=theme["bg_card"])
        qty_row.pack(fill="x", pady=(0, 8))
        
        tk.Label(qty_row, text="Quantity to Sell:", font=("Segoe UI", 10),
                 bg=theme["bg_card"], fg=theme["fg_primary"]).pack(side="left")
        
        qty_entry = UIComponents.create_entry(qty_row, self.sale_qty_var, width=10)
        qty_entry.pack(side="right")
        
        # Payment method
        payment_row = tk.Frame(sale_inner, bg=theme["bg_card"])
        payment_row.pack(fill="x", pady=(0, 8))
        
        tk.Label(payment_row, text="Payment Method:", font=("Segoe UI", 10),
                 bg=theme["bg_card"], fg=theme["fg_primary"]).pack(side="left")
        
        for method, label in [("cash", "Cash"), ("card", "Card"), ("credit", "Credit")]:
            tk.Radiobutton(
                payment_row, text=label, variable=self.payment_method_var, value=method,
                font=("Segoe UI", 9), bg=theme["bg_card"], fg=theme["fg_primary"],
                selectcolor=theme["bg_tertiary"], activebackground=theme["bg_card"]
            ).pack(side="right", padx=(8, 0))
        
        # Customer reference
        tk.Label(sale_inner, text="Customer Reference (optional):", font=("Segoe UI", 9),
                 bg=theme["bg_card"], fg=theme["fg_secondary"]).pack(anchor="w")
        UIComponents.create_entry(sale_inner, self.customer_ref_var, width=30).pack(fill="x", pady=(2, 0))
        
        # Totals
        totals_frame = tk.Frame(content, bg=theme["bg_tertiary"])
        totals_frame.pack(fill="x", pady=(0, 12), ipady=12)
        
        totals_inner = tk.Frame(totals_frame, bg=theme["bg_tertiary"])
        totals_inner.pack(fill="x", padx=16)
        
        tk.Label(totals_inner, text="TOTAL:", font=("Segoe UI Semibold", 14),
                 bg=theme["bg_tertiary"], fg=theme["fg_primary"]).pack(side="left")
        tk.Label(totals_inner, textvariable=self.total_var, font=("Segoe UI Black", 20),
                 bg=theme["bg_tertiary"], fg=theme["success"]).pack(side="left", padx=(8, 0))
        
        tk.Label(totals_inner, text="Profit:", font=("Segoe UI", 10),
                 bg=theme["bg_tertiary"], fg=theme["fg_muted"]).pack(side="right")
        tk.Label(totals_inner, textvariable=self.profit_var, font=("Segoe UI Semibold", 12),
                 bg=theme["bg_tertiary"], fg=theme["accent"]).pack(side="right", padx=(0, 8))
        
        # Buttons
        btn_frame = tk.Frame(content, bg=theme["bg_primary"])
        btn_frame.pack(fill="x")
        
        UIComponents.create_button(
            btn_frame, "Cancel", self.destroy, "ghost"
        ).pack(side="left")
        
        self.confirm_btn = UIComponents.create_button(
            btn_frame, "Confirm Sale", self._confirm_sale, "success"
        )
        self.confirm_btn.pack(side="right")
    
    def _bind_events(self):
        """Bind form events for real-time calculation."""
        self.sale_qty_var.trace_add("write", lambda *_: self._calculate_total())
        self.unit_price_var.trace_add("write", lambda *_: self._calculate_total())
    
    def _on_barcode_scan(self, barcode: str):
        """Handle barcode scanner input."""
        self.sku_var.set(barcode)
        self._lookup_product()
    
    def _lookup_product(self):
        """Look up product by SKU."""
        sku = self.sku_var.get().strip()
        if not sku:
            return
        
        product = self.product_repo.get_by_sku(sku)
        if product:
            self.product = product
            self.product_name_var.set(product.name)
            self.available_qty_var.set(str(product.quantity))
            self.unit_price_var.set(str(product.price))
            self._calculate_total()
        else:
            messagebox.showwarning("Not Found", f"Product '{sku}' not found.")
    
    def _calculate_total(self):
        """Calculate sale total and profit in real-time."""
        try:
            qty = int(self.sale_qty_var.get() or 0)
            price = Decimal(self.unit_price_var.get() or "0")
            total = price * qty
            
            profit = Decimal("0")
            if self.product and self.product.cost_price > 0:
                profit = (price - self.product.cost_price) * qty
            
            self.total_var.set(f"₱{total:,.2f}")
            self.profit_var.set(f"₱{profit:,.2f}")
        except (ValueError, InvalidOperation):
            self.total_var.set("₱0.00")
            self.profit_var.set("₱0.00")
    
    def _confirm_sale(self):
        """Process and record the sale."""
        if not self.product:
            messagebox.showwarning("No Product", "Please select a product first.")
            return
        
        try:
            qty = int(self.sale_qty_var.get())
            if qty <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError:
            messagebox.showwarning("Invalid Quantity", "Please enter a valid quantity.")
            return
        
        # Confirm sale
        total = Decimal(self.unit_price_var.get()) * qty
        if not messagebox.askyesno(
            "Confirm Sale",
            f"Record sale of {qty}x {self.product.name}?\n\n"
            f"Total: ₱{total:,.2f}\n"
            f"Payment: {self.payment_method_var.get().title()}"
        ):
            return
        
        # Record the sale
        success, message = self.sales_repo.record_sale(
            sku=self.product.sku,
            product_name=self.product.name,
            quantity=qty,
            unit_price=float(self.product.price),
            cost_price=float(self.product.cost_price),
            customer_ref=self.customer_ref_var.get().strip(),
            payment_method=self.payment_method_var.get(),
            user=self.user.username
        )
        
        if success:
            self.audit_repo.log(
                "SALE", "product", self.product.sku,
                f"Sold {qty}x {self.product.name} for ₱{total:,.2f}",
                self.user.username
            )
            messagebox.showinfo("Sale Complete", message)
            
            if self.on_sale_complete:
                self.on_sale_complete()
            
            self.destroy()
        else:
            messagebox.showerror("Sale Failed", message)


class DashboardView(tk.Frame):
    """Main dashboard with inventory management"""
    
    # Weak reference cache for images to prevent memory leaks
    _image_cache: ClassVar[weakref.WeakValueDictionary] = weakref.WeakValueDictionary()
    
    def __init__(self, master, user: User, on_logout: Callable[[], None]):
        super().__init__(master, bg=Config.THEME["bg_primary"])
        self.user = user
        self.on_logout = on_logout
        
        # Initialize repositories
        self.db = DatabaseManager()
        self.product_repo = ProductRepository(self.db)
        self.audit_repo = AuditRepository(self.db)
        self.user_repo = UserRepository(self.db)
        self.prefs_repo = UserPreferencesRepository(self.db)
        
        # RBAC: Determine user permissions
        self.can_modify = self.user.role in (UserRole.ADMIN, UserRole.MANAGER)
        self.is_admin = self.user.role == UserRole.ADMIN
        
        # State variables
        self.search_var = tk.StringVar()
        self.selected_product: Optional[Product] = None
        self.current_image_path = tk.StringVar()
        
        # Smart Search filter variables
        self.filter_category = tk.StringVar(value="All Categories")
        self.filter_status = tk.StringVar(value="All Status")
        
        # Form variables with validation traces
        self.form_vars: Dict[str, tk.StringVar] = {
            "sku": tk.StringVar(),
            "name": tk.StringVar(),
            "brand": tk.StringVar(),
            "price": tk.StringVar(),
            "cost_price": tk.StringVar(),
            "quantity": tk.StringVar(),
            "category": tk.StringVar(),
            "supplier": tk.StringVar(),
            "min_stock": tk.StringVar(value="5"),
        }
        
        # Stats variables
        self.stat_vars: Dict[str, tk.StringVar] = {
            "total_value": tk.StringVar(value="₱0.00"),
            "total_products": tk.StringVar(value="0"),
            "total_units": tk.StringVar(value="0"),
            "low_stock": tk.StringVar(value="0"),
            "aging_count": tk.StringVar(value="0"),
            "avg_margin": tk.StringVar(value="0%"),
        }
        
        # Button references for dynamic state
        self.save_btn: Optional[tk.Button] = None
        self.update_btn: Optional[tk.Button] = None
        self.delete_btn: Optional[tk.Button] = None
        
        # Barcode scanner listener for rapid SKU entry
        self.barcode_listener = BarcodeListener(on_barcode=self._on_barcode_scan)
        
        self._build_ui()
        self._setup_validation_traces()
        self._refresh_data()
    
    def _setup_validation_traces(self) -> None:
        """Setup real-time validation traces on required fields."""
        required_fields = ["sku", "name", "price", "quantity"]
        for field in required_fields:
            self.form_vars[field].trace_add("write", self._on_form_change)
    
    def _on_form_change(self, *args: Any) -> None:
        """Handle form field changes - update button states with RBAC."""
        is_valid = self._is_form_valid()
        has_selection = self.selected_product is not None
        
        # RBAC: Staff users cannot modify inventory
        if not self.can_modify:
            if self.save_btn:
                self.save_btn.config(state="disabled", bg=Config.THEME["bg_tertiary"], cursor="arrow")
            if self.update_btn:
                self.update_btn.config(state="disabled", bg=Config.THEME["bg_tertiary"], cursor="arrow")
            if self.delete_btn:
                self.delete_btn.config(state="disabled", bg=Config.THEME["bg_tertiary"], cursor="arrow")
            return
        
        # Update Save button state
        if self.save_btn:
            if is_valid:
                self.save_btn.config(
                    state="normal",
                    bg=Config.THEME["success"],
                    cursor="hand2"
                )
            else:
                self.save_btn.config(
                    state="disabled",
                    bg=Config.THEME["bg_tertiary"],
                    cursor="arrow"
                )
        
        # Update Update/Delete button states
        if self.update_btn:
            if is_valid and has_selection:
                self.update_btn.config(state="normal", bg=Config.THEME["accent"], cursor="hand2")
            else:
                self.update_btn.config(state="disabled", bg=Config.THEME["bg_tertiary"], cursor="arrow")
        
        if self.delete_btn:
            if has_selection:
                self.delete_btn.config(state="normal", bg=Config.THEME["danger"], cursor="hand2")
            else:
                self.delete_btn.config(state="disabled", bg=Config.THEME["bg_tertiary"], cursor="arrow")
    
    def _is_form_valid(self) -> bool:
        """Check if all required form fields are valid."""
        sku = self.form_vars["sku"].get().strip()
        name = self.form_vars["name"].get().strip()
        price_str = self.form_vars["price"].get().strip()
        qty_str = self.form_vars["quantity"].get().strip()
        
        if not sku or not name:
            return False
        
        # Validate price
        try:
            price = Decimal(price_str)
            if price < 0:
                return False
        except (InvalidOperation, ValueError):
            return False
        
        # Validate quantity
        try:
            qty = int(qty_str)
            if qty < 0:
                return False
        except ValueError:
            return False
        
        return True
    
    def _build_ui(self):
        theme = Config.THEME
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # === SIDEBAR ===
        self._build_sidebar()
        
        # === MAIN CONTENT ===
        main = tk.Frame(self, bg=theme["bg_primary"])
        main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)
        
        # Header with search
        self._build_header(main)
        
        # Stats row
        self._build_stats_row(main)
        
        # Content area (Table + Form)
        self._build_content_area(main)
    
    def _build_sidebar(self):
        theme = Config.THEME
        
        sidebar = tk.Frame(self, bg=theme["bg_secondary"], width=240)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # Brand
        brand_frame = tk.Frame(sidebar, bg=theme["bg_secondary"])
        brand_frame.pack(fill="x", pady=30)
        
        tk.Label(
            brand_frame, text="INVENTORY", font=("Segoe UI Black", 20),
            bg=theme["bg_secondary"], fg=theme["accent"]
        ).pack()
        tk.Label(
            brand_frame, text="SYSTEM", font=("Segoe UI Light", 12),
            bg=theme["bg_secondary"], fg=theme["fg_muted"]
        ).pack()
        
        # Image preview
        img_frame = tk.Frame(sidebar, bg=theme["bg_tertiary"], width=200, height=160)
        img_frame.pack(pady=15)
        img_frame.pack_propagate(False)
        
        self.img_label = tk.Label(
            img_frame, text="NO IMAGE", font=("Segoe UI", 10),
            bg=theme["bg_tertiary"], fg=theme["fg_muted"]
        )
        self.img_label.pack(fill="both", expand=True)
        
        # Sidebar buttons
        btn_frame = tk.Frame(sidebar, bg=theme["bg_secondary"])
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        UIComponents.create_button(
            btn_frame, "Upload Image", self._upload_image, "secondary", icon="📷"
        ).pack(fill="x", pady=4)
        
        UIComponents.create_button(
            btn_frame, "Export to CSV", self._export_csv, "warning", icon="📊"
        ).pack(fill="x", pady=4)
        
        # Manager/Admin: Record Sale (POS)
        if self.can_modify:
            UIComponents.create_button(
                btn_frame, "Record Sale", self._open_sales_window, "success", icon="💰"
            ).pack(fill="x", pady=4)
        
        UIComponents.create_button(
            btn_frame, "Generate Report", self._generate_report, "secondary", icon="📋"
        ).pack(fill="x", pady=4)
        
        # Admin-only: User Management
        if self.is_admin:
            UIComponents.create_button(
                btn_frame, "Manage Users", self._open_user_management, "primary", icon="👥"
            ).pack(fill="x", pady=4)
        
        # RBAC indicator for Staff
        if not self.can_modify:
            rbac_label = tk.Label(
                btn_frame, text="⚠️ View-Only Mode",
                font=("Segoe UI", 9), bg=theme["bg_secondary"], fg=theme["warning"]
            )
            rbac_label.pack(fill="x", pady=(8, 0))
        
        # User info at bottom
        user_frame = tk.Frame(sidebar, bg=theme["bg_tertiary"])
        user_frame.pack(side="bottom", fill="x", pady=0)
        
        user_info = tk.Frame(user_frame, bg=theme["bg_tertiary"])
        user_info.pack(fill="x", padx=16, pady=12)
        
        tk.Label(
            user_info, text=f"👤 {self.user.full_name or self.user.username}",
            font=("Segoe UI Semibold", 10), bg=theme["bg_tertiary"], fg=theme["fg_primary"]
        ).pack(anchor="w")
        
        tk.Label(
            user_info, text=f"Role: {self.user.role.value.title()}",
            font=("Segoe UI", 9), bg=theme["bg_tertiary"], fg=theme["fg_muted"]
        ).pack(anchor="w")
        
        UIComponents.create_button(
            user_frame, "Sign Out", self._handle_logout, "danger"
        ).pack(fill="x", padx=16, pady=(0, 16))
    
    def _build_header(self, parent):
        theme = Config.THEME
        
        header = tk.Frame(parent, bg=theme["bg_primary"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        
        # Title
        tk.Label(
            header, text="Inventory Dashboard", font=("Segoe UI Semibold", 20),
            bg=theme["bg_primary"], fg=theme["fg_primary"]
        ).pack(side="left")
        
        # === SMART SEARCH BAR ===
        search_container = tk.Frame(header, bg=theme["bg_primary"])
        search_container.pack(side="right")
        
        # Status filter dropdown
        status_options = ["All Status", "In Stock", "Low Stock", "Critical Stock"]
        status_combo = ttk.Combobox(
            search_container, textvariable=self.filter_status,
            values=status_options, state="readonly", width=12,
            font=("Segoe UI", 9)
        )
        status_combo.pack(side="right", padx=(8, 0))
        status_combo.bind("<<ComboboxSelected>>", lambda *_: self._filter_products())
        
        # Category filter dropdown
        category_options = ["All Categories"] + Config.CATEGORIES
        category_combo = ttk.Combobox(
            search_container, textvariable=self.filter_category,
            values=category_options, state="readonly", width=14,
            font=("Segoe UI", 9)
        )
        category_combo.pack(side="right", padx=(8, 0))
        category_combo.bind("<<ComboboxSelected>>", lambda *_: self._filter_products())
        
        # Fuzzy search bar
        search_frame = tk.Frame(search_container, bg=theme["bg_secondary"], padx=12, pady=8)
        search_frame.pack(side="right")
        
        tk.Label(
            search_frame, text="🔍", font=("Segoe UI", 12),
            bg=theme["bg_secondary"], fg=theme["fg_muted"]
        ).pack(side="left", padx=(0, 8))
        
        search_entry = UIComponents.create_entry(
            search_frame, self.search_var, placeholder="Smart search (SKU, Name, Brand, Supplier)...", width=32
        )
        search_entry.pack(side="left")
        search_entry.config(relief="flat", highlightthickness=0, bg=theme["bg_secondary"])
        
        self.search_var.trace_add("write", lambda *_: self._filter_products())
    
    def _build_stats_row(self, parent):
        theme = Config.THEME
        
        stats_frame = tk.Frame(parent, bg=theme["bg_primary"])
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        
        # Primary stats (first row)
        primary_cards = [
            ("Total Value", self.stat_vars["total_value"], theme["success"]),
            ("Products", self.stat_vars["total_products"], theme["accent"]),
            ("Units", self.stat_vars["total_units"], "#8b5cf6"),
            ("Low Stock", self.stat_vars["low_stock"], theme["danger"]),
            ("Aging", self.stat_vars["aging_count"], "#9333ea"),
            ("Avg Margin", self.stat_vars["avg_margin"], "#0891b2"),
        ]
        
        for title, var, color in primary_cards:
            card = UIComponents.create_stat_card(stats_frame, title, var, color)
            card.pack(side="left", padx=(0, 8))
    
    def _build_content_area(self, parent):
        theme = Config.THEME
        
        content = tk.Frame(parent, bg=theme["bg_primary"])
        content.grid(row=2, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # === TABLE SECTION ===
        table_container = tk.Frame(content, bg=theme["bg_card"])
        table_container.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        
        # Table header
        table_header = tk.Frame(table_container, bg=theme["bg_card"])
        table_header.pack(fill="x", padx=16, pady=12)
        
        tk.Label(
            table_header, text="Product Inventory", font=("Segoe UI Semibold", 14),
            bg=theme["bg_card"], fg=theme["fg_primary"]
        ).pack(side="left")
        
        UIComponents.create_button(
            table_header, "Refresh", self._refresh_data, "ghost", icon="🔄"
        ).pack(side="right")
        
        # Treeview with custom style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background=theme["bg_card"],
            foreground=theme["fg_primary"],
            fieldbackground=theme["bg_card"],
            rowheight=40,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=theme["bg_tertiary"],
            foreground=theme["fg_primary"],
            font=("Segoe UI Semibold", 10),
            borderwidth=0,
            relief="flat",
        )
        style.map("Custom.Treeview", background=[("selected", theme["accent"])])
        style.map("Custom.Treeview.Heading", background=[("active", theme["bg_tertiary"])])
        
        # Treeview
        columns = ("SKU", "Product Name", "Brand", "Supplier", "Price", "Qty", "Category", "Status", "Health")
        self.tree = ttk.Treeview(
            table_container, columns=columns, show="headings",
            style="Custom.Treeview", selectmode="browse"
        )
        
        col_widths = {"SKU": 95, "Product Name": 140, "Brand": 75, "Supplier": 90, "Price": 80, 
                      "Qty": 45, "Category": 85, "Status": 55, "Health": 55}
        
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, width=col_widths.get(col, 70), anchor="center" if col in ["Qty", "Status", "Health"] else "w")
        
        # Tags for row colors (stock and health-based)
        self.tree.tag_configure("critical", background="#7f1d1d")  # Critical stock
        self.tree.tag_configure("low", background="#78350f")       # Low stock
        self.tree.tag_configure("aging", background="#6b21a8")     # Aging inventory (>90 days)
        self.tree.tag_configure("low_margin", background="#9a3412") # Low profit margin
        self.tree.tag_configure("healthy", background="#166534")   # Healthy product
        self.tree.tag_configure("normal", background=theme["bg_card"])
        self.tree.tag_configure("stripe", background=theme["table_stripe"])
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
        scrollbar.pack(side="right", fill="y", pady=(0, 16), padx=(0, 8))
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        
        # === FORM SECTION ===
        self._build_form(content)
    
    def _build_form(self, parent):
        theme = Config.THEME
        
        form_container = tk.Frame(parent, bg=theme["bg_card"], width=320)
        form_container.grid(row=0, column=1, sticky="nsew")
        form_container.grid_propagate(False)
        
        # Form header
        header = tk.Frame(form_container, bg=theme["bg_card"])
        header.pack(fill="x", padx=12, pady=6)
        
        tk.Label(
            header, text="Product Details", font=("Segoe UI Semibold", 12),
            bg=theme["bg_card"], fg=theme["fg_primary"]
        ).pack(side="left")
        
        UIComponents.create_button(
            header, "Clear", self._clear_form, "ghost"
        ).pack(side="right")
        
        # Action buttons FIRST (pack at bottom before fields)
        btn_frame = tk.Frame(form_container, bg=theme["bg_card"])
        btn_frame.pack(fill="x", padx=12, pady=8, side="bottom")
        
        # Save button - disabled by default until form is valid
        self.save_btn = UIComponents.create_button(
            btn_frame, "Save New", self._save_product, "success"
        )
        self.save_btn.config(state="disabled", bg=theme["bg_tertiary"], cursor="arrow")
        self.save_btn.pack(fill="x", pady=1)
        
        # Update button - disabled until selection + valid form
        self.update_btn = UIComponents.create_button(
            btn_frame, "Update", self._update_product, "primary"
        )
        self.update_btn.config(state="disabled", bg=theme["bg_tertiary"], cursor="arrow")
        self.update_btn.pack(fill="x", pady=1)
        
        # Delete button - disabled until selection
        self.delete_btn = UIComponents.create_button(
            btn_frame, "Delete", self._delete_product, "danger"
        )
        self.delete_btn.config(state="disabled", bg=theme["bg_tertiary"], cursor="arrow")
        self.delete_btn.pack(fill="x", pady=1)
        
        # Form fields (pack after buttons so they fill remaining space)
        form = tk.Frame(form_container, bg=theme["bg_card"])
        form.pack(fill="both", expand=True, padx=12)
        
        fields = [
            ("SKU *", "sku", False),
            ("Product Name *", "name", False),
            ("Brand", "brand", False),
            ("Price (₱) *", "price", False),
            ("Cost Price (₱)", "cost_price", False),
            ("Quantity *", "quantity", False),
            ("Category", "category", True),
            ("Supplier", "supplier", False),
            ("Min Stock Alert", "min_stock", False),
        ]
        
        for label_text, key, is_dropdown in fields:
            tk.Label(
                form, text=label_text, font=("Segoe UI", 8),
                bg=theme["bg_card"], fg=theme["fg_secondary"]
            ).pack(anchor="w", pady=(2, 1))
            
            if key == "sku":
                sku_frame = tk.Frame(form, bg=theme["bg_card"])
                sku_frame.pack(fill="x")
                
                entry = UIComponents.create_entry(sku_frame, self.form_vars[key], width=20)
                entry.pack(side="left", fill="x", expand=True, ipady=2)
                
                # Bind barcode scanner detection
                entry.bind("<Key>", self.barcode_listener.on_key)
                
                UIComponents.create_button(
                    sku_frame, "GEN", self._generate_sku, "secondary"
                ).pack(side="right", padx=(6, 0))
                
            elif is_dropdown:
                combo = ttk.Combobox(
                    form, textvariable=self.form_vars[key],
                    values=Config.CATEGORIES, state="readonly",
                    font=("Segoe UI", 9)
                )
                combo.pack(fill="x", ipady=2)
            else:
                entry = UIComponents.create_entry(form, self.form_vars[key], width=28)
                entry.pack(fill="x", ipady=2)
    
    # === DATA OPERATIONS ===
    
    def _refresh_data(self):
        """Refresh table and statistics with Smart Search filters and health indicators."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load products with multi-criteria filtering
        products = self.product_repo.get_all(
            search=self.search_var.get(),
            category=self.filter_category.get(),
            status=self.filter_status.get()
        )
        
        for i, product in enumerate(products):
            # Stock status indicator
            if product.stock_status == "critical":
                status = "🔴"
                tag = "critical"
            elif product.stock_status == "low":
                status = "⚠️"
                tag = "low"
            else:
                status = "✓"
                tag = "stripe" if i % 2 else "normal"
            
            # Health indicator based on multiple factors
            health_score = product.health_score
            if health_score >= 80:
                health = "🟢"  # Excellent
            elif health_score >= 60:
                health = "🟡"  # Good
            elif health_score >= 40:
                health = "🟠"  # Fair
            else:
                health = "🔴"  # Poor
            
            # Override tag for special conditions
            if product.is_aging and tag not in ("critical", "low"):
                tag = "aging"
            elif product.is_low_margin and tag not in ("critical", "low", "aging"):
                tag = "low_margin"
            
            # Truncate supplier for display (unique identifier)
            supplier_display = (product.supplier[:12] + "…") if len(product.supplier) > 13 else product.supplier
            
            self.tree.insert("", "end", values=(
                product.sku,
                product.name,
                product.brand,
                supplier_display or "-",
                f"₱{product.price:,.2f}",
                product.quantity,
                product.category,
                status,
                health
            ), tags=(tag,))
        
        # Calculate health metrics
        aging_count = sum(1 for p in products if p.is_aging)
        margins = [float(p.profit_margin) for p in products if p.profit_margin is not None]
        avg_margin = sum(margins) / len(margins) if margins else 0.0
        
        # Update statistics
        stats = self.product_repo.get_statistics()
        self.stat_vars["total_value"].set(f"₱{stats['total_value']:,.2f}")
        self.stat_vars["total_products"].set(str(stats["total_products"]))
        self.stat_vars["total_units"].set(f"{stats['total_units']:,}")
        self.stat_vars["low_stock"].set(str(stats["low_stock_count"]))
        self.stat_vars["aging_count"].set(str(aging_count))
        self.stat_vars["avg_margin"].set(f"{avg_margin:.1f}%")
    
    def _filter_products(self) -> None:
        """
        Apply current search and filter criteria to the product list.
        
        Triggers a full data refresh with the current search_var,
        filter_category, and filter_status values.
        """
        self._refresh_data()
    
    def _sort_column(self, col: str) -> None:
        """
        Sort treeview data by the specified column.
        
        Args:
            col: Column name to sort by. Numeric columns (Price, Qty)
                 are sorted numerically; others alphabetically.
        """
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
        
        try:
            if col in ["Price", "Qty"]:
                data.sort(key=lambda x: float(x[0].replace("₱", "").replace(",", "").replace("-", "0") or 0), reverse=True)
            else:
                data.sort(key=lambda x: str(x[0]).lower())
        except (ValueError, TypeError, AttributeError):
            # Fallback: simple string sort if parsing fails
            data.sort(key=lambda x: str(x[0]))
        
        for index, (_, child) in enumerate(data):
            self.tree.move(child, "", index)
    
    def _on_select(self, event) -> None:
        """
        Handle Treeview row selection event.
        
        Populates the form fields with the selected product's data
        and updates button states based on RBAC permissions.
        
        Args:
            event: Tkinter event object (unused but required for binding)
        """
        selected = self.tree.focus()
        if not selected:
            return
        
        values = self.tree.item(selected)["values"]
        product = self.product_repo.get_by_sku(values[0])
        
        if product:
            self.selected_product = product
            self.form_vars["sku"].set(product.sku)
            self.form_vars["name"].set(product.name)
            self.form_vars["brand"].set(product.brand)
            self.form_vars["price"].set(str(product.price))
            self.form_vars["cost_price"].set(str(product.cost_price))
            self.form_vars["quantity"].set(str(product.quantity))
            self.form_vars["category"].set(product.category)
            self.form_vars["supplier"].set(product.supplier)
            self.form_vars["min_stock"].set(str(product.min_stock))
            self.current_image_path.set(product.image_path)
            self._load_image(product.image_path)
            
            # Update button states for selection
            self._on_form_change()
    
    def _on_double_click(self, event) -> None:
        """
        Handle double-click event for quick product editing.
        
        Args:
            event: Tkinter event object passed to _on_select
        """
        self._on_select(event)
    
    def _validate_form(self) -> Optional[Product]:
        """
        Validate form inputs and construct a Product object.
        
        Performs validation on required fields (SKU, name, price, quantity)
        and returns a Product instance if all validations pass.
        
        Returns:
            Product object if valid, None if validation fails
            (with error message shown to user)
        """
        sku = self.form_vars["sku"].get().strip()
        name = self.form_vars["name"].get().strip()
        price_str = self.form_vars["price"].get().strip()
        qty_str = self.form_vars["quantity"].get().strip()
        
        if not sku:
            messagebox.showwarning("Validation Error", "SKU is required.")
            return None
        
        if not name:
            messagebox.showwarning("Validation Error", "Product name is required.")
            return None
        
        try:
            price = Decimal(price_str)
            if price < 0:
                raise ValueError("Negative price")
        except (InvalidOperation, ValueError):
            messagebox.showwarning("Validation Error", "Please enter a valid price (positive number).")
            return None
        
        try:
            quantity = int(qty_str)
            if quantity < 0:
                raise ValueError("Negative quantity")
        except ValueError:
            messagebox.showwarning("Validation Error", "Please enter a valid quantity (whole number ≥ 0).")
            return None
        
        try:
            min_stock = int(self.form_vars["min_stock"].get() or "5")
        except ValueError:
            min_stock = 5
        
        # Parse cost price (optional)
        try:
            cost_price = Decimal(self.form_vars["cost_price"].get().strip() or "0")
            if cost_price < 0:
                cost_price = Decimal("0")
        except (InvalidOperation, ValueError):
            cost_price = Decimal("0")
        
        return Product(
            sku=sku,
            name=name,
            brand=self.form_vars["brand"].get().strip(),
            price=price,
            cost_price=cost_price,
            quantity=quantity,
            category=self.form_vars["category"].get(),
            supplier=self.form_vars["supplier"].get().strip(),
            image_path=self.current_image_path.get(),
            min_stock=min_stock,
        )
    
    def _save_product(self):
        """Save new product"""
        product = self._validate_form()
        if not product:
            return
        
        # Check if SKU exists
        if self.product_repo.get_by_sku(product.sku):
            messagebox.showerror("Error", f"SKU '{product.sku}' already exists.")
            return
        
        try:
            self.product_repo.save(product)
            self.audit_repo.log("CREATE", "product", product.sku, f"Created product: {product.name}", self.user.username)
            messagebox.showinfo("Success", f"Product '{product.name}' saved successfully.")
            self._clear_form()
            self._refresh_data()
        except Exception as e:
            logger.error(f"Failed to save product: {e}")
            messagebox.showerror("Error", f"Failed to save product: {e}")
    
    def _update_product(self):
        """Update existing product"""
        product = self._validate_form()
        if not product:
            return
        
        if not self.product_repo.get_by_sku(product.sku):
            messagebox.showerror("Error", f"Product with SKU '{product.sku}' not found.")
            return
        
        if not messagebox.askyesno("Confirm Update", f"Update product '{product.name}'?"):
            return
        
        try:
            self.product_repo.update(product)
            self.audit_repo.log("UPDATE", "product", product.sku, f"Updated product: {product.name}", self.user.username)
            messagebox.showinfo("Success", f"Product '{product.name}' updated successfully.")
            self._refresh_data()
        except Exception as e:
            logger.error(f"Failed to update product: {e}")
            messagebox.showerror("Error", f"Failed to update product: {e}")
    
    def _delete_product(self):
        """Delete selected product"""
        sku = self.form_vars["sku"].get().strip()
        
        if not sku:
            messagebox.showwarning("Selection Required", "Please select a product to delete.")
            return
        
        product = self.product_repo.get_by_sku(sku)
        if not product:
            messagebox.showerror("Error", "Product not found.")
            return
        
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete '{product.name}'?\n\nThis action cannot be undone."):
            return
        
        try:
            self.product_repo.delete(sku)
            self.audit_repo.log("DELETE", "product", sku, f"Deleted product: {product.name}", self.user.username)
            messagebox.showinfo("Success", f"Product '{product.name}' deleted.")
            self._clear_form()
            self._refresh_data()
        except Exception as e:
            logger.error(f"Failed to delete product: {e}")
            messagebox.showerror("Error", f"Failed to delete product: {e}")
    
    def _clear_form(self) -> None:
        """Clear all form fields and reset button states."""
        for var in self.form_vars.values():
            var.set("")
        self.form_vars["min_stock"].set("5")
        self.selected_product = None
        self.current_image_path.set("")
        self.img_label.config(image="", text="NO IMAGE")
        
        # Trigger validation update
        self._on_form_change()
        
        # Clean up image cache periodically
        gc.collect()
    
    def _generate_sku(self):
        """Generate unique SKU"""
        prefix = "CP"
        while True:
            sku = f"{prefix}-{random.randint(10000, 99999)}"
            if not self.product_repo.get_by_sku(sku):
                self.form_vars["sku"].set(sku)
                break
    
    def _on_barcode_scan(self, barcode: str):
        """
        Handle barcode scanner input with Quick-View popup.
        
        When a barcode is detected via rapid keystroke pattern,
        this method looks up the product and offers quick actions.
        """
        product = self.product_repo.get_by_sku(barcode)
        
        if product:
            # Product found - show Quick-View popup
            self._show_barcode_quick_view(product)
        else:
            # New barcode - populate SKU field for new entry
            self.form_vars["sku"].set(barcode)
            messagebox.showinfo(
                "New Product", 
                f"SKU '{barcode}' not found.\n\nThe SKU field has been populated for new product entry."
            )
    
    def _show_barcode_quick_view(self, product: Product):
        """Display Quick-View popup for scanned product."""
        theme = Config.THEME
        
        popup = tk.Toplevel(self)
        popup.title(f"Quick View: {product.sku}")
        popup.geometry("400x300")
        popup.configure(bg=theme["bg_card"])
        popup.transient(self)
        popup.grab_set()
        
        # Center popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 400) // 2
        y = (popup.winfo_screenheight() - 300) // 2
        popup.geometry(f"400x300+{x}+{y}")
        
        # Header
        header = tk.Frame(popup, bg=theme["bg_secondary"])
        header.pack(fill="x")
        tk.Label(
            header, text=f"📦 {product.name}", font=("Segoe UI Semibold", 14),
            bg=theme["bg_secondary"], fg=theme["fg_primary"]
        ).pack(padx=16, pady=12)
        
        # Product info
        info = tk.Frame(popup, bg=theme["bg_card"])
        info.pack(fill="both", expand=True, padx=16, pady=12)
        
        details = [
            ("SKU", product.sku),
            ("Brand", product.brand or "N/A"),
            ("Price", f"₱{product.price:,.2f}"),
            ("In Stock", f"{product.quantity} units"),
            ("Status", product.stock_status.title().replace("_", " ")),
            ("Category", product.category or "N/A"),
        ]
        
        for label, value in details:
            row = tk.Frame(info, bg=theme["bg_card"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=("Segoe UI", 10), width=10, anchor="w",
                     bg=theme["bg_card"], fg=theme["fg_muted"]).pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI Semibold", 10),
                     bg=theme["bg_card"], fg=theme["fg_primary"]).pack(side="left")
        
        # Action buttons
        btn_frame = tk.Frame(popup, bg=theme["bg_card"])
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        def view_product():
            popup.destroy()
            self._select_product_by_sku(product.sku)
        
        def sell_product():
            popup.destroy()
            if self.can_modify:
                self._open_sales_window(product)
            else:
                messagebox.showwarning("Access Denied", "Sales recording requires Manager or Admin role.")
        
        UIComponents.create_button(btn_frame, "View Details", view_product, "primary").pack(side="left", padx=(0, 8))
        
        if self.can_modify:
            UIComponents.create_button(btn_frame, "Sell", sell_product, "success").pack(side="left", padx=(0, 8))
        
        UIComponents.create_button(btn_frame, "Close", popup.destroy, "ghost").pack(side="right")
    
    def _select_product_by_sku(self, sku: str):
        """Select a product in the table by SKU."""
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values and values[0] == sku:
                self.tree.selection_set(item)
                self.tree.see(item)
                self._on_row_click(None)
                break
    
    def _upload_image(self):
        """Upload product image"""
        sku = self.form_vars["sku"].get().strip()
        if not sku:
            messagebox.showwarning("SKU Required", "Please enter or generate a SKU first.")
            return
        
        file_path = filedialog.askopenfilename(
            title="Select Product Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp")]
        )
        
        if not file_path:
            return
        
        # Validate file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > Config.MAX_IMAGE_SIZE_MB:
            messagebox.showerror("Error", f"Image size exceeds {Config.MAX_IMAGE_SIZE_MB}MB limit.")
            return
        
        # Copy to assets folder
        Config.ASSETS_PATH.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(file_path)[1].lower()
        dest_path = Config.ASSETS_PATH / f"{sku}{ext}"
        
        try:
            shutil.copy(file_path, dest_path)
            self.current_image_path.set(str(dest_path))
            self._load_image(str(dest_path))
            logger.info(f"Image uploaded for SKU: {sku}")
        except Exception as e:
            logger.error(f"Failed to upload image: {e}")
            messagebox.showerror("Error", f"Failed to upload image: {e}")
    
    def _load_image(self, path: str) -> None:
        """Load and display image with weak reference caching."""
        theme = Config.THEME
        
        if path and os.path.exists(path):
            try:
                # Check cache first (weak references auto-clean unused images)
                if path in self._image_cache:
                    photo = self._image_cache[path]
                    if photo is not None:  # WeakRef may have been garbage collected
                        self.img_label.config(image=photo, text="")
                        self.img_label.image = photo
                        return
                
                # Limit cache size to prevent memory bloat
                if len(self._image_cache) > 50:
                    # Clear old weak refs that have been garbage collected
                    self._image_cache = weakref.WeakValueDictionary({
                        k: v for k, v in self._image_cache.items() if v is not None
                    })
                    gc.collect()
                
                # Load and cache new image with optimized memory usage
                with Image.open(path) as img:
                    img = img.resize((200, 160), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                
                # Store in weak cache and strong reference on label
                self._image_cache[path] = photo
                self.img_label.config(image=photo, text="")
                self.img_label.image = photo
                return
            except Exception as e:
                logger.error(f"Failed to load image: {e}")
        
        self.img_label.config(image="", text="NO IMAGE")
    
    def _export_csv(self):
        """
        Export inventory to CSV with BI metrics.
        
        Uses background threading to prevent UI lag on large datasets.
        Shows loading indicator during export operation.
        """
        file_path = filedialog.asksaveasfilename(
            title="Export Inventory",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfilename=f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not file_path:
            return
        
        # Show loading indicator
        loading = UIComponents.show_loading(self, "Exporting inventory...")
        
        def do_export() -> tuple:
            """Background export task."""
            products = self.product_repo.get_all()
            
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "SKU", "Product Name", "Brand", "Price", "Cost Price", "Profit Margin %",
                    "Quantity", "Category", "Supplier", "Min Stock", "Total Value",
                    "Days in Stock", "Health Score", "Total Sold"
                ])
                
                for p in products:
                    writer.writerow([
                        p.sku, p.name, p.brand, float(p.price), float(p.cost_price),
                        f"{p.profit_margin:.1f}" if p.profit_margin else "N/A",
                        p.quantity, p.category, p.supplier, p.min_stock, float(p.total_value),
                        p.days_in_stock, p.health_score, p.total_sold
                    ])
            
            return len(products), file_path
        
        def on_complete(result: tuple):
            """Handle export completion."""
            loading.destroy()
            count, path = result
            self.audit_repo.log("EXPORT", "inventory", "", f"Exported {count} products to CSV", self.user.username)
            messagebox.showinfo("Export Complete", f"Successfully exported {count} products to:\n{path}")
            logger.info(f"Inventory exported to: {path}")
        
        def on_error(e: Exception):
            """Handle export error."""
            loading.destroy()
            logger.error(f"Export failed: {e}")
            messagebox.showerror("Export Failed", f"Failed to export: {e}")
        
        run_in_background(
            target=do_export,
            on_complete=on_complete,
            on_error=on_error,
            master=self.master
        )
    
    def _generate_report(self):
        """
        Generate inventory summary report with BI insights.
        
        Uses background threading for data aggregation to prevent UI freeze
        when processing large product catalogs.
        """
        # Show loading indicator
        loading = UIComponents.show_loading(self, "Generating report...")
        
        def do_generate() -> str:
            """Background report generation task."""
            stats = self.product_repo.get_statistics()
            products = self.product_repo.get_all()
            
            low_stock_items = [p for p in products if p.stock_status in ["low", "critical"]]
            aging_items = [p for p in products if p.is_aging]
            low_margin_items = [p for p in products if p.is_low_margin]
            
            # Calculate averages
            margins = [float(p.profit_margin) for p in products if p.profit_margin is not None]
            avg_margin = sum(margins) / len(margins) if margins else 0.0
            health_scores = [p.health_score for p in products]
            avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
            
            report = f"""
══════════════════════════════════════════════
     INVENTORY SYSTEM - BUSINESS INTELLIGENCE REPORT
══════════════════════════════════════════════
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Generated by: {self.user.full_name or self.user.username}
══════════════════════════════════════════════

INVENTORY SUMMARY
────────────────────────────────────────────
Total Products:     {stats['total_products']:,}
Total Units:        {stats['total_units']:,}
Inventory Value:    ₱{stats['total_value']:,.2f}
Low Stock Items:    {stats['low_stock_count']}
Critical Stock:     {stats['critical_stock_count']}

HEALTH INDICATORS
────────────────────────────────────────────
Average Health Score:  {avg_health:.0f}/100
Average Profit Margin: {avg_margin:.1f}%
Aging Inventory (>90d): {len(aging_items)}
Low Margin Items (<15%): {len(low_margin_items)}

"""
            
            if low_stock_items:
                report += """LOW STOCK ALERTS
────────────────────────────────────────────
"""
                for p in low_stock_items:
                    status = "🔴 CRITICAL" if p.stock_status == "critical" else "⚠️ LOW"
                    report += f"• [{p.sku}] {p.name}: {p.quantity} units {status}\n"
            
            if aging_items:
                report += """
AGING INVENTORY (>90 DAYS)
────────────────────────────────────────────
"""
                for p in aging_items:
                    report += f"• [{p.sku}] {p.name}: {p.days_in_stock} days, {p.quantity} units\n"
            
            if low_margin_items:
                report += """
LOW MARGIN PRODUCTS (<15%)
────────────────────────────────────────────
"""
                for p in low_margin_items:
                    margin = p.profit_margin if p.profit_margin else 0
                    report += f"• [{p.sku}] {p.name}: {margin:.1f}% margin\n"
            
            report += """
══════════════════════════════════════════════
         END OF REPORT
══════════════════════════════════════════════
"""
            return report
        
        def on_complete(report: str):
            """Handle report generation completion."""
            loading.destroy()
            
            # Ask user where to save
            file_path = filedialog.asksaveasfilename(
                title="Save Report",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")],
                initialfilename=f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            
            if file_path:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(report)
                    self.audit_repo.log("REPORT", "inventory", "", "Generated inventory report", self.user.username)
                    messagebox.showinfo("Report Generated", f"Report saved to:\n{file_path}")
                except (IOError, PermissionError, OSError) as e:
                    logger.error(f"Failed to save report: {e}")
                    messagebox.showerror("Save Failed", f"Could not save report:\n{e}")
        
        def on_error(e: Exception):
            """Handle report generation error."""
            loading.destroy()
            logger.error(f"Report generation failed: {e}")
            messagebox.showerror("Report Failed", f"Failed to generate report: {e}")
        
        run_in_background(
            target=do_generate,
            on_complete=on_complete,
            on_error=on_error,
            master=self.master
        )
    
    def _open_user_management(self):
        """Open User Management window (Admin only)."""
        if not self.is_admin:
            messagebox.showerror("Access Denied", "User Management is restricted to Administrators.")
            return
        
        self.audit_repo.log("ACCESS", "user_management", "", "Opened User Management panel", self.user.username)
        UserManagementWindow(self.master, self.user, self.audit_repo)
    
    def _open_sales_window(self, product: Optional[Product] = None):
        """Open Sales/POS window (Manager/Admin only)."""
        if not self.can_modify:
            messagebox.showerror("Access Denied", "Sales recording requires Manager or Admin role.")
            return
        
        self.audit_repo.log("ACCESS", "sales_pos", "", "Opened POS Terminal", self.user.username)
        SalesWindow(
            self.master, 
            self.user, 
            product=product,
            on_sale_complete=self._refresh_data
        )
    
    def _handle_logout(self):
        """Handle user logout"""
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to sign out?"):
            self.audit_repo.log("LOGOUT", "user", self.user.username, "User signed out", self.user.username)
            logger.info(f"User '{self.user.username}' logged out")
            self.on_logout()

# ==============================================================================
# APPLICATION CONTROLLER
# ==============================================================================

class Application(tk.Tk):
    """
    Main Application Controller.
    
    Orchestrates the application lifecycle including:
    - Hardware-adaptive window sizing (80% of screen, clamped to bounds)
    - View management (login → dashboard transitions)
    - User session state
    - Database initialization
    
    The application follows MVC architecture with:
    - Model: Repository classes (ProductRepository, UserRepository, etc.)
    - View: UI classes (LoginView, DashboardView, etc.)
    - Controller: This Application class
    
    Attributes:
        current_view: Currently displayed view frame
        current_user: Authenticated User object or None
    """
    
    def __init__(self):
        super().__init__()
        
        self.title(f"{Config.APP_NAME} v{Config.APP_VERSION}")
        
        # Dynamic hardware-adaptive window sizing
        # Calculate dimensions as 80% of the screen to prevent UI overlap
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Target 80% of screen dimensions, with sensible min/max bounds
        target_width = int(screen_width * 0.80)
        target_height = int(screen_height * 0.80)
        
        # Clamp to reasonable bounds (min 1200x700, max 1920x1080)
        window_width = max(1200, min(target_width, 1920))
        window_height = max(700, min(target_height, 1080))
        
        self.geometry(f"{window_width}x{window_height}")
        self.minsize(1100, 650)  # Minimum usable size for compact displays
        self.configure(bg=Config.THEME["bg_primary"])
        
        # Center window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Set icon if available
        try:
            if sys.platform == "win32":
                self.iconbitmap(default="assets/icon.ico")
        except (tk.TclError, FileNotFoundError):
            pass  # Icon not found - continue without it
        
        self.current_view: Optional[tk.Frame] = None
        self.current_user: Optional[User] = None
        
        # Initialize database
        DatabaseManager()
        
        # Show login
        self._show_login()
        
        logger.info("Application started")
    
    def _show_login(self) -> None:
        """Display the login view, destroying any existing view."""
        if self.current_view:
            self.current_view.destroy()
        
        self.current_view = LoginView(self, self._on_login_success)
        self.current_view.pack(fill="both", expand=True)
    
    def _on_login_success(self, user: User) -> None:
        """
        Handle successful authentication.
        
        Args:
            user: Authenticated User object from LoginView
        """
        self.current_user = user
        self._show_dashboard()
    
    def _show_dashboard(self) -> None:
        """Display the main dashboard view for the authenticated user."""
        if self.current_view:
            self.current_view.destroy()
        
        self.current_view = DashboardView(self, self.current_user, self._on_logout)
        self.current_view.pack(fill="both", expand=True)
    
    def _on_logout(self) -> None:
        """Handle user logout by clearing session and returning to login."""
        self.current_user = None
        self._show_login()


# ==============================================================================
# ENTRY POINT
# ==============================================================================

def main() -> None:
    """
    Application entry point.
    
    Initializes the runtime environment:
    1. Enables DPI awareness for high-resolution displays
    2. Creates portable data directories (data/, assets/, logs/)
    3. Launches the main Application window
    
    Fatal errors are caught, logged, and displayed to the user.
    """
    try:
        # Enable DPI awareness for crisp UI on high-resolution displays
        setup_dpi_awareness()
        
        # Ensure portable data directories exist
        Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        Config.ASSETS_PATH.mkdir(parents=True, exist_ok=True)
        Config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        app = Application()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        messagebox.showerror("Fatal Error", f"Application failed to start:\n{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
