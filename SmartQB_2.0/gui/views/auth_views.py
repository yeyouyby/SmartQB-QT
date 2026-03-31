from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import FluentWindow, TitleLabel, PrimaryPushButton


class AuthBaseWindow(FluentWindow):
    """
    Common base class for authentication/setup windows to share boilerplate.
    """

    def __init__(self, title: str, object_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)

        self.central_widget = QWidget(self)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = TitleLabel(title, self.central_widget)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.action_button = PrimaryPushButton("", self.central_widget)
        self.action_button.setFixedWidth(200)

        self.main_layout.addWidget(self.title_label)
        self.main_layout.addSpacing(30)
        self.main_layout.addWidget(
            self.action_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

        self.central_widget.setObjectName(object_name)
        self.addSubInterface(self.central_widget, None, title)
        self.navigationInterface.hide()


class OOBE_WizardWindow(AuthBaseWindow):
    """
    Placeholder Out-Of-Box Experience (OOBE) window for initial setup.
    """

    def __init__(self, parent=None):
        super().__init__(
            title="Welcome to SmartQB - Initial Setup",
            object_name="SetupWidget",
            parent=parent,
        )
        self.setWindowTitle("SmartQB - Initialization")
        self.action_button.setText("Start Configuration")


class LoginWindow(AuthBaseWindow):
    """
    Placeholder Login window.
    """

    def __init__(self, parent=None):
        super().__init__(title="System Login", object_name="LoginWidget", parent=parent)
        self.setWindowTitle("SmartQB - Login")
        self.action_button.setText("Login")
