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

    def get_base_path(self) -> Path:
        """
        Helper function to reliably get the project root path.
        Works for both script execution and PyInstaller packaged exe.
        """
        if hasattr(sys, "_MEIPASS"):
            # Running as bundled executable, use standard user data directory for persistent DB to avoid permission errors
            app_data_path_str = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            if not app_data_path_str:
                raise RuntimeError(
                    "Could not determine writable application data location."
                )
            base_dir = Path(app_data_path_str)
        else:
            # Running as script
            base_dir = self.script_root

        return base_dir

    def boot(self):
        """
        Evaluates conditions and boots the appropriate window.
        """
        # Delay import until QApplication exists
        from gui.views.auth_views import OOBE_WizardWindow, LoginWindow

        base_path = self.get_base_path()
        db_dir = base_path / "SmartQB_Data"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "sys_master.db"

        # Check if master database exists
        if db_path.exists():
            # DB exists, show Login
            self.current_window = LoginWindow()
        else:
            # DB does not exist, show Out-of-Box Experience (OOBE) setup
            self.current_window = OOBE_WizardWindow()

        self.current_window.show()
