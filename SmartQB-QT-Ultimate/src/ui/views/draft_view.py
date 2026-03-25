import pathlib
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl
from qfluentwidgets import (TextEdit, ToolButton, PrimaryPushButton,
                            ListWidget, ListWidgetItem, Flyout, FlyoutView, InfoBar)
import os
from src.core.ai_brain import AICorrectionWorker, AIBrain

class DraftInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DraftInterface")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)

        # Left: Task List (Pending drafts)
        self.taskList = ListWidget(self)
        self.taskList.setFixedWidth(200)
        self.layout.addWidget(self.taskList)

        self.splitter = QSplitter(Qt.Horizontal, self)

        # Center: Markdown Editor (Review raw text)
        self.editorLayoutWidget = QWidget()
        self.editorLayout = QVBoxLayout(self.editorLayoutWidget)
        self.editorLayout.setContentsMargins(0, 0, 0, 0)

        self.mdEditor = TextEdit(self.editorLayoutWidget)
        self.mdEditor.setPlaceholderText("Edit Markdown here...")
        self.editorLayout.addWidget(self.mdEditor)

        self.aiCorrectBtn = PrimaryPushButton("AI 纠错 (LiteLLM)", self.editorLayoutWidget)
        self.editorLayout.addWidget(self.aiCorrectBtn)
        self.aiCorrectBtn.clicked.connect(self.trigger_ai_correction)

        # Right: Rendered Cherry Markdown Preview (WYSIWYG)
        self.previewView = QWebEngineView(self)
        self.init_cherry_markdown()

        self.splitter.addWidget(self.editorLayoutWidget)
        self.splitter.addWidget(self.previewView)
        self.splitter.setSizes([300, 400])

        self.layout.addWidget(self.splitter)

        # Add mock drafts
        self.taskList.addItem(ListWidgetItem("Draft 1 - Math Form"))
        self.taskList.addItem(ListWidgetItem("Draft 2 - Physics Test"))

    def init_cherry_markdown(self):
        # Load internal editor UI directly from local assets ensuring no network drops
        editor_path = pathlib.Path(__file__).resolve().parent.parent.parent / "assets" / "editor" / "index.html"
        self.previewView.load(QUrl.fromLocalFile(str(editor_path)))

    def trigger_ai_correction(self):
        self.aiCorrectBtn.setDisabled(True)
        self.aiCorrectBtn.setText("纠错中... (Correcting...)")

        raw_text = self.mdEditor.toPlainText()
        brain_instance = getattr(self.window(), 'ai_brain', None) # Or instantiate if missing
        self.worker = AICorrectionWorker(raw_text, brain=brain_instance)
        self.worker.result_ready.connect(self.on_ai_success)
        self.worker.error.connect(self.on_ai_error)
        self.worker.start()

    def on_ai_success(self, corrected_text):
        self.mdEditor.setPlainText(corrected_text)
        self.aiCorrectBtn.setDisabled(False)
        self.aiCorrectBtn.setText("AI 纠错 (LiteLLM)")
        InfoBar.success(
            title="AI 纠错完成",
            content="文本已成功修复格式！",
            duration=2000,
            parent=self
        )

    def on_ai_error(self, err_msg):
        self.aiCorrectBtn.setDisabled(False)
        self.aiCorrectBtn.setText("AI 纠错 (LiteLLM)")
        InfoBar.error(
            title="AI 错误",
            content=str(err_msg),
            duration=3000,
            parent=self
        )
