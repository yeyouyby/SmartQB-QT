from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer, QTime
from PySide6.QtGui import QFont
from qfluentwidgets import (
    PrimaryPushButton,
    TitleLabel,
    BodyLabel,
    TextEdit,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF


class ZenModeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ZenModeInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)

        # Zen Mode is fully dark
        self.setStyleSheet("background-color: #121212; color: #E0E0E0;")

        # Header Toolbar
        self.header = QHBoxLayout()
        self.exitBtn = TransparentToolButton(FIF.CLOSE, self)
        self.exitBtn.clicked.connect(self.exit_zen_mode)
        self.header.addWidget(self.exitBtn, alignment=Qt.AlignLeft)

        self.timerLabel = TitleLabel("00:00", self)
        font = QFont("Consolas", 24, QFont.Bold)
        self.timerLabel.setFont(font)
        self.timerLabel.setAlignment(Qt.AlignCenter)
        self.timerLabel.setStyleSheet("color: #4CAF50;")
        self.header.addWidget(self.timerLabel, alignment=Qt.AlignCenter)
        self.header.addStretch(1)
        self.layout.addLayout(self.header)

        # Question Content
        self.questionContent = BodyLabel(
            "请认真审题，不要被外界干扰。\n\n已知有一质量为 m 的滑块在倾角为 θ 的斜面上匀速下滑...\n\n求：动摩擦因数 μ = ?",
            self,
        )
        self.questionContent.setWordWrap(True)
        self.questionContent.setStyleSheet("font-size: 20px; line-height: 1.6;")
        self.layout.addWidget(
            self.questionContent, stretch=2, alignment=Qt.AlignTop | Qt.AlignHCenter
        )

        # Drafting Area
        self.draftArea = TextEdit(self)
        self.draftArea.setPlaceholderText("在这里写草稿或代码解答...")
        self.draftArea.setStyleSheet(
            "background-color: #1E1E1E; border: 1px solid #333; color: white; font-family: Consolas;"
        )
        self.layout.addWidget(self.draftArea, stretch=1)

        # Timer Setup
        self.timeElapsed = QTime(0, 0, 0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

    def showEvent(self, event):
        super().showEvent(event)
        self.timeElapsed = QTime(0, 0, 0)
        self.timerLabel.setText("00:00")
        self.timer.start(1000)
        main_win = self.window()
        if main_win:
            if hasattr(main_win, "navigationInterface"):
                self._prev_nav_state = not main_win.navigationInterface.isHidden()
                main_win.navigationInterface.setHidden(True)
            main_win.showFullScreen()

    def update_timer(self):
        self.timeElapsed = self.timeElapsed.addSecs(1)
        self.timerLabel.setText(self.timeElapsed.toString("mm:ss"))

    def exit_zen_mode(self):
        self.timer.stop()
        main_win = self.window()
        if main_win:
            if (
                hasattr(self, "_prev_nav_state")
                and self._prev_nav_state
                and hasattr(main_win, "navigationInterface")
            ):
                main_win.navigationInterface.setHidden(False)
            main_win.showNormal()
