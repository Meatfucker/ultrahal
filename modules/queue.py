from PySide6.QtWidgets import QHBoxLayout, QWidget
from modules.ui_widgets import Console, QueueViewer


class QueueTab(QWidget):
    def __init__(self, avernus_client, ultrahal):
        super().__init__()
        self.avernus_client = avernus_client
        self.ultrahal = ultrahal
        self.console = Console()
        self.queue_view = QueueViewer()
        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.console)
        self.main_layout.addWidget(self.queue_view)
        self.setLayout(self.main_layout)
