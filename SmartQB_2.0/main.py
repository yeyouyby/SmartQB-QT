import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Must import PySide6-Fluent-Widgets AFTER QApplication creation
    from qfluentwidgets import setTheme, Theme, setThemeColor
    from core.auth_router import BootRouter

    # Configure global fluent theme (Win 11 style)
    setTheme(Theme.AUTO)
    setThemeColor("#005fb8")  # SmartQB default primary color

    # Initialize the router to determine which window to show
    router = BootRouter()
    router.boot()

    print("Main app booted successfully and instantiated the router.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
