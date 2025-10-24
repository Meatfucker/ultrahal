import asyncio
import tempfile
import time
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QListWidget, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.ui_widgets import (ClickablePixmap, HorizontalSlider, ImageGallery, PainterWidget, ParagraphInputBox,
                                QueueObjectWidget, QueueViewer, SingleLineInputBox, VerticalTabWidget)
from modules.utils import base64_to_images, image_to_base64, get_generic_danbooru_tags, get_random_artist_prompt


class QwenImageInpaintTab(QWidget):
    def __init__(self, avernus_client: AvernusClient, tabs: VerticalTabWidget):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.paint_area = PainterWidget()

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
        self.enable_nunchaku_checkbox = QCheckBox("Enable Nunchaku")
        self.enable_nunchaku_checkbox.setChecked(True)
        self.steps_label = SingleLineInputBox("Steps:", placeholder_text="30")
        self.batch_size_label = SingleLineInputBox("Batch Size:", placeholder_text="4")
        self.true_cfg_scale_label = SingleLineInputBox("True CFG Scale:", placeholder_text="4.0")
        self.seed_label = SingleLineInputBox("Seed", placeholder_text="42")

        self.paint_layout = QVBoxLayout()
        self.config_layout = QVBoxLayout()
        self.config_widgets_layout = QVBoxLayout()
        self.config_widgets_layout.setAlignment(Qt.AlignTop)
        self.main_layout = QHBoxLayout()

        self.paint_layout.addWidget(self.paint_area)

        self.config_layout.addLayout(self.brush_size_slider)
        self.config_layout.addWidget(self.paste_button)
        self.config_layout.addWidget(self.load_button)
        self.config_layout.addLayout(self.strength_slider)
        self.config_layout.addWidget(self.clear_mask_button)
        self.config_layout.addWidget(self.lora_list)
        self.config_layout.addLayout(self.prompt_label)
        self.config_layout.addLayout(self.negative_prompt_label)
        self.config_layout.addLayout(self.config_widgets_layout)

        self.config_widgets_layout.addWidget(self.prompt_enhance_checkbox)
        self.config_widgets_layout.addWidget(self.add_random_artist_checkbox)
        self.config_widgets_layout.addWidget(self.add_random_danbooru_tags_checkbox)
        self.config_widgets_layout.addLayout(self.danbooru_tags_slider)
        self.config_widgets_layout.addWidget(self.enable_nunchaku_checkbox)
        self.config_widgets_layout.addLayout(self.steps_label)
        self.config_widgets_layout.addLayout(self.batch_size_label)
        self.config_widgets_layout.addLayout(self.true_cfg_scale_label)
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
        true_cfg_scale = self.true_cfg_scale_label.input.text()
        seed = self.seed_label.input.text()
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
        nunchaku_enabled = self.enable_nunchaku_checkbox.isChecked()
        width = self.paint_area.original_image.width()
        height = self.paint_area.original_image.height()
        strength = round(float(self.strength_slider.slider.value() * 0.01), 2)

        try:
            request = QwenInpaintRequest(avernus_client=self.avernus_client,
                                         gallery=self.gallery,
                                         tabs=self.tabs,
                                         prompt=prompt,
                                         negative_prompt=negative_prompt,
                                         steps=steps,
                                         batch_size=batch_size,
                                         true_cfg_scale=true_cfg_scale,
                                         seed=seed,
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
                                         nunchaku_enabled=nunchaku_enabled)
            queue_item = self.queue_view.add_queue_item(request, self.queue_view)
            request.ui_item = queue_item
            self.tabs.parent().pending_requests.append(request)
            self.tabs.parent().request_event.set()
        except Exception as e:
            print(f"QWEN IMAGE INPAINT on_submit EXCEPTION: {e}")

    def set_brush_size(self):
        self.paint_area.pen.setWidth(int(self.brush_size_slider.slider.value()))

    @asyncSlot()
    async def make_lora_list(self):
        self.lora_list.clear()
        loras = await self.avernus_client.list_qwen_image_loras()
        self.lora_list.insertItems(0, loras)


class QwenInpaintRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 prompt: str,
                 negative_prompt: str,
                 steps: str,
                 batch_size: str,
                 true_cfg_scale: str,
                 seed: str,
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
                 nunchaku_enabled: bool):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.enhanced_prompt = prompt
        self.negative_prompt = negative_prompt
        self.steps = steps
        self.batch_size = batch_size
        self.true_cfg_scale = true_cfg_scale
        self.seed = seed
        self.lora_name = lora_name
        self.enhance_prompt = enhance_prompt
        self.add_artist = add_artist
        self.add_danbooru_tags = add_danbooru_tags
        self.danbooru_tags_amount = danbooru_tags_amount
        self.nunchaku_enabled = nunchaku_enabled
        self.queue_info = None
        self.image = image
        self.mask_image = mask_image
        self.width = width
        self.height = height
        self.strength = strength
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"{self.width}x{self.height}, {self.lora_name},EP:{self.enhance_prompt}"

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.ui_item.status_label.setText(f"Finished\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        """API call to generate the images and convert them from base64"""
        print(f"QWEN INPAINT: {self.prompt}, {self.steps}, {self.batch_size}")

        kwargs = {}
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.batch_size != "": kwargs["batch_size"] = int(self.batch_size)
        if self.true_cfg_scale != "":kwargs["true_cfg_scale"] = float(self.true_cfg_scale)
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

        if self.enhance_prompt:
            llm_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            self.enhanced_prompt = llm_prompt
        if self.add_artist:
            random_artist_prompt = get_random_artist_prompt()
            self.enhanced_prompt = f"{random_artist_prompt}. {self.enhanced_prompt}"
        if self.add_danbooru_tags:
            danbooru_tags = get_generic_danbooru_tags("./assets/danbooru.csv", self.danbooru_tags_amount)
            self.enhanced_prompt = f"{self.enhanced_prompt}, {danbooru_tags}"

        try:
            if self.nunchaku_enabled:
                base64_images = await self.avernus_client.qwen_image_inpaint_nunchaku_image(self.enhanced_prompt, **kwargs)
            else:
                base64_images = await self.avernus_client.qwen_image_inpaint_image(self.enhanced_prompt, **kwargs)
            images = await base64_to_images(base64_images)
            await self.display_images(images)
        except Exception as e:
            print(f"QWEN IMAGE INPAINT EXCEPTION: {e}")


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