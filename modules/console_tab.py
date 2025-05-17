from PySide6.QtWidgets import QHBoxLayout, QWidget
from modules.ui_widgets import Console


class QueueTab(QWidget):
    def __init__(self, avernus_client):
        super().__init__()
        self.avernus_client = avernus_client

        self.console = Console()
        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.console)
        self.setLayout(self.main_layout)
