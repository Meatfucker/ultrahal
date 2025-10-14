from PySide6.QtWidgets import QHBoxLayout, QWidget

from modules.avernus_client import AvernusClient
from modules.ui_widgets import Console, QueueViewer


class QueueTab(QWidget):
    def __init__(self,
                 avernus_client: AvernusClient,
                 ultrahal: QWidget):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.ultrahal: QWidget = ultrahal
        self.console: Console = Console()
        self.queue_view: QueueViewer = QueueViewer()
        self.main_layout: QHBoxLayout = QHBoxLayout()
        self.main_layout.addLayout(self.console, stretch=1)
        self.main_layout.addWidget(self.queue_view, stretch=3)
        self.setLayout(self.main_layout)
