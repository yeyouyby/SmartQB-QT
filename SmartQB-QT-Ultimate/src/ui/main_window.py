from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QSize
from qfluentwidgets import (NavigationInterface, NavigationItemPosition, NavigationWidget,
                            MessageBox, isDarkTheme, setTheme, Theme, qrouter,
                            FluentWindow, MSFluentWindow)

from .views.task_center import TaskCenterInterface
from .views.draft_view import DraftInterface
from .views.exam_bag import ExamBagInterface
from .views.zen_mode import ZenModeInterface

class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()

        # --- Create interfaces ---
        self.taskInterface = TaskCenterInterface(self)
        self.draftInterface = DraftInterface(self)
        self.examBagInterface = ExamBagInterface(self)
        self.zenInterface = ZenModeInterface(self)

        self.initNavigation()
        self.initWindow()

    def initNavigation(self):
        self.addSubInterface(self.taskInterface, QIcon('src/assets/icons/task.png'), '任务中心 (Tasks)')
        self.addSubInterface(self.draftInterface, QIcon('src/assets/icons/draft.png'), '暂存区 (Drafts/Review)')
        self.addSubInterface(self.examBagInterface, QIcon('src/assets/icons/bag.png'), '试卷袋 (Exam Bag)')
        self.addSubInterface(self.zenInterface, QIcon('src/assets/icons/zen.png'), '专注模式 (Zen Mode)', NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(1000, 700)
        self.setWindowTitle('SmartQB-QT Ultimate Edition')
        # Center the window
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

if __name__ == '__main__':
    import sys
    # setTheme(Theme.DARK)
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()

# Import MCP Server start function
from src.core.mcp_server import start_mcp_server_bg

class UltimateApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        # Start MCP Server in Background thread as soon as app starts
        self.mcp_thread = start_mcp_server_bg()

# Modify main block to use UltimateApp
if __name__ == '__main__':
    import sys
    # setTheme(Theme.DARK)
    app = UltimateApp(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()
