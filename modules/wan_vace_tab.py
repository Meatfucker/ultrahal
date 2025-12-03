
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.request_helpers import BaseVideoRequest, QueueObjectWidget
from modules.ui_widgets import (ImageGallery, ImageInputBox, ModelPickerWidget, ParagraphInputBox,
                                ResolutionInput, QueueViewer, SingleLineInputBox, VerticalTabWidget)
from modules.utils import image_to_base64, get_enhanced_prompt


class WanVACETab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.first_frame_label = ImageInputBox(self, "First Frame", "assets/chili.png")
        self.last_frame_label = ImageInputBox(self, "Last Frame", "assets/chili.png")
        self.model_picker = ModelPickerWidget("wan_vace", "Wan VACE Model")
        self.prompt_input = ParagraphInputBox("Prompt")
        self.negative_prompt_input =  ParagraphInputBox("Negative Prompt")
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

        input_layout = QVBoxLayout()
        prompt_layout = QHBoxLayout()
        image_layout = QHBoxLayout()

        config_layout = QVBoxLayout()
        config_layout.setAlignment(Qt.AlignTop)

        input_layout.addLayout(prompt_layout)
        input_layout.addLayout(image_layout)
        prompt_layout.addWidget(self.prompt_input)
        prompt_layout.addWidget(self.negative_prompt_input)
        image_layout.addWidget(self.first_frame_label)
        image_layout.addWidget(self.last_frame_label)

        config_layout.addWidget(self.model_picker)
        config_layout.addWidget(self.frames_input)
        config_layout.addWidget(self.steps_input)
        config_layout.addWidget(self.resolution_input)
        config_layout.addWidget(self.guidance_scale_input)
        config_layout.addWidget(self.flow_shift_input)
        config_layout.addWidget(self.seed_input)
        config_layout.addWidget(self.prompt_enhance_checkbox)
        #config_layout.addStretch()
        config_layout.addWidget(self.submit_button)

        main_layout.addLayout(input_layout)
        main_layout.addLayout(config_layout)
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
        flow_shift = self.flow_shift_input.input.text()
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

        request = WanVACERequest(avernus_client=self.avernus_client,
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
                                 first_frame_enabled=first_frame_enabled,
                                 first_frame=first_frame,
                                 last_frame_enabled=last_frame_enabled,
                                 last_frame=last_frame,
                                 flow_shift=flow_shift,
                                 enhance_prompt=enhance_prompt,
                                 model_name=model_name
                                 )

        queue_item = self.queue_view.add_queue_item(request, self.queue_view)
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class WanVACERequest(BaseVideoRequest):
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
                 first_frame_enabled: bool,
                 first_frame: QPixmap,
                 last_frame_enabled: bool,
                 last_frame: QPixmap,
                 flow_shift: str,
                 enhance_prompt: bool,
                 model_name: str):
        super().__init__(avernus_client, gallery, tabs)
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
        self.first_frame_enabled = first_frame_enabled
        self.first_frame = first_frame
        self.last_frame_enabled = last_frame_enabled
        self.last_frame = last_frame
        self.enhance_prompt = enhance_prompt
        self.model_name = model_name
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"VACE: FF:{self.first_frame_enabled}, LF:{self.last_frame_enabled}"

    @asyncSlot()
    async def generate(self):
        print(f"WAN VACE: {self.prompt}, {self.frames}")
        kwargs = {}
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.frames != "": kwargs["num_frames"] = int(self.frames)
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.width != "":
            kwargs["width"] = int(self.width)
        else:
            kwargs["width"] = 832
        if self.height != "":
            kwargs["height"] = int(self.height)
        else: kwargs["height"] = 480
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.flow_shift != "": kwargs["flow_shift"] = float(self.flow_shift)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.model_name != "" or None: kwargs["model_name"] = str(self.model_name)
        if self.enhance_prompt:
            llm_prompt = await get_enhanced_prompt(self.avernus_client, self.prompt, "Rewrite and enhance the original editing instruction with richer detail, clearer structure, and improved descriptive quality. When adding text that should appear inside an image, place that text inside double quotes and in capital letters. Explain what needs to be changed and what needs to be left unchanged. Explain in details how to change  camera position or tell that camera position shouldn't be changed. example: Original text: add text 911 and 'Police' Result: Add the word '911' in large blue letters to the hood. Below that, add the word 'POLICE.' Keep the camera position unchanged, as do the background, car position, and lighting. Answer only with expanded prompt. Rewrite Prompt: ")
            self.enhanced_prompt = llm_prompt
        kwargs["prompt"] = self.enhanced_prompt

        if self.first_frame_enabled:
            image = image_to_base64(self.first_frame, kwargs["width"], kwargs["height"])
            kwargs["first_frame"] = str(image)
        if self.last_frame_enabled:
            image = image_to_base64(self.last_frame, kwargs["width"], kwargs["height"])
            kwargs["last_frame"] = str(image)
        try:
            response = await self.avernus_client.wan_vace(**kwargs)
            if response["status"] == True or response["status"] == "True":
                self.status = "Finished"
                await self.display_video(response["video"])
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"WAN VACE REQUEST EXCEPTION: {e}")
