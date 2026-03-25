from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    PrimaryPushButton,
    TitleLabel,
    CardWidget,
    BodyLabel,
    FlowLayout,
    SearchLineEdit,
)


class ExamBagInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ExamBagInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Header
        self.titleLabel = TitleLabel("试卷袋 (Exam Bag)", self)
        self.layout.addWidget(self.titleLabel)

        # Toolbar
        self.toolbar = QHBoxLayout()
        self.searchBox = SearchLineEdit(self)
        self.searchBox.setPlaceholderText("Hybrid Search (Dense + BM25)...")
        self.searchBox.setFixedWidth(300)
        self.toolbar.addWidget(self.searchBox)

        self.saBtn = PrimaryPushButton("🔥 智能组卷 (Simulated Annealing)", self)
        self.exportBtn = PrimaryPushButton("📄 套用母版导出 (Export Word)", self)
        self.saBtn.clicked.connect(self.on_saBtn_clicked)
        self.exportBtn.clicked.connect(self.on_exportBtn_clicked)
        self.toolbar.addWidget(self.saBtn)
        self.toolbar.addWidget(self.exportBtn)
        self.toolbar.addStretch(1)
        self.layout.addLayout(self.toolbar)

        # Waterfall Flow layout for Question Cards
        self.flowLayoutWidget = QWidget()
        self.flowLayout = FlowLayout(self.flowLayoutWidget)

        # Add mock cards
        for i in range(5):
            card = CardWidget(self)
            card.setFixedSize(250, 150)
            cardLayout = QVBoxLayout(card)
            cardLayout.addWidget(
                BodyLabel(
                    f"Mock Question #{100 + i}\nTopic: Mechanics\nTags: #Force #Acceleration",
                    card,
                )
            )
            self.flowLayout.addWidget(card)

        self.layout.addWidget(self.flowLayoutWidget)

    def on_saBtn_clicked(self):
        # TODO: Implement full Simulated Annealing UI popup logic
        import logging

        logging.info("SA Generation triggered. UI placeholder.")

    def on_exportBtn_clicked(self):
        # TODO: Implement Word Export dialog UI
        import logging

        logging.info("Export pipeline triggered. UI placeholder.")
