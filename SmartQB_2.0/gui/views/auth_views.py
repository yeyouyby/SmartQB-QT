from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import FluentWindow, TitleLabel, PrimaryPushButton

class OOBE_WizardWindow(FluentWindow):
    """
    Placeholder Out-Of-Box Experience (OOBE) window for initial setup.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SmartQB - Initialization")
        self.resize(800, 600)

        # Create a simple central widget
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignCenter)

        # Add UI components
        self.title_label = TitleLabel("Welcome to SmartQB - Initial Setup", self.central_widget)
        self.title_label.setAlignment(Qt.AlignCenter)

        self.confirm_button = PrimaryPushButton("Start Configuration", self.central_widget)
        self.confirm_button.setFixedWidth(200)

        self.layout.addWidget(self.title_label)
        self.layout.addSpacing(30)
        self.layout.addWidget(self.confirm_button, alignment=Qt.AlignCenter)

        # Set object name for proper styling/routing
        self.central_widget.setObjectName("SetupWidget")

        # Use addSubInterface to properly integrate with FluentWindow even if it's just one view
        self.addSubInterface(self.central_widget, None, "Setup")

        # Hide navigation pane since it's just a wizard
        self.navigationInterface.hide()

class LoginWindow(FluentWindow):
    """
    Placeholder Login window.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SmartQB - Login")
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignCenter)

        self.title_label = TitleLabel("System Login", self.central_widget)
        self.title_label.setAlignment(Qt.AlignCenter)

        self.login_button = PrimaryPushButton("Login", self.central_widget)
        self.login_button.setFixedWidth(200)

        self.layout.addWidget(self.title_label)
        self.layout.addSpacing(30)
        self.layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        # Set object name for proper styling/routing
        self.central_widget.setObjectName("LoginWidget")

        self.addSubInterface(self.central_widget, None, "Login")
        self.navigationInterface.hide()
