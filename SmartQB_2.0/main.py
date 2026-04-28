import qasync
import asyncio
from pathlib import Path
import logging
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox


def get_script_root() -> Path:
    """
    Returns the project root directory.
    Handles running from source and from a PyInstaller bundle.
    """
    if getattr(sys, "frozen", False):
        # The application is frozen
        return Path(sys.executable).parent
    else:
        # The application is not frozen
        return Path(__file__).resolve().parent.parent


def main():
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SmartQB")
    app.setOrganizationName("SmartQB")

    # Must import PySide6-Fluent-Widgets AFTER QApplication creation
    from qfluentwidgets import setTheme, Theme, setThemeColor
    from core.auth_router import BootRouter
    from resources.config.constants import THEME_COLOR_PRIMARY

    # Configure global fluent theme (Win 11 style)
    setTheme(Theme.AUTO)
    setThemeColor(THEME_COLOR_PRIMARY)

    # Initialize the router to determine which window to show
    script_root = get_script_root()
    router = BootRouter(script_root)
    try:
        router.boot()
    except Exception as e:
        logging.exception("Main app failed to boot")
        QMessageBox.critical(
            None, "Startup Error", f"Could not initialize application:\n{e}"
        )
        sys.exit(1)

    logging.info("Main app booted successfully and instantiated the router.")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        sys.exit(loop.run_forever())


if __name__ == "__main__":
    main()
