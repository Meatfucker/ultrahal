import sys
import asyncio

import qasync
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                               QWidget, QStyleFactory)
from qasync import QEventLoop, asyncSlot

from modules.ui_widgets import CircleWidget, VerticalTabWidget
from modules.ace_tab import ACETab
from modules.avernus_client import AvernusClient
from modules.chroma_tab import ChromaTab
from modules.flux_fill_tab import FluxFillTab
from modules.flux_inpaint_tab import FluxInpaintTab
from modules.flux_tab import FluxTab
from modules.framepack_tab import FramepackTab
from modules.llm_tab import LlmTab
from modules.gallery import GalleryTab
from modules.hidream import HiDreamTab
from modules.hunyuan_video_tab import HunyuanVideoTab
from modules.image_processors import ImageProcessorTab
from modules.sdxl_tab import SdxlTab
from modules.sdxl_inpaint_tab import SdxlInpaintTab
from modules.queue import QueueTab
from modules.qwen_tab import QwenTab
from modules.qwen_image_inpaint_tab import QwenImageInpaintTab
from modules.qwen_edit_plus_tab import QwenEditPlusTab
from modules.wan_tab import WanTab
from modules.wan_vace_tab import WanVACETab


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UltraHal")
        self.resize(1280, 800)
        self.avernus_url: str = "localhost"
        self.avernus_port: int = 6969
        self.avernus_client: AvernusClient = AvernusClient(self.avernus_url)
        self.loop = qasync.QEventLoop(self)
        self.pending_requests: list = []
        self.request_event = asyncio.Event()
        self.request_currently_processing: bool = False
        self.process_request_queue()

        self.avernus_label = QLabel("Avernus URL:")
        self.avernus_entry = QLineEdit(text="localhost")
        self.avernus_entry.returnPressed.connect(self.update_avernus_url)
        self.avernus_port_label = QLabel("Port:")
        self.avernus_port_entry = QLineEdit(text="6969")
        self.avernus_port_entry.returnPressed.connect(self.update_avernus_url)
        self.avernus_current_server = QLabel(f"Current Server:{self.avernus_url}")
        self.avernus_online_label = CircleWidget()
        self.avernus_button = QPushButton("Update URL")
        self.avernus_button.clicked.connect(self.update_avernus_url)
        self.update_avernus_url()

        self.tabs = VerticalTabWidget()

        self.gallery_tab = GalleryTab(self.avernus_client, self)
        self.queue_tab = QueueTab(self.avernus_client, self)
        self.tabs.addTab(self.gallery_tab, "Gallery")
        self.tabs.addTab(self.queue_tab, "Queue")

        self.ace_tab = ACETab(self.avernus_client, self.tabs)
        self.chroma_tab = ChromaTab(self.avernus_client, self.tabs)
        self.flux_tab = FluxTab(self.avernus_client, self.tabs)
        self.flux_inpaint_tab = FluxInpaintTab(self.avernus_client, self.tabs)
        self.flux_fill_tab = FluxFillTab(self.avernus_client, self.tabs)
        self.framepack_tab = FramepackTab(self.avernus_client, self.tabs)
        self.hidream_tab = HiDreamTab(self.avernus_client, self.tabs)
        self.hunyuan_video_tab = HunyuanVideoTab(self.avernus_client, self.tabs)
        self.image_processor_tab = ImageProcessorTab(self.avernus_client, self.tabs)
        self.llm_chat_tab = LlmTab(self.avernus_client, self.tabs)
        self.qwen_tab = QwenTab(self.avernus_client, self.tabs)
        self.qwen_inpaint_tab = QwenImageInpaintTab(self.avernus_client, self.tabs)
        self.qwen_edit_tab = QwenEditPlusTab(self.avernus_client, self.tabs)
        self.wan_tab = WanTab(self.avernus_client, self.tabs)
        self.wan_vace_tab = WanVACETab(self.avernus_client, self.tabs)
        self.sdxl_tab = SdxlTab(self.avernus_client, self.tabs)
        self.sdxl_inpaint_tab = SdxlInpaintTab(self.avernus_client, self.tabs)


        self.tabs.addTab(self.ace_tab, "ACE")
        self.tabs.addTab(self.chroma_tab, "Chroma")
        self.tabs.addTab(self.flux_tab, "Flux")
        self.tabs.addTab(self.flux_inpaint_tab, "Flux Inpaint")
        self.tabs.addTab(self.flux_fill_tab, "Flux Fill")
        self.tabs.addTab(self.framepack_tab, "Framepack")
        self.tabs.addTab(self.hidream_tab, "HiDream")
        self.tabs.addTab(self.hunyuan_video_tab, "Hunyuan Video")
        self.tabs.addTab(self.llm_chat_tab, "LLM")
        self.tabs.addTab(self.image_processor_tab, "Processors")
        self.tabs.addTab(self.qwen_tab, "Qwen")
        self.tabs.addTab(self.qwen_inpaint_tab, "Qwen Inpaint")
        self.tabs.addTab(self.qwen_edit_tab, "Qwen Edit+")
        self.tabs.addTab(self.sdxl_tab, "SDXL")
        self.tabs.addTab(self.sdxl_inpaint_tab, "SDXL Inpaint")
        self.tabs.addTab(self.wan_tab, "Wan")
        self.tabs.addTab(self.wan_vace_tab, "Wan VACE")

        self.avernus_layout = QHBoxLayout()
        self.avernus_layout.addWidget(self.avernus_label)
        self.avernus_layout.addWidget(self.avernus_entry)
        self.avernus_layout.addWidget(self.avernus_port_label)
        self.avernus_layout.addWidget(self.avernus_port_entry)
        self.avernus_layout.addWidget(self.avernus_current_server)
        self.avernus_layout.addWidget(self.avernus_online_label)
        self.avernus_layout.addWidget(self.avernus_button)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.avernus_layout)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        self.setStyle(QStyleFactory.create("Fusion"))

    @asyncSlot()
    async def update_avernus_url(self):
        self.avernus_url = self.avernus_entry.text()
        self.avernus_port = int(self.avernus_port_entry.text())
        await self.avernus_client.update_url(self.avernus_url, self.avernus_port)
        self.avernus_current_server.setText(f"Current Server: {self.avernus_url}")
        print(f"Avernus URL Updated: {self.avernus_url}")
        await self.check_status()
        await self.update_lists()


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

    @asyncSlot()
    async def check_status(self):
        status = await self.avernus_client.check_status()
        if status.get("status") == "Ok!":
            self.avernus_online_label.set_color(1)
        else:
            self.avernus_online_label.set_color(0)

    @asyncSlot()
    async def update_lists(self):
        await self.sdxl_tab.make_lora_list()
        await self.sdxl_tab.make_controlnet_list()
        await self.sdxl_tab.make_scheduler_list()
        await self.sdxl_inpaint_tab.make_lora_list()
        await self.sdxl_inpaint_tab.make_scheduler_list()
        await self.flux_tab.make_lora_list()
        await self.flux_inpaint_tab.make_lora_list()
        await self.flux_fill_tab.make_lora_list()
        await self.qwen_tab.make_lora_list()
        await self.qwen_edit_tab.make_lora_list()
        await self.qwen_inpaint_tab.make_lora_list()
        await self.chroma_tab.make_lora_list()


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
