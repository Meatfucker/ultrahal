from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.request_helpers import BaseImageRequest, QueueObjectWidget
from modules.ui_widgets import (ImageGallery, ImageInputBox, QueueViewer, SingleLineInputBox, VerticalTabWidget)
from modules.utils import base64_to_images, image_to_base64


class ImageProcessorTab(QWidget):
    def __init__(self, avernus_client: AvernusClient, tabs: VerticalTabWidget):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.processor_selector = QComboBox()
        processor_list = ["RealESRGAN",
                          "Swin2SR"]
        self.processor_selector.insertItems(0, processor_list)
        self.processor_selector.currentTextChanged.connect(self.change_processor)
        self.input_image = ImageInputBox(self, "input", "assets/chili.png")
        self.input_image.enable_checkbox.setChecked(True)

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)
        selector_layout = QVBoxLayout()
        self.config_widget = RealESRGANConfig(self.avernus_client, self.tabs, self.input_image)
        self.config_widget.main_layout.setAlignment(Qt.AlignBottom)

        selector_layout.addWidget(self.processor_selector)
        selector_layout.addWidget(self.input_image)

        self.main_layout.addLayout(selector_layout, stretch=10)
        self.main_layout.addWidget(self.config_widget)

    def change_processor(self):
        self.main_layout.removeWidget(self.config_widget)
        self.config_widget.deleteLater()
        print(self.processor_selector.currentText())
        if self.processor_selector.currentText() == "RealESRGAN":
            self.config_widget = RealESRGANConfig(self.avernus_client, self.tabs, self.input_image)
        elif self.processor_selector.currentText() == "Swin2SR":
            self.config_widget = Swin2SRConfig(self.avernus_client, self.tabs, self.input_image)
        else:
            pass
        self.main_layout.addWidget(self.config_widget)
        self.config_widget.main_layout.setAlignment(Qt.AlignBottom)


class RealESRGANConfig(QWidget):
    def __init__(self,
                 avernus_client: AvernusClient,
                 tabs: VerticalTabWidget,
                 image_input: ImageInputBox):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view
        self.input_image = image_input

        self.scale_input = SingleLineInputBox("Scale", placeholder_text="4")
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setMaximumHeight(40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.scale_input)
        self.main_layout.addWidget(self.submit_button)
        self.setLayout(self.main_layout)


    @asyncSlot()
    async def on_submit(self):
        if self.scale_input.input.text() != "":
            scale = int(self.scale_input.input.text())
        else:
            scale = 4
        request = RealESRGANRequest(self.avernus_client, self.gallery, self.tabs, self.input_image.input_image, scale)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view)
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class Swin2SRConfig(QWidget):
    def __init__(self,
                 avernus_client: AvernusClient,
                 tabs: VerticalTabWidget,
                 image_input: ImageInputBox):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view
        self.input_image = image_input

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setMaximumHeight(40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.submit_button)
        self.setLayout(self.main_layout)


    @asyncSlot()
    async def on_submit(self):
        request = Swin2SRRequest(self.avernus_client, self.gallery, self.tabs, self.input_image.input_image)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view)
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

class RealESRGANRequest(BaseImageRequest):
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 image: QPixmap,
                 scale: int):
        super().__init__(avernus_client, gallery, tabs)
        self.status = None
        self.prompt = "RealESRGAN"
        self.image = image
        self.scale = scale
        self.queue_info = None
        self.ui_item: QueueObjectWidget | None = None

    async def generate(self):
        print("RealESRGAN:")
        base64_input = image_to_base64(self.image, self.image.width(), self.image.height())
        try:
            response = await self.avernus_client.realesrgan(image=base64_input, scale=self.scale)
            if response["status"] == "True" or response["status"] == True:
                self.status = "Finished"
                base64_images = response["images"]
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"REALESRGAN REQUEST EXCEPTION: {e}")

class Swin2SRRequest(BaseImageRequest):
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 image: QPixmap):
        super().__init__(avernus_client, gallery, tabs)
        self.status = None
        self.prompt = "Swin2SR"
        self.image = image
        self.queue_info = None
        self.ui_item: QueueObjectWidget | None = None

    async def generate(self):
        print("Swin2SR:")
        base64_input = image_to_base64(self.image, self.image.width(), self.image.height())
        try:
            response = await self.avernus_client.swin2sr(image=base64_input)
            if response["status"] == "True" or response["status"] == True:
                self.status = "Finished"
                base64_images = response["images"]
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"SWIN2SR REQUEST EXCEPTION: {e}")
