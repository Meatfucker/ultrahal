import sys
import asyncio
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget
from qasync import QEventLoop, asyncSlot
from modules.avernus_client import AvernusClient
from modules.console import Console
from modules.flux_gen import Flux
from modules.llm_chat import LlmChat
from modules.sdxl_gen import Sdxl


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UltraHal")
        self.resize(1020, 800)
        self.avernus_url = "localhost"
        self.avernus_client = AvernusClient(self.avernus_url)

        self.avernus_label = QLabel("Avernus URL:")
        self.avernus_entry = QLineEdit(text="localhost")
        self.avernus_entry.returnPressed.connect(self.update_avernus_url)
        self.avernus_current_server = QLabel(f"Current Server: {self.avernus_url}")
        self.avernus_button = QPushButton("Update URL")
        self.avernus_button.clicked.connect(self.update_avernus_url)
        self.update_avernus_url()
        self.tabs = QTabWidget()
        self.console_tab = Console()
        self.llm_chat_tab = LlmChat(self.avernus_client)
        self.sdxl_tab = Sdxl(self.avernus_client)
        self.flux_tab = Flux(self.avernus_client)

        self.avernus_layout = QHBoxLayout()
        self.avernus_layout.addWidget(self.avernus_label)
        self.avernus_layout.addWidget(self.avernus_entry)
        self.avernus_layout.addWidget(self.avernus_current_server)
        self.avernus_layout.addWidget(self.avernus_button)
        self.tabs.addTab(self.console_tab, "Console")
        self.tabs.addTab(self.llm_chat_tab, "LLM Chat")
        self.tabs.addTab(self.sdxl_tab, "SDXL Gen")
        self.tabs.addTab(self.flux_tab, "Flux Gen")
        self.layout = QVBoxLayout()
        self.layout.addLayout(self.avernus_layout)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    @asyncSlot()
    async def update_avernus_url(self):
        self.avernus_url = self.avernus_entry.text()
        self.avernus_client = AvernusClient(self.avernus_url)
        self.avernus_current_server.setText(f"Current Server: {self.avernus_url}")
        self.llm_chat_tab.avernus_client = self.avernus_client
        self.sdxl_tab.avernus_client = self.avernus_client
        self.flux_tab.avernus_client = self.avernus_client
        print(f"Avernus URL Updated: {self.avernus_url}")
        status = await self.avernus_client.check_status()
        print(status)
        await self.sdxl_tab.make_lora_list()
        await self.sdxl_tab.make_controlnet_list()
        await self.flux_tab.make_lora_list()

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    icon = QIcon("assets/icon.png")
    app.setStyle('Fusion')
    app.setWindowIcon(icon)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()
