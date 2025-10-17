import asyncio
import time
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.ui_widgets import (ClickableVideo, ImageGallery, ModelPickerWidget, ParagraphInputBox, ResolutionInput,
                                QueueObjectWidget, QueueViewer, SingleLineInputBox, VerticalTabWidget)


class HunyuanVideoTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view
        self.queue_color: str = "#191000"

        self.prompt_input = ParagraphInputBox("Prompt")
        self.negative_prompt_input = ParagraphInputBox("Negative Prompt")
        self.model_picker = ModelPickerWidget("hunyuan_video", "Model")
        self.frames_input = SingleLineInputBox("Frames", placeholder_text="129")
        self.resolution_input = ResolutionInput(placeholder_x="1280", placeholder_y="720")
        self.guidance_scale_input = SingleLineInputBox("Guidance Scale", placeholder_text="6.0")
        self.seed_input = SingleLineInputBox("Seed", placeholder_text="42")
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")

        main_layout = QHBoxLayout()
        prompt_layout = QVBoxLayout()
        prompt_layout.setAlignment(Qt.AlignTop)
        input_layout = QVBoxLayout()
        input_layout.setAlignment(Qt.AlignTop)
        prompt_layout.addLayout(self.prompt_input)
        prompt_layout.addLayout(self.negative_prompt_input)
        input_layout.addLayout(self.model_picker)
        input_layout.addLayout(self.frames_input)
        input_layout.addWidget(self.resolution_input)
        input_layout.addLayout(self.guidance_scale_input)
        input_layout.addLayout(self.seed_input)
        input_layout.addStretch()
        input_layout.addWidget(self.submit_button)

        main_layout.addLayout(prompt_layout)
        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)

    @asyncSlot()
    async def on_submit(self):
        self.queue_color: str = "#190000"
        model_name = self.model_picker.model_list_picker.currentText()
        prompt = self.prompt_input.input.toPlainText()
        negative_prompt = self.negative_prompt_input.input.toPlainText()
        frames = self.frames_input.input.text()
        width = self.resolution_input.width_label.input.text()
        height = self.resolution_input.height_label.input.text()
        guidance_scale = self.guidance_scale_input.input.text()
        seed = self.seed_input.input.text()

        request = HunyuanVideoRequest(avernus_client=self.avernus_client,
                                      gallery=self.gallery,
                                      tabs=self.tabs,
                                      prompt=prompt,
                                      negative_prompt=negative_prompt,
                                      frames=frames,
                                      width=width,
                                      height=height,
                                      guidance_scale=guidance_scale,
                                      seed=seed,
                                      model_name=model_name)
        queue_item = self.queue_view.add_queue_item(request, self.queue_view, self.queue_color)


        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class HunyuanVideoRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 prompt: str,
                 negative_prompt: str,
                 frames: str,
                 width: str,
                 height: str,
                 guidance_scale: str,
                 seed: str,
                 model_name: str):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.frames = frames
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.seed = seed
        self.model_name = model_name
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"Width:{self.width}, Height{self.height}"

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        elapsed_time = time.time() - start_time
        self.ui_item.status_label.setText(f"Finished\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        print(f"HUNYUAN_VIDEO: {self.prompt}, {self.frames}")
        kwargs = {}
        kwargs["prompt"] = self.prompt
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.frames != "": kwargs["num_frames"] = int(self.frames)
        if self.width != "": kwargs["width"] = float(self.width)
        if self.height != "": kwargs["height"] = float(self.height)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.model_name != "" or None: kwargs["model_name"] = str(self.model_name)
        response = await self.avernus_client.hunyuan_ti2v(**kwargs)
        await self.display_video(response)

    @asyncSlot()
    async def display_video(self, response):
        video_item = self.load_video_from_file(response)
        self.gallery.gallery.add_item(video_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    def load_video_from_file(self, video_path):
        return ClickableVideo(video_path, self.prompt)
