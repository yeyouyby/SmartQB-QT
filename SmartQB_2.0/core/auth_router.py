import sys
from pathlib import Path


class BootRouter:
    """
    State Machine router that determines the initial boot sequence.
    """

    def __init__(self):
        self.current_window = None

    def get_base_path(self) -> Path:
        """
        Helper function to reliably get the project root path.
        Works for both script execution and PyInstaller packaged exe.
        """
        if hasattr(sys, "_MEIPASS"):
            # Running as bundled executable, use executable directory for persistent DB
            base_dir = Path(sys.executable).parent
        else:
            # Running as script
            # Go up three levels from core/auth_router.py to reach project root (where SmartQB_Data is)
            base_dir = Path(__file__).resolve().parent.parent.parent

        return base_dir

    def boot(self):
        """
        Evaluates conditions and boots the appropriate window.
        """
        # Delay import until QApplication exists
        from gui.views.auth_views import OOBE_WizardWindow, LoginWindow

        base_path = self.get_base_path()
        db_path = base_path / "SmartQB_Data" / "sys_master.db"

        # Check if master database exists
        if db_path.exists():
            # DB exists, show Login
            self.current_window = LoginWindow()
        else:
            # DB does not exist, show Out-of-Box Experience (OOBE) setup
            self.current_window = OOBE_WizardWindow()

        self.current_window.show()
