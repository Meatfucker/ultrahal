import asyncio
import tempfile
import time
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QSizePolicy
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.ui_widgets import (ClickableVideo, ImageGallery, ImageInputBox, ModelPickerWidget, ParagraphInputBox,
                                ResolutionInput, QueueObjectWidget, QueueViewer, SingleLineInputBox, VerticalTabWidget)
from modules.utils import image_to_base64


class FramepackTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view
        self.queue_color: str = "#004031"

        self.first_frame_label = ImageInputBox(self, "First Frame", "assets/chili.png")
        self.last_frame_label = ImageInputBox(self, "Last Frame", "assets/chili.png")
        self.model_picker = ModelPickerWidget("framepack", "Framepack Model")
        self.prompt_input = ParagraphInputBox("Prompt")
        self.negative_prompt_input =  ParagraphInputBox("Negative Prompt")
        self.frames_input = SingleLineInputBox("Frames", placeholder_text="129")
        self.resolution_input = ResolutionInput(placeholder_x="1280", placeholder_y="720")
        self.guidance_scale_input = SingleLineInputBox("Guidance Scale", placeholder_text="6.0")
        self.seed_input = SingleLineInputBox("Seed", placeholder_text="42")
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")

        main_layout = QHBoxLayout()

        input_layout = QVBoxLayout()
        prompt_layout = QHBoxLayout()
        image_layout = QHBoxLayout()

        config_layout = QVBoxLayout()
        config_layout.setAlignment(Qt.AlignTop)

        input_layout.addLayout(prompt_layout)
        input_layout.addLayout(image_layout)
        prompt_layout.addLayout(self.prompt_input)
        prompt_layout.addLayout(self.negative_prompt_input)
        image_layout.addLayout(self.first_frame_label)
        image_layout.addLayout(self.last_frame_label)

        config_layout.addLayout(self.model_picker)
        config_layout.addLayout(self.frames_input)
        config_layout.addWidget(self.resolution_input)
        config_layout.addLayout(self.guidance_scale_input)
        config_layout.addLayout(self.seed_input)
        config_layout.addWidget(self.prompt_enhance_checkbox)
        config_layout.addStretch()
        config_layout.addWidget(self.submit_button)

        main_layout.addLayout(input_layout)
        main_layout.addLayout(config_layout)
        self.setLayout(main_layout)

    @asyncSlot()
    async def on_submit(self):
        self.queue_color: str = "#210000"
        model_name = self.model_picker.model_list_picker.currentText()
        prompt = self.prompt_input.input.toPlainText()
        negative_prompt = self.negative_prompt_input.input.toPlainText()
        frames = self.frames_input.input.text()
        width = self.resolution_input.width_label.input.text()
        height = self.resolution_input.height_label.input.text()
        guidance_scale = self.guidance_scale_input.input.text()
        seed = self.seed_input.input.text()
        first_frame_enabled = self.first_frame_label.enable_checkbox.isChecked()
        last_frame_enabled = self.last_frame_label.enable_checkbox.isChecked()
        enhance_prompt = self.prompt_enhance_checkbox.isChecked()
        if first_frame_enabled is True:
            first_frame = self.first_frame_label.input_image
        else:
            first_frame = None
        if last_frame_enabled is True:
            last_frame = self.last_frame_label.input_image
        else:
            last_frame = None

        request = FramepackRequest(avernus_client=self.avernus_client,
                                   gallery=self.gallery,
                                   tabs=self.tabs,
                                   prompt=prompt,
                                   negative_prompt=negative_prompt,
                                   frames=frames,
                                   width=width,
                                   height=height,
                                   guidance_scale=guidance_scale,
                                   seed=seed,
                                   first_frame_enabled=first_frame_enabled,
                                   first_frame=first_frame,
                                   last_frame_enabled=last_frame_enabled,
                                   last_frame=last_frame,
                                   enhance_prompt=enhance_prompt,
                                   model_name=model_name)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#443366")
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class FramepackRequest:
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
                 first_frame_enabled: bool,
                 first_frame: QPixmap,
                 last_frame_enabled: bool,
                 last_frame: QPixmap,
                 enhance_prompt: bool,
                 model_name: str):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.enhanced_prompt = prompt
        self.negative_prompt = negative_prompt
        self.frames = frames
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.seed = seed
        self.first_frame_enabled = first_frame_enabled
        self.first_frame = first_frame
        self.last_frame_enabled = last_frame_enabled
        self.last_frame = last_frame
        self.enhance_prompt = enhance_prompt
        self.model_name = model_name
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"Framepack: {self.width}x{self.height} Frames: {self.frames} FF:{self.first_frame_enabled}, LF:{self.last_frame_enabled}"

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
        print(f"FRAMEPACK: {self.prompt}, {self.frames}")
        kwargs = {}
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.frames != "": kwargs["num_frames"] = int(self.frames)
        if self.width != "":
            kwargs["width"] = int(self.width)
        else:
            kwargs["width"] = 832
        if self.height != "":
            kwargs["height"] = int(self.height)
        else: kwargs["height"] = 480
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.model_name != "" or None: kwargs["model_name"] = str(self.model_name)
        if self.enhance_prompt:
            llm_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            self.enhanced_prompt = llm_prompt
        kwargs["prompt"] = self.enhanced_prompt

        if self.first_frame_enabled:
            first_frame_temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".png")
            self.first_frame.save(first_frame_temp_file.name, quality=100)
            image = image_to_base64(first_frame_temp_file.name, kwargs["width"], kwargs["height"])
            kwargs["image"] = str(image)
        if self.last_frame_enabled:
            last_frame_temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".png")
            self.last_frame.save(last_frame_temp_file.name, quality=100)
            image = image_to_base64(last_frame_temp_file.name, kwargs["width"], kwargs["height"])
            kwargs["last_image"] = str(image)
        response = await self.avernus_client.framepack(**kwargs)
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

