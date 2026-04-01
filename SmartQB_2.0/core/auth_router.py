from typing import Tuple
from PySide6.QtCore import QStandardPaths
import sys
from pathlib import Path


class BootRouter:
    """
    State Machine router that determines the initial boot sequence.
    """

    def __init__(self, script_root: Path):
        self.current_window = None
        self.script_root = script_root

    def get_base_path(self) -> Tuple[Path, bool]:
        """
        Helper function to reliably get the project root path.
        Works for both script execution and PyInstaller packaged exe.
        Returns a tuple of (path, is_bundled).
        """
        if hasattr(sys, "_MEIPASS"):
            # Running as bundled executable
            app_data_path_str = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            if not app_data_path_str:
                raise RuntimeError(
                    "Could not determine writable application data location."
                )
            base_dir = Path(app_data_path_str)
            is_bundled = True
        else:
            # Running as script
            base_dir = self.script_root
            is_bundled = False

        return base_dir, is_bundled

    def boot(self):
        """
        Evaluates conditions and boots the appropriate window.
        """
        # Delay import until QApplication exists
        from gui.views.auth_views import OOBE_WizardWindow, LoginWindow

        base_path, is_bundled = self.get_base_path()

        # If bundled, AppDataLocation already includes the app name, so avoid redundant nesting.
        # If running as a script, use the SmartQB_Data folder at the project root.
        db_dir = base_path / "data" if is_bundled else base_path / "SmartQB_Data"
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise RuntimeError(f"Failed to create database directory: {e}")
        db_path = db_dir / "sys_master.db"

        # Check if master database exists
        if db_path.exists():
            # DB exists, show Login
            self.current_window = LoginWindow()
        else:
            # DB does not exist, show Out-of-Box Experience (OOBE) setup
            self.current_window = OOBE_WizardWindow()

        self.current_window.show()
