import sys
import tempfile
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

# Ensure project root is on sys.path when running from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # noqa: E402

from main import (  # noqa: E402
    BackgroundTask,
    Config,
    DashboardView,
    DatabaseManager,
    User,
    UserRole,
)


def main():
    tmpdir = tempfile.mkdtemp()
    Config.DB_PATH = Path(tmpdir) / "smoke.db"
    DatabaseManager._instance = None

    # Initialize DB and dashboard
    root = tk.Tk()
    root.withdraw()

    DatabaseManager()  # Initialize database

    admin = User(
        username="admin", password_hash="", role=UserRole.ADMIN, full_name="Admin"
    )
    dashboard = DashboardView(root, admin, on_logout=lambda: None)

    # Monkeypatch filedialog to return temp file paths
    export_path = Path(tmpdir) / "export.csv"
    report_path = Path(tmpdir) / "report.txt"

    filedialog_asksave = filedialog.asksaveasfilename

    def _wait_for_file(path: Path, timeout: int = 5) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                root.update()
            except Exception:
                pass
            if path.exists():
                return True
            time.sleep(0.1)
        return False

    try:
        filedialog.asksaveasfilename = lambda **kw: str(export_path)
        dashboard._export_csv()
        # Wait for background tasks to finish and allow Tk callbacks to run
        BackgroundTask.wait_all(timeout=5)
        assert _wait_for_file(
            export_path, timeout=5
        ), f"Export file not created: {export_path}"

        filedialog.asksaveasfilename = lambda **kw: str(report_path)
        dashboard._generate_report()
        BackgroundTask.wait_all(timeout=5)
        assert _wait_for_file(
            report_path, timeout=5
        ), f"Report file not created: {report_path}"

        print("SMOKE CHECKS PASSED: export and report created:")
        print(str(export_path))
        print(str(report_path))

    finally:
        filedialog.asksaveasfilename = filedialog_asksave
        try:
            dashboard.destroy()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
