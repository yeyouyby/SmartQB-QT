from PySide6.QtCore import QStandardPaths
import sys
from pathlib import Path

from gui.views.auth_views import OOBEWizardWindow, LoginWindow
from resources.config.constants import DATA_FOLDER_NAME, DB_NAME


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
        Works for both script execution, PyInstaller packaged exe, and installed packages.
        """
        is_frozen = getattr(sys, "frozen", False)
        # Check if we are running from the development repository
        is_dev_env = (self.script_root / ".git").exists() or (
            self.script_root / ".gitignore"
        ).exists()

        if is_frozen or not is_dev_env:
            # Use standard user data directory for persistent DB to avoid permission errors
            # in non-development or bundled environments
            app_data_path_str = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
            if not app_data_path_str:
                raise RuntimeError(
                    "Could not determine writable application data location."
                )
            return Path(app_data_path_str)

        # Running as script in development env: use local data folder
        return self.script_root / DATA_FOLDER_NAME

    def boot(self):
        """
        Evaluates conditions and boots the appropriate window.
        """

        base_path = self.get_base_path()

        db_path = base_path / DB_NAME
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if master database exists
        if db_path.is_file():
            # DB exists, show Login
            self.current_window = LoginWindow(db_path=db_path)
        else:
            # DB does not exist, show Out-of-Box Experience (OOBE) setup
            self.current_window = OOBEWizardWindow(db_path=db_path)

        self.current_window.show()
