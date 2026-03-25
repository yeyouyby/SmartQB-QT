from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QTimer
from qfluentwidgets import (
    PrimaryPushButton,
    TableWidget,
    CardWidget,
    TitleLabel,
    BodyLabel,
    IndeterminateProgressRing,
    InfoBar,
    InfoBarPosition,
)


class TaskCenterInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskCenterInterface")
        self.layout = QVBoxLayout(self)

        # Header
        self.titleLabel = TitleLabel("任务中心 (Task Center)", self)
        self.layout.addWidget(self.titleLabel)

        # Upload Button
        self.uploadBtn = PrimaryPushButton("导入图片/文档 (Upload)", self)
        self.uploadBtn.clicked.connect(self.simulate_upload)
        self.layout.addWidget(self.uploadBtn, alignment=Qt.AlignLeft)

        # Task Table setup
        self.taskTable = TableWidget(self)
        self.taskTable.setColumnCount(4)
        self.taskTable.setHorizontalHeaderLabels(
            ["Task ID", "File", "Status", "Progress"]
        )
        self.layout.addWidget(self.taskTable)

        self.layout.setContentsMargins(20, 20, 20, 20)

    def simulate_upload(self):
        row = self.taskTable.rowCount()
        self.taskTable.insertRow(row)
        self.taskTable.setItem(row, 0, QTableWidgetItem(f"Task-{row+1000}"))
        self.taskTable.setItem(row, 1, QTableWidgetItem(f"sample_test_{row}.png"))
        self.taskTable.setItem(row, 2, QTableWidgetItem("Processing..."))

        # Add Progress Ring (Simulating OCR background task)
        progressWidget = QWidget()
        progressLayout = QHBoxLayout(progressWidget)
        progressLayout.setContentsMargins(0, 0, 0, 0)
        ring = IndeterminateProgressRing(self)
        ring.setFixedSize(20, 20)
        ring.start()
        progressLayout.addWidget(ring)
        progressLayout.setAlignment(Qt.AlignCenter)
        self.taskTable.setCellWidget(row, 3, progressWidget)

        InfoBar.success(
            title="解析开始",
            content="后台 OCR 已启动，请稍候查看暂存区。",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=2000,
            parent=self,
        )
