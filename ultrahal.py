from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget
import sys

from modules.client import AvernusClient
from modules.llm_chat import LlmChat
from modules.sdxl_gen import SdxlGen
from modules.flux_gen import FluxGen


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.avernus_client = AvernusClient("localhost")
        layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tab1 = LlmChat(self.avernus_client)
        self.tab2 = SdxlGen(self.avernus_client)
        self.tab3 = FluxGen(self.avernus_client)

        self.tabs.addTab(self.tab1, "LLM Chat")
        self.tabs.addTab(self.tab2, "SDXL Gen")
        self.tabs.addTab(self.tab3, "Flux Gen")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setWindowTitle("UltraHal")
        self.resize(1020, 800)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
