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
        Helper function to reliably get the application data root path.
        Works for both script execution and PyInstaller packaged exe.
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
            return Path(app_data_path_str)

        # Running as script: use local data folder
        return self.script_root / "SmartQB_Data"

    def boot(self):
        """
        Evaluates conditions and boots the appropriate window.
        """
        # Delay import until QApplication exists
        from gui.views.auth_views import OOBE_WizardWindow, LoginWindow

        base_path = self.get_base_path()

        db_path = base_path / "sys_master.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if master database exists
        if db_path.is_file():
            # DB exists, show Login
            self.current_window = LoginWindow(db_path=db_path)
        else:
            # DB does not exist, show Out-of-Box Experience (OOBE) setup
            self.current_window = OOBE_WizardWindow(db_path=db_path)

        self.current_window.show()
