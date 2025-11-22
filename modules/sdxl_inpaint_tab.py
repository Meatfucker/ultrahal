import tempfile
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QListWidget, QPushButton, QSizePolicy, QVBoxLayout,
                               QWidget)
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.request_helpers import BaseImageRequest, QueueObjectWidget
from modules.ui_widgets import (ImageGallery, HorizontalSlider, ModelPickerWidget, PainterWidget, ParagraphInputBox,
                                QueueViewer, SingleLineInputBox, VerticalTabWidget)
from modules.utils import base64_to_images, image_to_base64, get_random_artist_prompt, get_generic_danbooru_tags, get_enhanced_prompt


class SdxlInpaintTab(QWidget):
    def __init__(self, avernus_client: AvernusClient, tabs: VerticalTabWidget):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab = self.tabs.widget(0)
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.paint_area = PainterWidget()

        self.model_picker = ModelPickerWidget("sdxl")
        self.scheduler_list = QComboBox()
        self.clear_mask_button = QPushButton("Clear Mask")
        self.clear_mask_button.clicked.connect(self.paint_area.clear)
        self.brush_size_slider = HorizontalSlider("Brush Size", 1, 127, 10, enable_ticks=False)
        self.brush_size_slider.slider.valueChanged.connect(self.set_brush_size)
        self.paste_button = QPushButton("Paste Image")
        self.paste_button.clicked.connect(self.paint_area.paste_image)
        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.paint_area.load_image)
        self.strength_slider = HorizontalSlider("Replace %", 0, 100, 70, enable_ticks=False)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")
        self.prompt_label = ParagraphInputBox("Prompt")
        self.negative_prompt_label = ParagraphInputBox("Negative Prompt")
        self.lora_list = QListWidget()
        self.lora_list.setSelectionMode(QListWidget.MultiSelection)
        self.lora_list.setStyleSheet("""
             QListWidget {
                 border: none;
                 background-color: #2c2c31;
                 color: #ddd;
                 font-size: 14px;
                 border: 2px solid solid;
                 border-color: #28282f;
                 border-radius: 8px; /* rounded corners */
             }
         """)
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.add_random_artist_checkbox = QCheckBox("Add Random Artist")
        self.add_random_danbooru_tags_checkbox = QCheckBox("Add Random Danbooru Tags")
        self.danbooru_tags_slider = HorizontalSlider("Num Tags", 1, 20, 6, enable_ticks=False)
        self.steps_label = SingleLineInputBox("Steps:", placeholder_text="30")
        self.batch_size_label = SingleLineInputBox("Batch Size:", placeholder_text="4")
        self.guidance_scale_label = SingleLineInputBox("Guidance Scale:", placeholder_text="7.5")
        self.seed_label = SingleLineInputBox("Seed", placeholder_text="42")

        self.paint_layout = QVBoxLayout()
        self.config_layout = QVBoxLayout()
        self.config_widgets_layout = QVBoxLayout()
        self.config_widgets_layout.setAlignment(Qt.AlignTop)
        self.main_layout = QHBoxLayout()

        self.paint_layout.addWidget(self.paint_area)

        self.config_layout.addLayout(self.brush_size_slider)
        self.config_layout.addLayout(self.model_picker)
        self.config_layout.addWidget(self.scheduler_list)
        self.config_layout.addWidget(self.clear_mask_button)
        self.config_layout.addWidget(self.lora_list)
        self.config_layout.addWidget(self.paste_button)
        self.config_layout.addWidget(self.load_button)
        self.config_layout.addLayout(self.strength_slider)
        self.config_layout.addLayout(self.prompt_label)
        self.config_layout.addLayout(self.negative_prompt_label)
        self.config_layout.addLayout(self.config_widgets_layout)


        self.config_widgets_layout.addWidget(self.prompt_enhance_checkbox)
        self.config_widgets_layout.addWidget(self.add_random_artist_checkbox)
        self.config_widgets_layout.addWidget(self.add_random_danbooru_tags_checkbox)
        self.config_widgets_layout.addLayout(self.danbooru_tags_slider)
        self.config_widgets_layout.addLayout(self.steps_label)
        self.config_widgets_layout.addLayout(self.batch_size_label)
        self.config_widgets_layout.addLayout(self.guidance_scale_label)
        self.config_widgets_layout.addLayout(self.seed_label)
        self.config_widgets_layout.addWidget(self.submit_button)

        self.main_layout.addLayout(self.paint_layout, stretch=4)
        self.main_layout.addLayout(self.config_layout, stretch=1)
        self.setLayout(self.main_layout)

    @asyncSlot()
    async def on_submit(self):
        prompt = self.prompt_label.input.toPlainText()
        negative_prompt = self.negative_prompt_label.input.toPlainText()
        steps = self.steps_label.input.text()
        batch_size = self.batch_size_label.input.text()
        guidance_scale = self.guidance_scale_label.input.text()
        seed = self.seed_label.input.text()
        model_name = self.model_picker.model_list_picker.currentText()
        scheduler = self.scheduler_list.currentText()
        lora_items = self.lora_list.selectedItems()
        lora_name = "<None>"
        if lora_items:
            lora_name = []
            for lora_list_item in lora_items:
                lora_name.append(lora_list_item.text())
        enhance_prompt = self.prompt_enhance_checkbox.isChecked()
        add_artist = self.add_random_artist_checkbox.isChecked()
        add_danbooru_tags = self.add_random_danbooru_tags_checkbox.isChecked()
        danbooru_tags_amount = int(self.danbooru_tags_slider.slider.value())
        width = self.paint_area.original_image.width()
        height = self.paint_area.original_image.height()
        strength = round(float(self.strength_slider.slider.value() * 0.01), 2)

        try:
            request = SDXLInpaintRequest(avernus_client=self.avernus_client,
                                         gallery=self.gallery,
                                         tabs=self.tabs,
                                         prompt=prompt,
                                         negative_prompt=negative_prompt,
                                         steps=steps,
                                         batch_size=batch_size,
                                         guidance_scale=guidance_scale,
                                         lora_name=lora_name,
                                         enhance_prompt=enhance_prompt,
                                         add_artist=add_artist,
                                         add_danbooru_tags=add_danbooru_tags,
                                         danbooru_tags_amount=danbooru_tags_amount,
                                         width=width,
                                         height=height,
                                         image=self.paint_area.original_image,
                                         mask_image=self.paint_area.original_mask,
                                         strength=strength,
                                         model_name=model_name,
                                         scheduler=scheduler,
                                         seed=seed)
            queue_item = self.queue_view.add_queue_item(request, self.queue_view)
            request.ui_item = queue_item
            self.tabs.parent().pending_requests.append(request)
            self.tabs.parent().request_event.set()
        except Exception as e:
            print(f"SDXL INPAINT on_submit EXCEPTION: {e}")

    def set_brush_size(self):
        self.paint_area.pen.setWidth(int(self.brush_size_slider.slider.value()))

    @asyncSlot()
    async def make_lora_list(self):
        self.lora_list.clear()
        response = await self.avernus_client.list_sdxl_loras()
        if response["status"] is True:
            self.lora_list.insertItems(0, response["loras"])
        else:
            self.lora_list.insertItems(0, ["NONE"])

    @asyncSlot()
    async def make_scheduler_list(self):
        self.scheduler_list.clear()
        response = await self.avernus_client.list_sdxl_schedulers()
        if response["status"] is True:
            for scheduler in response["schedulers"]:
                self.scheduler_list.addItem(scheduler)
        else:
            self.scheduler_list.addItem("NONE")


class SDXLInpaintRequest(BaseImageRequest):
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 prompt: str,
                 negative_prompt: str,
                 steps: str,
                 batch_size: str,
                 guidance_scale: str,
                 enhance_prompt: bool,
                 add_artist: bool,
                 add_danbooru_tags: bool,
                 danbooru_tags_amount: int,
                 width: str,
                 height: str,
                 image: QPixmap,
                 mask_image: QPixmap,
                 strength: float,
                 lora_name: list,
                 model_name: str,
                 scheduler: str,
                 seed: str):
        super().__init__(avernus_client, gallery, tabs)
        self.status = None
        self.prompt = prompt
        self.enhanced_prompt = prompt
        self.negative_prompt = negative_prompt
        self.steps = steps
        self.batch_size = batch_size
        self.guidance_scale = guidance_scale
        self.model_name = model_name
        self.scheduler = scheduler
        self.lora_name = lora_name
        self.enhance_prompt = enhance_prompt
        self.add_artist = add_artist
        self.add_danbooru_tags = add_danbooru_tags
        self.danbooru_tags_amount = danbooru_tags_amount
        self.queue_info = None
        self.image = image
        self.mask_image = mask_image
        self.width = width
        self.height = height
        self.strength = strength
        self.seed = seed
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"{self.width}x{self.height}, {self.model_name}, {self.lora_name},EP:{self.enhance_prompt}"

    @asyncSlot()
    async def generate(self):
        """API call to generate the images and convert them from base64"""
        print(f"SDXL INPAINT: {self.prompt}, {self.negative_prompt}, {self.steps}, {self.batch_size}")

        kwargs = {}
        if self.negative_prompt != "": kwargs["negative_prompt"] = self.negative_prompt
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.batch_size != "": kwargs["batch_size"] = int(self.batch_size)
        if self.guidance_scale != "":kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.lora_name != "<None>": kwargs["lora_name"] = self.lora_name
        image_temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".png")
        self.image.save(image_temp_file.name, quality=100)
        image = image_to_base64(image_temp_file.name, self.width, self.height)
        kwargs["image"] = str(image)
        mask_temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".png")
        self.mask_image.save(mask_temp_file.name, quality=100)
        mask_image = image_to_base64(mask_temp_file.name, self.width, self.height)
        kwargs["mask_image"] = str(mask_image)
        kwargs["width"] = self.width
        kwargs["height"] = self.height
        kwargs["strength"] = self.strength
        kwargs["model_name"] = str(self.model_name)
        kwargs["scheduler"] = str(self.scheduler)

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
            response = await self.avernus_client.sdxl_inpaint_image(self.enhanced_prompt, **kwargs)
            if response["status"] == "True" or response["status"] == True:
                self.status = "Finished"
                base64_images = response["images"]
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"SDXL INPAINT EXCEPTION: {e}")
