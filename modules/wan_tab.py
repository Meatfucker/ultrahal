import asyncio
import tempfile
import time
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.ui_widgets import (ClickableVideo, ImageGallery, ImageInputBox, ModelPickerWidget, ParagraphInputBox,
                                ResolutionInput, QueueObjectWidget, QueueViewer, SingleLineInputBox, VideoInputWidget,
                                VerticalTabWidget)
from modules.utils import image_to_base64


class WanTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.i2v_image_label = ImageInputBox(self, "i2v", "assets/chili.png")
        self.v2v_video_label = VideoInputWidget("v2v")
        self.model_picker_t2v = ModelPickerWidget("wan_t2v", "T2V Model")
        self.model_picker_i2v = ModelPickerWidget("wan_i2v", "I2V Model")
        self.model_picker_v2v = ModelPickerWidget("wan_v2v", "V2V Model")
        self.prompt_input = ParagraphInputBox("Prompt")
        self.negative_prompt_input = ParagraphInputBox("Negative Prompt")
        self.frames_input = SingleLineInputBox("Frames", placeholder_text="81")
        self.steps_input = SingleLineInputBox("Steps", placeholder_text="50")
        self.resolution_input = ResolutionInput(placeholder_x="832", placeholder_y="480")
        self.guidance_scale_input = SingleLineInputBox("Guidance Scale", placeholder_text="5.0")
        self.flow_shift_input = SingleLineInputBox("Flow Shift", placeholder_text="3.0")
        self.seed_input = SingleLineInputBox("Seed", placeholder_text="42")
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")

        main_layout = QHBoxLayout()
        image_layout = QVBoxLayout()
        image_layout.setAlignment(Qt.AlignTop)
        input_layout = QVBoxLayout()
        input_layout.setAlignment(Qt.AlignTop)
        image_layout.addLayout(self.i2v_image_label)
        image_layout.addWidget(self.v2v_video_label, stretch=1)
        input_layout.addLayout(self.model_picker_t2v)
        input_layout.addLayout(self.model_picker_i2v)
        input_layout.addLayout(self.model_picker_v2v)
        input_layout.addLayout(self.prompt_input)
        input_layout.addLayout(self.negative_prompt_input)
        input_layout.addLayout(self.frames_input)
        input_layout.addLayout(self.steps_input)
        input_layout.addWidget(self.resolution_input)
        input_layout.addLayout(self.guidance_scale_input)
        input_layout.addLayout(self.flow_shift_input)
        input_layout.addLayout(self.seed_input)
        input_layout.addWidget(self.prompt_enhance_checkbox)
        input_layout.addStretch()
        input_layout.addWidget(self.submit_button)

        main_layout.addLayout(image_layout)
        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)

        self.setup_mutually_exclusive_checkboxes()

    @asyncSlot()
    async def on_submit(self):
        model_name_t2v = self.model_picker_t2v.model_list_picker.currentText()
        model_name_i2v = self.model_picker_i2v.model_list_picker.currentText()
        model_name_v2v = self.model_picker_v2v.model_list_picker.currentText()
        prompt = self.prompt_input.input.toPlainText()
        negative_prompt = self.negative_prompt_input.input.toPlainText()
        frames = self.frames_input.input.text()
        steps = self.steps_input.input.text()
        width = self.resolution_input.width_label.input.text()
        height = self.resolution_input.height_label.input.text()
        guidance_scale = self.guidance_scale_input.input.text()
        flow_shift = self.flow_shift_input.input.text()
        seed = self.seed_input.input.text()
        i2v_image_enable = self.i2v_image_label.enable_checkbox.isChecked()
        v2v_enable = self.v2v_video_label.enable_checkbox.isChecked()
        enhance_prompt = self.prompt_enhance_checkbox.isChecked()
        if v2v_enable is not True:
            if i2v_image_enable is True:
                i2v_image = self.i2v_image_label.input_image
                model_name = model_name_i2v
            else:
                i2v_image = None
                model_name = model_name_t2v

            request = WanRequest(avernus_client=self.avernus_client,
                                 gallery=self.gallery,
                                 tabs=self.tabs,
                                 prompt=prompt,
                                 negative_prompt=negative_prompt,
                                 frames=frames,
                                 steps=steps,
                                 width=width,
                                 height=height,
                                 guidance_scale=guidance_scale,
                                 flow_shift=flow_shift,
                                 seed=seed,
                                 i2v_image_enabled=i2v_image_enable,
                                 i2v_image=i2v_image,
                                 model_name=model_name,
                                 enhance_prompt=enhance_prompt,
                                 )
            queue_item = self.queue_view.add_queue_item(request, self.queue_view)
        else:
            request = WanV2VRequest(avernus_client=self.avernus_client,
                                    gallery=self.gallery,
                                    tabs=self.tabs,
                                    prompt=prompt,
                                    steps=steps,
                                    negative_prompt=negative_prompt,
                                    width=width,
                                    height=height,
                                    guidance_scale=guidance_scale,
                                    flow_shift=flow_shift,
                                    seed=seed,
                                    video=self.v2v_video_label.file_path,
                                    model_name=model_name_v2v,
                                    enhance_prompt=enhance_prompt,)
            queue_item = self.queue_view.add_queue_item(request, self.queue_view)

        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

    def setup_mutually_exclusive_checkboxes(self):
        self.i2v_image_label.enable_checkbox.toggled.connect(self.on_i2v_checkbox_toggled)
        self.v2v_video_label.enable_checkbox.toggled.connect(self.on_v2v_checkbox_toggled)

    def on_i2v_checkbox_toggled(self, checked):
        if checked:
            self.v2v_video_label.enable_checkbox.blockSignals(True)
            self.v2v_video_label.enable_checkbox.setChecked(False)
            self.v2v_video_label.enable_checkbox.blockSignals(False)

    def on_v2v_checkbox_toggled(self, checked):
        if checked:
            self.i2v_image_label.enable_checkbox.blockSignals(True)
            self.i2v_image_label.enable_checkbox.setChecked(False)
            self.i2v_image_label.enable_checkbox.blockSignals(False)


class WanRequest:
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
                 i2v_image_enabled: bool,
                 i2v_image: QPixmap,
                 model_name: str,
                 flow_shift: str,
                 enhance_prompt: bool,):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.status = None
        self.prompt = prompt
        self.enhanced_prompt = prompt
        self.negative_prompt = negative_prompt
        self.frames = frames
        self.steps = steps
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.flow_shift = flow_shift
        self.seed = seed
        self.i2v_image_enabled = i2v_image_enabled
        self.i2v_image = i2v_image
        self.model_name = model_name
        self.enhance_prompt = enhance_prompt
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"I2I:{self.i2v_image_enabled}"

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        elapsed_time = time.time() - start_time
        self.ui_item.status_label.setText(f"{self.status}\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        print(f"WAN: {self.prompt}, {self.frames}")
        kwargs = {}
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.frames != "": kwargs["num_frames"] = int(self.frames)
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.width != "": kwargs["width"] = float(self.width)
        if self.height != "": kwargs["height"] = float(self.height)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.flow_shift != "": kwargs["flow_shift"] = float(self.flow_shift)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.model_name != "" or None: kwargs["model_name"] = str(self.model_name)
        if self.enhance_prompt:
            llm_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            self.enhanced_prompt = llm_prompt
        kwargs["prompt"] = self.enhanced_prompt

        if self.i2v_image_enabled:
            i2v_temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".png")
            self.i2v_image.save(i2v_temp_file.name, quality=100)
            if self.width == "":
                kwargs["width"] = None
                i2v_width = int(self.i2v_image.width())
            else:
                i2v_width = int(self.width)
            if self.height == "":
                kwargs["height"] = None
                i2v_height = int(self.i2v_image.height())
            else:
                i2v_height = int(self.height)
            image = image_to_base64(i2v_temp_file.name, i2v_width, i2v_height)
            kwargs["image"] = str(image)
        try:
            response = await self.avernus_client.wan_ti2v(**kwargs)
            if response["status"] == True or response["status"] == "True":
                self.status = "Finished"
                await self.display_video(response["video"])
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"WAN REQUEST EXCEPTION: {e}")

    @asyncSlot()
    async def display_video(self, response):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_file.write(response)
        temp_file.close()
        video_item = self.load_video_from_file(temp_file.name)
        self.gallery.gallery.add_item(video_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    def load_video_from_file(self, video_path):
        return ClickableVideo(video_path, self.prompt)

class WanV2VRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 prompt: str,
                 negative_prompt: str,
                 width: str,
                 height: str,
                 guidance_scale: str,
                 seed: str,
                 steps: str,
                 video,
                 model_name: str,
                 enhance_prompt: bool,
                 flow_shift: str):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.status = None
        self.prompt = prompt
        self.enhanced_prompt = prompt
        self.negative_prompt = negative_prompt
        self.width = width
        self.height = height
        self.steps = steps
        self.guidance_scale = guidance_scale
        self.flow_shift = flow_shift
        self.seed = seed
        self.video = video
        self.model_name = model_name
        self.enhance_prompt = enhance_prompt
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"{self.prompt}, {self.width}x{self.height}, {self.model_name}"

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        elapsed_time = time.time() - start_time
        self.ui_item.status_label.setText(f"{self.status}\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        print(f"WAN: {self.prompt}")
        kwargs = {}
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.width != "": kwargs["width"] = float(self.width)
        if self.height != "": kwargs["height"] = float(self.height)
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.flow_shift != "": kwargs["flow_shift"] = float(self.flow_shift)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.model_name != "" or None: kwargs["model_name"] = str(self.model_name)
        if self.enhance_prompt:
            llm_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            self.enhanced_prompt = llm_prompt
        kwargs["prompt"] = self.enhanced_prompt
        kwargs["video_path"] = self.video
        try:
            response = await self.avernus_client.wan_v2v(**kwargs)
            if response["status"] == True or response["status"] == "True":
                self.status = "Finished"
                await self.display_video(response["video"])
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"WAN V2V REQUEST EXCEPTION: {e}")

    @asyncSlot()
    async def display_video(self, response):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_file.write(response)
        temp_file.close()
        video_item = self.load_video_from_file(temp_file.name)
        self.gallery.gallery.add_item(video_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    def load_video_from_file(self, video_path):
        return ClickableVideo(video_path, self.prompt)
