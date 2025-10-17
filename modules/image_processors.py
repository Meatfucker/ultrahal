import asyncio
import time
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.ui_widgets import (ClickablePixmap, ImageGallery, ImageInputBox, QueueObjectWidget, QueueViewer,
                                SingleLineInputBox, VerticalTabWidget)
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
        self.queue_color: str = "#000000"

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
        selector_layout.addLayout(self.input_image)

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
        self.queue_color: str = "#000000"
        self.input_image = image_input

        self.scale_input = SingleLineInputBox("Scale", placeholder_text="4")
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setMaximumHeight(40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.scale_input)
        self.main_layout.addWidget(self.submit_button)
        self.setLayout(self.main_layout)


    @asyncSlot()
    async def on_submit(self):
        self.queue_color: str = "#000000"
        if self.scale_input.input.text() != "":
            scale = int(self.scale_input.input.text())
        else:
            scale = 4
        request = RealESRGANRequest(self.avernus_client, self.gallery, self.tabs, self.input_image.input_image, scale)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, self.queue_color)
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
        self.queue_color: str = "#000000"
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
        self.queue_color: str = "#000000"
        request = Swin2SRRequest(self.avernus_client, self.gallery, self.tabs, self.input_image.input_image)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, self.queue_color)
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

class RealESRGANRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tab: VerticalTabWidget,
                 image: QPixmap,
                 scale: int):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tab
        self.prompt = "RealESRGAN"
        self.image = image
        self.scale = scale
        self.queue_info = None
        self.ui_item: QueueObjectWidget | None = None

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.ui_item.status_label.setText(f"Finished\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    async def generate(self):
        print("RealESRGAN:")
        self.image.save("temp.png", quality=100)
        base64_input = image_to_base64("temp.png", self.image.width(), self.image.height())
        base64_images = await self.avernus_client.realesrgan(image=base64_input, scale=self.scale)
        images = await base64_to_images([base64_images])
        await self.display_images(images)

    @asyncSlot()
    async def display_images(self, images):
        for image in images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.getvalue())
            pixmap_item = ClickablePixmap(pixmap, self.gallery.gallery, self.tabs)
            self.gallery.gallery.add_item(pixmap_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()


class Swin2SRRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tab: VerticalTabWidget,
                 image: QPixmap):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tab
        self.prompt = "Swin2SR"
        self.image = image
        self.queue_info = None
        self.ui_item: QueueObjectWidget | None = None

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.ui_item.status_label.setText(f"Finished\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    async def generate(self):
        print("Swin2SR:")
        self.image.save("temp.png", quality=100)
        base64_input = image_to_base64("temp.png", self.image.width(), self.image.height())
        base64_images = await self.avernus_client.swin2sr(image=base64_input)
        images = await base64_to_images([base64_images])
        await self.display_images(images)

    @asyncSlot()
    async def display_images(self, images):
        for image in images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.getvalue())
            pixmap_item = ClickablePixmap(pixmap, self.gallery.gallery, self.tabs)
            self.gallery.gallery.add_item(pixmap_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()
