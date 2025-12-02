import tempfile
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import  QCheckBox, QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout, QWidget
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.request_helpers import BaseImageRequest, QueueObjectWidget
from modules.ui_widgets import (HorizontalSlider, ImageGallery, ImageInputBox, ModelPickerWidget,
                                ParagraphInputBox, PromptPickerWidget, QueueViewer, ResolutionInput,
                                SingleLineInputBox, VerticalTabWidget)
from modules.utils import base64_to_images, image_to_base64, get_generic_danbooru_tags, get_random_artist_prompt, get_enhanced_prompt


class SanaSprintTab(QWidget):
    def __init__(self, avernus_client: AvernusClient, tabs: VerticalTabWidget):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")
        self.prompt_picker = PromptPickerWidget()
        self.prompt_label = ParagraphInputBox("Prompt")
        self.model_picker = ModelPickerWidget("sana_sprint")
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.add_random_artist_checkbox = QCheckBox("Add Random Artist")
        self.add_random_danbooru_tags_checkbox = QCheckBox("Add Random Danbooru Tags")
        self.danbooru_tags_slider = HorizontalSlider("Num Tags", 1, 20, 6, enable_ticks=False)
        self.resolution_widget = ResolutionInput()
        self.steps_label = SingleLineInputBox("Steps:", placeholder_text="30")
        self.batch_size_label = SingleLineInputBox("Batch Size:", placeholder_text="4")
        self.guidance_scale_label = SingleLineInputBox("Guidance Scale:", placeholder_text="5.0")
        self.seed_label = SingleLineInputBox("Seed", placeholder_text="42")
        self.max_timesteps_label = SingleLineInputBox("Max Timesteps", placeholder_text="1.5708")
        self.intermediate_timesteps_label = SingleLineInputBox("Intermediate Timesteps", placeholder_text="1.3")

        self.i2i_image_label = ImageInputBox(self, "i2i", "assets/chili.png")
        self.i2i_strength_label = HorizontalSlider("Strength", 0, 100, 70, enable_ticks=False)

        self.main_layout = QHBoxLayout()
        self.input_layout = QVBoxLayout()
        self.prompt_layout = QVBoxLayout()
        self.prompt_layout.setAlignment(Qt.AlignTop)

        self.input_layout.addWidget(self.i2i_image_label)
        self.input_layout.addWidget(self.i2i_strength_label)

        self.prompt_layout.addWidget(self.model_picker)
        self.prompt_layout.addWidget(self.prompt_picker)
        self.prompt_layout.addLayout(self.prompt_label)
        self.prompt_layout.addWidget(self.prompt_enhance_checkbox)
        self.prompt_layout.addWidget(self.add_random_artist_checkbox)
        self.prompt_layout.addWidget(self.add_random_danbooru_tags_checkbox)
        self.prompt_layout.addWidget(self.danbooru_tags_slider)
        self.prompt_layout.addWidget(self.resolution_widget)
        self.prompt_layout.addLayout(self.steps_label)
        self.prompt_layout.addLayout(self.batch_size_label)
        self.prompt_layout.addLayout(self.guidance_scale_label)
        self.prompt_layout.addLayout(self.seed_label)
        self.prompt_layout.addLayout(self.max_timesteps_label)
        self.prompt_layout.addLayout(self.intermediate_timesteps_label)
        self.prompt_layout.addWidget(self.submit_button)

        self.main_layout.addLayout(self.input_layout)
        self.main_layout.addLayout(self.prompt_layout)
        self.setLayout(self.main_layout)

    @asyncSlot()
    async def on_submit(self):
        added_prompts = self.prompt_picker.get_selected_items()
        prompt = self.prompt_label.input.toPlainText()
        for added_prompt in added_prompts:
            prompt = f"{prompt}, {added_prompt}"
        width = self.resolution_widget.width_label.input.text()
        height = self.resolution_widget.height_label.input.text()
        steps = self.steps_label.input.text()
        batch_size = self.batch_size_label.input.text()
        guidance_scale = self.guidance_scale_label.input.text()
        seed = self.seed_label.input.text()
        max_timesteps = self.max_timesteps_label.input.text()
        intermediate_timesteps = self.intermediate_timesteps_label.input.text()
        model_name = self.model_picker.model_list_picker.currentText()
        strength = round(float(self.i2i_strength_label.slider.value() * 0.01), 2)
        i2i_image_enable = self.i2i_image_label.enable_checkbox.isChecked()
        if i2i_image_enable is True:
            i2i_image = self.i2i_image_label.input_image
        else:
            i2i_image = None
        enhance_prompt = self.prompt_enhance_checkbox.isChecked()
        add_artist = self.add_random_artist_checkbox.isChecked()
        add_danbooru_tags = self.add_random_danbooru_tags_checkbox.isChecked()
        danbooru_tags_amount = int(self.danbooru_tags_slider.slider.value())

        try:
            if i2i_image_enable is True:
                request = SanaSprintI2IRequest(avernus_client=self.avernus_client,
                                               gallery=self.gallery,
                                               tabs=self.tabs,
                                               prompt=prompt,
                                               width=width,
                                               height=height,
                                               steps=steps,
                                               batch_size=batch_size,
                                               guidance_scale=guidance_scale,
                                               strength=strength,
                                               i2i_image_enabled=i2i_image_enable,
                                               i2i_image=i2i_image,
                                               enhance_prompt=enhance_prompt,
                                               add_artist=add_artist,
                                               add_danbooru_tags=add_danbooru_tags,
                                               danbooru_tags_amount=danbooru_tags_amount,
                                               model_name=model_name,
                                               seed=seed,
                                               max_timesteps=max_timesteps,
                                               intermediate_timesteps=intermediate_timesteps)
            else:
                request = SanaSprintRequest(avernus_client=self.avernus_client,
                                            gallery=self.gallery,
                                            tabs=self.tabs,
                                            prompt=prompt,
                                            width=width,
                                            height=height,
                                            steps=steps,
                                            batch_size=batch_size,
                                            guidance_scale=guidance_scale,
                                            strength=strength,
                                            i2i_image_enabled=i2i_image_enable,
                                            i2i_image=i2i_image,
                                            enhance_prompt=enhance_prompt,
                                            add_artist=add_artist,
                                            add_danbooru_tags=add_danbooru_tags,
                                            danbooru_tags_amount=danbooru_tags_amount,
                                            model_name=model_name,
                                            seed=seed,
                                            max_timesteps=max_timesteps,
                                            intermediate_timesteps=intermediate_timesteps)
            queue_item = self.queue_view.add_queue_item(request, self.queue_view)
            request.ui_item = queue_item
            self.tabs.parent().pending_requests.append(request)
            self.tabs.parent().request_event.set()
        except Exception as e:
            print(f"Sana Sprint on_submit EXCEPTION: {e}")

class SanaSprintRequest(BaseImageRequest):
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 prompt: str,
                 width: str,
                 height: str,
                 steps: str,
                 batch_size: str,
                 guidance_scale: str,
                 strength: float,
                 i2i_image_enabled: bool,
                 i2i_image: QPixmap,
                 enhance_prompt: bool,
                 model_name: str,
                 seed: str,
                 max_timesteps: str,
                 intermediate_timesteps: str,
                 add_artist: bool,
                 add_danbooru_tags: bool,
                 danbooru_tags_amount: int):
        super().__init__(avernus_client, gallery, tabs)
        self.status = None
        self.prompt = prompt
        self.enhanced_prompt = prompt
        self.width = width
        self.height = height
        self.steps = steps
        self.batch_size = batch_size
        self.guidance_scale = guidance_scale
        self.seed = seed
        self.max_timesteps = max_timesteps
        self.intermediate_timesteps = intermediate_timesteps
        self.model_name = model_name
        self.strength = strength
        self.i2i_image_enabled = i2i_image_enabled
        self.i2i_image = i2i_image
        self.enhance_prompt = enhance_prompt
        self.add_artist = add_artist
        self.add_danbooru_tags = add_danbooru_tags
        self.danbooru_tags_amount = danbooru_tags_amount
        if self.width == "":
            self.width = 1024
        if self.height == "":
            self.height = 1024
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"{self.width}x{self.height}, {self.model_name},EP:{self.enhance_prompt},I2I:{self.i2i_image_enabled}"

    @asyncSlot()
    async def generate(self):
        """API call to generate the images and convert them from base64"""
        print(f"Chroma: {self.prompt}, {self.width}, {self.height}, {self.steps}, {self.batch_size}, {self.strength}")

        kwargs = {}
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.batch_size != "": kwargs["batch_size"] = int(self.batch_size)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.max_timesteps != "": kwargs["max_timesteps"] = float(self.max_timesteps)
        if self.intermediate_timesteps != "": kwargs["intermediate_timesteps"] = float(self.intermediate_timesteps)
        kwargs["model_name"] = str(self.model_name)
        if self.width is not None: kwargs["width"] = int(self.width)
        if self.height is not None: kwargs["height"] = int(self.height)


        if self.i2i_image_enabled:
            i2i_temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".png")
            self.i2i_image.save(i2i_temp_file.name, quality=100)
            image = image_to_base64(i2i_temp_file.name, kwargs["width"], kwargs["height"])
            kwargs["image"] = str(image)
            if self.strength != "":
                kwargs["strength"] = float(self.strength)

        if self.enhance_prompt:
            llm_prompt = await get_enhanced_prompt(self.avernus_client, self.prompt)
            self.enhanced_prompt = llm_prompt
        if self.add_artist:
            random_artist_prompt = get_random_artist_prompt()
            self.enhanced_prompt = f"{random_artist_prompt}. {self.enhanced_prompt}"
        if self.add_danbooru_tags:
            danbooru_tags = get_generic_danbooru_tags("./assets/danbooru.csv", self.danbooru_tags_amount)
            self.enhanced_prompt = f"{self.enhanced_prompt}, {danbooru_tags}"

        try:
            response = await self.avernus_client.sana_sprint_image(self.enhanced_prompt, **kwargs)
            if response["status"] == "True" or response["status"] == True:
                self.status = "Finished"
                base64_images = response["images"]
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"SANA SPRINT REQUEST EXCEPTION: {e}")

class SanaSprintI2IRequest(SanaSprintRequest):
    def __init__(self, avernus_client: AvernusClient, gallery: ImageGallery, tabs: VerticalTabWidget, prompt: str,
                 width: str, height: str, steps: str, batch_size: str, guidance_scale: str, strength: float,
                 i2i_image_enabled: bool, i2i_image: QPixmap, enhance_prompt: bool, model_name: str, seed: str,
                 max_timesteps: str, intermediate_timesteps: str, add_artist: bool, add_danbooru_tags: bool,
                 danbooru_tags_amount: int):
        super().__init__(avernus_client, gallery, tabs, prompt, width, height, steps, batch_size, guidance_scale,
                         strength, i2i_image_enabled, i2i_image, enhance_prompt, model_name, seed, max_timesteps,
                         intermediate_timesteps, add_artist, add_danbooru_tags, danbooru_tags_amount)
