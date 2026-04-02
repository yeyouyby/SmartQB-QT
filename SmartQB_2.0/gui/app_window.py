from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter, QVBoxLayout, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QImage, QPixmap
from qfluentwidgets import (
    FluentWindow,
    SmoothScrollArea,
    TextEdit,
    ElevatedCardWidget,
)
from qfluentwidgets import FluentIcon as FIF
import fitz  # PyMuPDF
import gc


class EventBus(QObject):
    """Global Event Bus for cross-panel communication."""

    question_focused = Signal(int)  # int represents block ID


class QuestionBlockCard(ElevatedCardWidget):
    """
    Flyweight Middle Panel Block.
    Switches between a light QLabel and heavy QWebEngineView dynamically.
    """

    def __init__(self, block_id: int, bus: EventBus, parent=None):
        super().__init__(parent)
        self.block_id = block_id
        self.bus = bus
        self.layout = QVBoxLayout(self)

        # State 1: Lightweight Preview Label
        self.preview_label = QLabel("Click to Edit Markdown")
        self.layout.addWidget(self.preview_label)

        # State 2 components (instantiated only when active)
        self.web_engine_view: QWebEngineView | None = None
        self.text_edit: TextEdit | None = None

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self._sync_preview)

    def mouseDoubleClickEvent(self, event):
        """Switch to State 2 (Active Edit) and allocate Chromium Engine."""
        if not self.web_engine_view:
            self.web_engine_view = QWebEngineView(self)
            self.text_edit = TextEdit(self)

            # Hide preview label
            self.preview_label.hide()

            # Replace UI with heavy widgets
            self.layout.addWidget(self.web_engine_view)
            self.layout.addWidget(self.text_edit)

            self.text_edit.textChanged.connect(self._on_text_changed)
            self.text_edit.setFocus()

            # Broadcast to EventBus that this block is active
            self.bus.question_focused.emit(self.block_id)

    def focusOutEvent(self, event):
        """Switch back to State 1 and free Chromium Engine resources."""
        if self.web_engine_view:
            # Revert UI state
            self.layout.removeWidget(self.web_engine_view)
            self.layout.removeWidget(self.text_edit)
            self.preview_label.show()

            # Delete Heavy Chromium processes safely
            self.web_engine_view.deleteLater()
            self.text_edit.deleteLater()
            self.web_engine_view = None
            self.text_edit = None

            # Force GC
            gc.collect()

    @Slot()
    def _on_text_changed(self):
        """Start the 300ms debounce timer to prevent Chromium blinking."""
        self.debounce_timer.start()

    @Slot()
    def _sync_preview(self):
        """Synchronize Markdown -> HTML DOM without reloading entire page."""
        if self.web_engine_view and self.text_edit:
            # Using runJavaScript to patch HTML inline (assuming template loaded)
            html_content = self.text_edit.toPlainText().replace("'", "\\'")
            js_patch = f"document.body.innerHTML = '{html_content}';"
            self.web_engine_view.page().runJavaScript(js_patch)


class CalibrationWorkspace(QWidget):
    """
    3-Panel Calibration Workspace
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)

        self.bus = EventBus()

        # Panel A: Left (PyMuPDF)
        self.left_panel = SmoothScrollArea(self)
        self.left_content = QWidget()
        self.left_layout = QVBoxLayout(self.left_content)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_panel.setWidget(self.left_content)
        self.left_panel.setWidgetResizable(True)

        # Panel B: Middle (Flyweight Question Blocks)
        self.mid_panel = SmoothScrollArea(self)
        self.mid_content = QWidget()
        self.mid_layout = QVBoxLayout(self.mid_content)
        self.mid_panel.setWidget(self.mid_content)
        self.mid_panel.setWidgetResizable(True)

        # Panel C: Right (Metadata Inspector)
        self.right_panel = QWidget(self)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_label = QLabel("Metadata Inspector: Select a block")
        self.right_layout.addWidget(self.right_label)

        # Event Bus Subscription
        self.bus.question_focused.connect(self._update_right_panel)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)

        # Set ratios roughly: 3.5, 5, 1.5
        self.splitter.setStretchFactor(0, 35)
        self.splitter.setStretchFactor(1, 50)
        self.splitter.setStretchFactor(2, 15)

        self.layout.addWidget(self.splitter)

        # Mock Initial Blocks
        for i in range(5):
            self.mid_layout.addWidget(QuestionBlockCard(block_id=i, bus=self.bus))

    @Slot(int)
    def _update_right_panel(self, block_id: int):
        self.right_label.setText(f"Editing Block ID: {block_id}\n\nAI Logic Chain: ...")

    def render_pdf_lazy(self, pdf_path: str):
        """
        Loads PDF with fitz.Matrix(2.0, 2.0).
        Actual Lazy Loading requires tracking scroll value, simplified here.
        """
        doc = fitz.open(pdf_path)
        for page_num in range(min(2, doc.page_count)):  # Render only first 2 for now
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))

            # Convert PyMuPDF Pixmap to QImage
            qt_image = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format.Format_RGB888,
            )
            label = QLabel()
            label.setPixmap(QPixmap.fromImage(qt_image))
            self.left_layout.addWidget(label)

        # Close document and invoke GC
        doc.close()
        gc.collect()


class AppWindow(FluentWindow):
    """
    Main Global Application Window.
    Provides Navigation (Mica Material).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create Interfaces
        self.workspace = CalibrationWorkspace(self)
        self.workspace.setObjectName("WorkspaceInterface")

        # Bind Interfaces to Navigation
        self.addSubInterface(self.workspace, FIF.DOCUMENT, "Calibration Workspace")

        self.resize(1280, 800)
        self.setWindowTitle("SmartQB 2.0 - Studio")
