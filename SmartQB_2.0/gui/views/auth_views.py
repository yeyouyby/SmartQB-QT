from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import TitleLabel, PrimaryPushButton
from qframelesswindow import FramelessWindow


class AuthBaseWindow(FramelessWindow):
    """
    Common base class for authentication/setup windows to share boilerplate.
    """

    def __init__(
        self,
        title: str,
        object_name: str,
        parent=None,
        window_title: Optional[str] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(window_title if window_title is not None else title)
        self.resize(800, 600)

        # Create central container
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName(object_name)

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
        # Set up FramelessWindow layout
        self.window_layout = QVBoxLayout(self)
        # Assuming we have a title bar, we need to make sure layout accounts for it or we just add our widget.
        self.window_layout.addWidget(self.central_widget)


class OOBE_WizardWindow(AuthBaseWindow):
    """
    Placeholder Out-Of-Box Experience (OOBE) window for initial setup.
    """

    def __init__(self, parent=None):
        super().__init__(
            title="Welcome to SmartQB - Initial Setup",
            object_name="SetupWidget",
            parent=parent,
            window_title="SmartQB - Initialization",
        )
        self.action_button.setText("Start Configuration")


class LoginWindow(AuthBaseWindow):
    """
    Placeholder Login window.
    """

    def __init__(self, parent=None):
        super().__init__(
            title="System Login",
            object_name="LoginWidget",
            parent=parent,
            window_title="SmartQB - Login",
        )
        self.action_button.setText("Login")
