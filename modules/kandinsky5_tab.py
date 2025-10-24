import asyncio
import time
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.ui_widgets import (ClickableVideo, ImageGallery, ModelPickerWidget, ParagraphInputBox, ResolutionInput,
                                QueueObjectWidget, QueueViewer, SingleLineInputBox, VerticalTabWidget)


class Kandinsky5Tab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.prompt_input = ParagraphInputBox("Prompt")
        self.negative_prompt_input = ParagraphInputBox("Negative Prompt")
        self.model_picker = ModelPickerWidget("kandinsky5", "Model")
        self.frames_input = SingleLineInputBox("Frames", placeholder_text="121")
        self.steps_input = SingleLineInputBox("Steps", placeholder_text="50")
        self.resolution_input = ResolutionInput(placeholder_x="768", placeholder_y="512")
        self.guidance_scale_input = SingleLineInputBox("Guidance Scale", placeholder_text="5.0")
        self.seed_input = SingleLineInputBox("Seed", placeholder_text="42")
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
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
        input_layout.addLayout(self.steps_input)
        input_layout.addWidget(self.resolution_input)
        input_layout.addLayout(self.guidance_scale_input)
        input_layout.addLayout(self.seed_input)
        input_layout.addWidget(self.prompt_enhance_checkbox)
        input_layout.addStretch()
        input_layout.addWidget(self.submit_button)

        main_layout.addLayout(prompt_layout)
        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)

    @asyncSlot()
    async def on_submit(self):
        model_name = self.model_picker.model_list_picker.currentText()
        prompt = self.prompt_input.input.toPlainText()
        negative_prompt = self.negative_prompt_input.input.toPlainText()
        frames = self.frames_input.input.text()
        steps = self.steps_input.input.text()
        width = self.resolution_input.width_label.input.text()
        height = self.resolution_input.height_label.input.text()
        guidance_scale = self.guidance_scale_input.input.text()
        seed = self.seed_input.input.text()
        enhance_prompt = self.prompt_enhance_checkbox.isChecked()

        request = Kandinsky5Request(avernus_client=self.avernus_client,
                                    gallery=self.gallery,
                                    tabs=self.tabs,
                                    prompt=prompt,
                                    negative_prompt=negative_prompt,
                                    frames=frames,
                                    steps=steps,
                                    width=width,
                                    height=height,
                                    guidance_scale=guidance_scale,
                                    seed=seed,
                                    enhance_prompt=enhance_prompt,
                                    model_name=model_name)
        queue_item = self.queue_view.add_queue_item(request, self.queue_view)


        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class Kandinsky5Request:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 prompt: str,
                 negative_prompt: str,
                 frames: str,
                 steps: str,
                 width: str,
                 height: str,
                 guidance_scale: str,
                 seed: str,
                 enhance_prompt: bool,
                 model_name: str):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.enhanced_prompt = prompt
        self.negative_prompt = negative_prompt
        self.frames = frames
        self.steps = steps
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.seed = seed
        self.enhance_prompt = enhance_prompt
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
        print(f"KANDINSKY5: {self.prompt}, {self.frames}")
        if self.enhance_prompt:
            llm_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            self.enhanced_prompt = llm_prompt
        kwargs = {}
        kwargs["prompt"] = self.enhanced_prompt
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.frames != "": kwargs["num_frames"] = int(self.frames)
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.width != "": kwargs["width"] = float(self.width)
        if self.height != "": kwargs["height"] = float(self.height)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.model_name != "" or None: kwargs["model_name"] = str(self.model_name)
        response = await self.avernus_client.kandinsky5_t2v(**kwargs)
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
