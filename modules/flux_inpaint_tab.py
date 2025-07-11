import asyncio

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import  QApplication, QCheckBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget, QListWidget
from qasync import asyncSlot
from modules.avernus_client import AvernusClient
from modules.ui_widgets import PainterWidget, ParagraphInputBox, SingleLineInputBox, HorizontalSlider, ClickablePixmap
from modules.utils import base64_to_images, image_to_base64

class FluxInpaintTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs = tabs
        self.gallery_tab = self.tabs.widget(0)
        self.gallery = self.gallery_tab.gallery
        self.queue_tab = self.tabs.widget(1)
        self.queue_view = self.queue_tab.queue_view

        self.paint_area = PainterWidget()

        self.clear_mask_button = QPushButton("Clear Mask")
        self.clear_mask_button.clicked.connect(self.paint_area.clear)
        self.brush_size_slider = HorizontalSlider("Brush Size", 1, 200, 10, enable_ticks=False)
        self.brush_size_slider.slider.valueChanged.connect(self.set_brush_size)
        self.load_button = QPushButton("Load Image")
        self.load_button.clicked.connect(self.paint_area.load_image)
        self.strength_slider = HorizontalSlider("Replace %", 0, 100, 70, enable_ticks=False)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.prompt_label = ParagraphInputBox("Prompt")
        self.lora_list = QListWidget()
        self.lora_list.setSelectionMode(QListWidget.MultiSelection)
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.steps_label = SingleLineInputBox("Steps:", placeholder_text="30")
        self.batch_size_label = SingleLineInputBox("Batch Size:", placeholder_text="4")
        self.guidance_scale_label = SingleLineInputBox("Guidance Scale:", placeholder_text="7.0")
        self.seed_label = SingleLineInputBox("Seed", placeholder_text="42")

        self.paint_layout = QVBoxLayout()
        self.config_layout = QVBoxLayout()
        self.config_widgets_layout = QVBoxLayout()
        self.config_widgets_layout.setAlignment(Qt.AlignTop)
        self.main_layout = QHBoxLayout()

        self.paint_layout.addWidget(self.paint_area)

        self.config_layout.addLayout(self.brush_size_slider)
        self.config_layout.addWidget(self.load_button)
        self.config_layout.addLayout(self.strength_slider)
        self.config_layout.addWidget(self.clear_mask_button)
        self.config_layout.addWidget(self.lora_list)
        self.config_layout.addLayout(self.prompt_label)
        self.config_layout.addLayout(self.config_widgets_layout)

        self.config_widgets_layout.addWidget(self.prompt_enhance_checkbox)
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
        steps = self.steps_label.input.text()
        batch_size = self.batch_size_label.input.text()
        guidance_scale = self.guidance_scale_label.input.text()
        seed = self.seed_label.input.text()
        lora_items = self.lora_list.selectedItems()
        lora_name = "<None>"
        if lora_items:
            lora_name = []
            for lora_list_item in lora_items:
                lora_name.append(lora_list_item.text())
        enhance_prompt = self.prompt_enhance_checkbox.isChecked()
        width = self.paint_area.original_image.width()
        height = self.paint_area.original_image.height()
        strength = round(float(self.strength_slider.slider.value() * 0.01), 2)

        try:
            request = FluxInpaintRequest(avernus_client=self.avernus_client,
                                         gallery=self.gallery,
                                         tabs=self.tabs,
                                         prompt=prompt,
                                         steps=steps,
                                         batch_size=batch_size,
                                         guidance_scale=guidance_scale,
                                         seed=seed,
                                         lora_name=lora_name,
                                         enhance_prompt=enhance_prompt,
                                         width=width,
                                         height=height,
                                         image=self.paint_area.original_image,
                                         mask_image=self.paint_area.original_mask,
                                         strength=strength)
            queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#2F2452")
            request.ui_item = queue_item
            self.tabs.parent().pending_requests.append(request)
            self.tabs.parent().request_event.set()
        except Exception as e:
            print(f"FLUX INPAINT on_submit EXCEPTION: {e}")

    def set_brush_size(self):
        self.paint_area.pen.setWidth(int(self.brush_size_slider.slider.value()))

    @asyncSlot()
    async def make_lora_list(self):
        self.lora_list.clear()
        loras = await self.avernus_client.list_flux_loras()
        self.lora_list.insertItems(0, loras)

class FluxInpaintRequest:
    def __init__(self, avernus_client, gallery, tabs, prompt, steps, batch_size, guidance_scale, seed,
                 enhance_prompt, width, height, image, mask_image, strength, lora_name):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.steps = steps
        self.batch_size = batch_size
        self.guidance_scale = guidance_scale
        self.seed = seed
        self.lora_name = lora_name
        self.enhance_prompt = enhance_prompt
        self.queue_info = None
        self.image = image
        self.mask_image = mask_image
        self.width = width
        self.height = height
        self.strength = strength
        self.queue_info = f"{self.width}x{self.height}, {self.lora_name},EP:{self.enhance_prompt}"

    async def run(self):
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        self.ui_item.status_label.setText("Finished")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")


    @asyncSlot()
    async def generate(self):
        """API call to generate the images and convert them from base64"""
        print(f"FLUX INPAINT: {self.prompt}, {self.steps}, {self.batch_size}")

        kwargs = {}
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.batch_size != "": kwargs["batch_size"] = int(self.batch_size)
        if self.guidance_scale != "":kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.lora_name != "<None>": kwargs["lora_name"] = self.lora_name
        self.image.save("temp.png", quality=100)
        image = image_to_base64("temp.png", self.width, self.height)
        kwargs["image"] = str(image)
        self.mask_image.save("temp.png", quality=100)
        mask_image = image_to_base64("temp.png", self.width, self.height)
        kwargs["mask_image"] = str(mask_image)
        kwargs["width"] = self.width
        kwargs["height"] = self.height
        kwargs["strength"] = self.strength

        if self.enhance_prompt is True:
            self.enhanced_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            try:
                base64_images = await self.avernus_client.flux_inpaint_image(self.enhanced_prompt, **kwargs)
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            except Exception as e:
                print(f"FLUX INPAINT EXCEPTION: {e}")
        else:
            try:
                base64_images = await self.avernus_client.flux_inpaint_image(self.prompt, **kwargs)
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            except Exception as e:
                print(f"FLUX INPAINT EXCEPTION: {e}")

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