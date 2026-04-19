from PySide6.QtCore import (
    QEvent,
    Qt,
    QTimer,
    Signal,
    Slot,
    QObject,
    QRunnable,
    QThreadPool,
)
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QLabel,
    QApplication,
)
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
from resources.config.constants import MAX_PREVIEW_PAGES
import json
import logging
import bleach  # type: ignore
from markdown_it import MarkdownIt


class PDFRenderSignals(QObject):
    image_rendered = Signal(QImage)
    render_finished = Signal()


class PDFRenderWorker(QRunnable):
    """
    Background worker to render PyMuPDF pages without blocking the GUI thread.
    """

    def __init__(self, pdf_path: str):
        super().__init__()
        self.pdf_path = pdf_path
        self.signals = PDFRenderSignals()

    @Slot()
    def run(self):
        try:
            with fitz.open(self.pdf_path) as doc:
                for page_num in range(min(MAX_PREVIEW_PAGES, doc.page_count)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))

                    qt_image = QImage(
                        pix.samples,
                        pix.width,
                        pix.height,
                        pix.stride,
                        QImage.Format.Format_RGB888,
                    ).copy()
                    self.signals.image_rendered.emit(qt_image)
        except Exception as e:
            logging.error(f"Error opening PDF: {e}")
        finally:
            self.signals.render_finished.emit()


class WebEnginePool(QObject):
    """
    Global pool for QWebEngineView to prevent Chromium process creation/destruction overhead.
    Maintains a small pool of shared instances to support multi-block concurrent editing.
    """

    _pool: list[QWebEngineView] = []
    reclaim_view = Signal(QWebEngineView)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    MAX_INSTANCES = 3

    @classmethod
    def get_view(cls, parent=None) -> QWebEngineView:
        # Try to find an unused view (parent is None or not a widget in layout)
        for view in cls._pool:
            if view.parent() is None:
                view.setParent(parent)
                return view

        # If pool isn't full, create a new one
        if len(cls._pool) < cls.MAX_INSTANCES:
            new_view = QWebEngineView()
            new_view.setHtml("")
            new_view.setParent(parent)
            cls._pool.append(new_view)
            return new_view

        # Hard limit reached: Implement simple LRU by stealing the oldest active view
        oldest_view = cls._pool.pop(0)
        # Emit via the global pool object instead of hacking into the parent
        cls.instance().reclaim_view.emit(oldest_view)

        oldest_view.setHtml("")
        oldest_view.setParent(parent)
        cls._pool.append(oldest_view)  # Move to end (most recently used)
        return oldest_view


class EventBus(QObject):
    """Global Event Bus for cross-panel communication."""

    question_focused = Signal(int)  # int represents block ID
    reclaim_view = Signal(QWebEngineView)

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


class QuestionBlockCard(ElevatedCardWidget):
    _md_instance = MarkdownIt()
    _ALLOWED_HTML_TAGS = bleach.sanitizer.ALLOWED_TAGS | {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "br",
        "strong",
        "em",
        "code",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
    }
    _ALLOWED_HTML_ATTRS = {
        "h1": ["id", "class"],
        "h2": ["id", "class"],
        "h3": ["id", "class"],
        "h4": ["id", "class"],
        "h5": ["id", "class"],
        "h6": ["id", "class"],
        "p": ["class"],
        "div": ["class", "id"],
        "span": ["class"],
        "code": ["class"],
        "pre": ["class"],
        "a": ["href", "title", "class"],
        "img": ["src", "alt", "title", "class"],
    }
    """
    Flyweight Middle Panel Block.
    Switches between a light QLabel and heavy QWebEngineView dynamically.
    """

    def __init__(self, block_id: int, bus: EventBus, parent=None):
        super().__init__(parent)
        self.block_id = block_id
        self.bus = bus
        self.markdown_text = ""
        self.card_layout = QVBoxLayout(self)

        # State 1: Lightweight Preview Label
        self.preview_label = QLabel("Click to Edit Markdown")
        self.preview_label.setWordWrap(True)
        self.preview_label.setTextFormat(Qt.TextFormat.PlainText)
        self.card_layout.addWidget(self.preview_label)

        # State 2 components (instantiated only when active)
        self.web_engine_view: QWebEngineView | None = None
        self.text_edit: TextEdit | None = None

        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self._sync_preview)

        WebEnginePool.instance().reclaim_view.connect(self._on_reclaim_view)

    def mouseDoubleClickEvent(self, event):
        """Switch to State 2 (Active Edit) and borrow Chromium Engine from the pool."""
        super().mouseDoubleClickEvent(event)
        if not self.web_engine_view:
            self.web_engine_view = WebEnginePool.get_view(self)
            self.text_edit = TextEdit(self)

            # Hide preview label
            self.preview_label.hide()

            # Replace UI with heavy widgets
            self.card_layout.addWidget(self.web_engine_view)
            self.web_engine_view.show()
            self.card_layout.addWidget(self.text_edit)

            # Initialize with the stored markdown text
            self.text_edit.setText(self.markdown_text)
            self._sync_preview()

            self.text_edit.textChanged.connect(self._on_text_changed)
            self.text_edit.setFocus()
            self.text_edit.installEventFilter(self)

            # Broadcast to EventBus that this block is active
            self.bus.question_focused.emit(self.block_id)

    def eventFilter(self, obj, event):

        if obj is self.text_edit and event.type() == QEvent.Type.FocusOut:
            focused_widget = QApplication.focusWidget()
            if (
                focused_widget is not None
                and focused_widget is not self
                and not self.isAncestorOf(focused_widget)
            ):
                self._revert_state()
        return super().eventFilter(obj, event)

    @Slot(QWebEngineView)
    def _on_reclaim_view(self, target_view: QWebEngineView):
        if self.web_engine_view is target_view:
            self._revert_state(force=True)

    def _revert_state(self, force=False):
        """Switch back to State 1 and release Chromium Engine resources back to the pool."""
        self.debounce_timer.stop()
        if self.web_engine_view:
            if self.text_edit:
                self.text_edit.deleteLater()
                self.text_edit = None
            if not force and self.isAncestorOf(QApplication.focusWidget()):
                return

            # Save content and update preview before destruction
            if self.text_edit:
                self.markdown_text = self.text_edit.toPlainText()
                self.preview_label.setText(
                    self.markdown_text
                    if self.markdown_text
                    else "Click to Edit Markdown"
                )

            # Revert UI state
            self.card_layout.removeWidget(self.web_engine_view)
            self.card_layout.removeWidget(self.text_edit)
            self.preview_label.show()

            # Return Heavy Chromium process to the void (unparent it) rather than destroying it
            if self.web_engine_view.parent() is self:
                self.web_engine_view.hide()
                self.web_engine_view.setParent(None)
            self.web_engine_view = None

            self.text_edit.deleteLater()
            self.text_edit = None

    @Slot()
    def _on_text_changed(self):
        """Start the 300ms debounce timer to prevent Chromium blinking."""
        self.debounce_timer.start()

    @Slot()
    def _sync_preview(self):
        """Synchronize Markdown -> HTML DOM without reloading entire page."""
        if self.web_engine_view and self.text_edit:
            # Using runJavaScript to patch HTML inline (assuming template loaded)

            raw_html = self._md_instance.render(self.text_edit.toPlainText())
            clean_html = bleach.clean(
                raw_html,
                tags=self._ALLOWED_HTML_TAGS,
                attributes=self._ALLOWED_HTML_ATTRS,
                strip=True,
            )
            html_json = json.dumps(clean_html)
            js_patch = (
                f"if (document.body) {{ document.body.innerHTML = {html_json}; }}"
            )
            self.web_engine_view.page().runJavaScript(js_patch)


class CalibrationWorkspace(QWidget):
    """
    3-Panel Calibration Workspace
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
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

        self.main_layout.addWidget(self.splitter)

        # Mock Initial Blocks
        for i in range(5):
            self.mid_layout.addWidget(QuestionBlockCard(block_id=i, bus=self.bus))

    @Slot(int)
    def _update_right_panel(self, block_id: int):
        self.right_label.setText(f"Editing Block ID: {block_id}\n\nAI Logic Chain: ...")

    def render_pdf_lazy(self, pdf_path: str):
        """
        Spawns a background worker to render PDF pages.
        """
        worker = PDFRenderWorker(pdf_path)
        worker.signals.image_rendered.connect(self._on_pdf_image_rendered)
        # Assuming global QThreadPool
        QThreadPool.globalInstance().start(worker)

    @Slot(QImage)
    def _on_pdf_image_rendered(self, qt_image: QImage):
        label = QLabel()
        label.setPixmap(QPixmap.fromImage(qt_image))
        self.left_layout.addWidget(label)


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
