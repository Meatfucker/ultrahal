import sys
import asyncio
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QTabWidget, QPushButton, QLabel, QLineEdit
from qasync import QEventLoop

from modules.client import AvernusClient
from modules.llm_chat import LlmChat
from modules.sdxl_gen import SdxlGen
from modules.flux_gen import FluxGen


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.avernus_url = "localhost"
        self.avernus_client = AvernusClient(self.avernus_url)
        layout = QVBoxLayout()

        self.avernus_layout = QHBoxLayout()
        self.avernus_label = QLabel("Avernus URL:")
        self.avernus_entry = QLineEdit()
        self.avernus_entry.returnPressed.connect(self.update_avernus_url)
        self.avernus_current_server = QLabel(f"Current Server: {self.avernus_url}")
        self.avernus_button = QPushButton("Update URL")
        self.avernus_button.clicked.connect(self.update_avernus_url)
        self.avernus_layout.addWidget(self.avernus_label)
        self.avernus_layout.addWidget(self.avernus_entry)
        self.avernus_layout.addWidget(self.avernus_current_server)
        self.avernus_layout.addWidget(self.avernus_button)

        self.tabs = QTabWidget()
        self.tab1 = LlmChat(self.avernus_client)
        self.tab2 = SdxlGen(self.avernus_client)
        self.tab3 = FluxGen(self.avernus_client)

        self.tabs.addTab(self.tab1, "LLM Chat")
        self.tabs.addTab(self.tab2, "SDXL Gen")
        self.tabs.addTab(self.tab3, "Flux Gen")

        layout.addLayout(self.avernus_layout)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setWindowTitle("UltraHal")
        self.resize(1020, 800)

    def update_avernus_url(self):
        self.avernus_url = self.avernus_entry.text()
        self.avernus_client = AvernusClient(self.avernus_url)
        self.avernus_current_server.setText(f"Current Server: {self.avernus_url}")
        self.tab1.avernus_client = self.avernus_client
        self.tab2.avernus_client = self.avernus_client
        self.tab3.avernus_client = self.avernus_client


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()
