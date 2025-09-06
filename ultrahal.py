import sys
import asyncio

import qasync
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget
from qasync import QEventLoop, asyncSlot
from modules.ace_tab import ACETab
from modules.avernus_client import AvernusClient
from modules.flux_fill_tab import FluxFillTab
from modules.flux_inpaint_tab import FluxInpaintTab
from modules.flux_tab import FluxTab
from modules.llm_tab import LlmTab
from modules.gallery import GalleryTab
from modules.sdxl_tab import SdxlTab
from modules.sdxl_inpaint_tab import SdxlInpaintTab
from modules.queue import QueueTab
from modules.qwen_tab import QwenTab
from modules.qwen_image_inpaint_tab import QwenImageInpaintTab


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UltraHal")
        self.resize(1280, 800)
        self.avernus_url = "localhost"
        self.avernus_client = AvernusClient(self.avernus_url)
        self.loop = qasync.QEventLoop(self)
        self.pending_requests = []
        self.request_event = asyncio.Event()
        self.request_currently_processing = False
        self.process_request_queue()

        self.avernus_label = QLabel("Avernus URL:")
        self.avernus_entry = QLineEdit(text="localhost")
        self.avernus_entry.returnPressed.connect(self.update_avernus_url)
        self.avernus_current_server = QLabel(f"Current Server: {self.avernus_url}")
        self.avernus_button = QPushButton("Update URL")
        self.avernus_button.clicked.connect(self.update_avernus_url)
        self.update_avernus_url()

        self.tabs = QTabWidget()
        self.gallery_tab = GalleryTab(self.avernus_client, self)
        self.queue_tab = QueueTab(self.avernus_client, self)
        self.tabs.addTab(self.gallery_tab, "Gallery")
        self.tabs.addTab(self.queue_tab, "Queue")

        self.llm_chat_tab = LlmTab(self.avernus_client, self.tabs)
        self.sdxl_tab = SdxlTab(self.avernus_client, self.tabs)
        self.sdxl_inpaint_tab = SdxlInpaintTab(self.avernus_client, self.tabs)
        self.flux_tab = FluxTab(self.avernus_client, self.tabs)
        self.flux_inpaint_tab = FluxInpaintTab(self.avernus_client, self.tabs)
        self.flux_fill_tab = FluxFillTab(self.avernus_client, self.tabs)
        self.ace_tab = ACETab(self.avernus_client, self.tabs)
        self.qwen_tab = QwenTab(self.avernus_client, self.tabs)
        self.qwen_inpaint_tab = QwenImageInpaintTab(self.avernus_client, self.tabs)

        self.avernus_layout = QHBoxLayout()
        self.avernus_layout.addWidget(self.avernus_label)
        self.avernus_layout.addWidget(self.avernus_entry)
        self.avernus_layout.addWidget(self.avernus_current_server)
        self.avernus_layout.addWidget(self.avernus_button)


        self.tabs.addTab(self.llm_chat_tab, "LLM")
        self.tabs.addTab(self.sdxl_tab, "SDXL")
        self.tabs.addTab(self.sdxl_inpaint_tab, "SDXL Inpaint")
        self.tabs.addTab(self.flux_tab, "Flux")
        self.tabs.addTab(self.flux_inpaint_tab, "Flux Inpaint")
        self.tabs.addTab(self.flux_fill_tab, "Flux Fill")
        self.tabs.addTab(self.ace_tab, "ACE")
        self.tabs.addTab(self.qwen_tab, "Qwen")
        self.tabs.addTab(self.qwen_inpaint_tab, "Qwen Inpaint")

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.avernus_layout)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    @asyncSlot()
    async def update_avernus_url(self):
        self.avernus_url = self.avernus_entry.text()
        await self.avernus_client.update_url(self.avernus_url)
        self.avernus_current_server.setText(f"Current Server: {self.avernus_url}")
        print(f"Avernus URL Updated: {self.avernus_url}")
        status = await self.avernus_client.check_status()
        print(status)
        await self.sdxl_tab.make_lora_list()
        await self.sdxl_tab.make_controlnet_list()
        await self.sdxl_tab.make_scheduler_list()
        await self.sdxl_inpaint_tab.make_lora_list()
        await self.sdxl_inpaint_tab.make_scheduler_list()
        await self.flux_tab.make_lora_list()
        await self.flux_inpaint_tab.make_lora_list()
        await self.flux_fill_tab.make_lora_list()
        await self.qwen_tab.make_lora_list()
        await self.qwen_inpaint_tab.make_lora_list()

    @asyncSlot()
    async def process_request_queue(self):
        while True:
            # Wait for a new event or retry if queue isn't empty
            if not self.pending_requests:
                await self.request_event.wait()
                self.request_event.clear()

            while self.pending_requests:
                queue_request = self.pending_requests.pop(0)
                try:
                    await queue_request.run()
                except Exception as e:
                    print(f"Exception while processing request: {e}")

    def closeEvent(self, event):
        QApplication.quit()


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
