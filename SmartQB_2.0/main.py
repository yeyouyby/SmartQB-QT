from pathlib import Path
import logging
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def get_script_root() -> Path:
    """
    Returns the project root directory.
    """
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

    # Configure global fluent theme (Win 11 style)
    setTheme(Theme.AUTO)
    setThemeColor("#005fb8")  # TODO: Move to a constants/config file

    # Initialize the router to determine which window to show
    script_root = get_script_root()
    router = BootRouter(script_root)
    try:
        router.boot()
    except Exception as e:
        logging.error(f"Main app failed to boot: {e}")
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(
            None, "Startup Error", f"Could not initialize application:\n{e}"
        )
        sys.exit(1)

    logging.info("Main app booted successfully and instantiated the router.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
