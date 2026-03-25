import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from qfluentwidgets import NavigationItemPosition, MSFluentWindow

from .views.task_center import TaskCenterInterface
from .views.draft_view import DraftInterface
from .views.exam_bag import ExamBagInterface
from .views.zen_mode import ZenModeInterface
import os


class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()
        from src.core.ai_brain import AIBrain

        self.ai_brain = AIBrain()

        self.taskInterface = TaskCenterInterface(self)
        self.draftInterface = DraftInterface(self)
        self.examBagInterface = ExamBagInterface(self)
        self.zenInterface = ZenModeInterface(self)

        self.initNavigation()
        self.initWindow()

    def get_icon(self, name):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return QIcon(os.path.join(base_dir, "assets", "icons", name))

    def initNavigation(self):
        self.addSubInterface(
            self.taskInterface, self.get_icon("task.png"), "任务中心 (Tasks)"
        )
        self.addSubInterface(
            self.draftInterface, self.get_icon("draft.png"), "暂存区 (Drafts/Review)"
        )
        self.addSubInterface(
            self.examBagInterface, self.get_icon("bag.png"), "试卷袋 (Exam Bag)"
        )
        self.addSubInterface(
            self.zenInterface,
            self.get_icon("zen.png"),
            "专注模式 (Zen Mode)",
            NavigationItemPosition.BOTTOM,
        )

    def initWindow(self):
        self.resize(1000, 700)
        self.setWindowTitle("SmartQB-QT Ultimate Edition")
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)


def run_app() -> int:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    try:
        return app.exec()
    finally:
        pass


if __name__ == "__main__":
    raise SystemExit(run_app())
