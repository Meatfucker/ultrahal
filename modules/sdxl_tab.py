import asyncio
import json
import random
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import  (QApplication, QCheckBox, QComboBox, QHBoxLayout, QListWidget, QListWidgetItem,
                                QPushButton, QVBoxLayout, QWidget)
from qasync import asyncSlot
from modules.avernus_client import AvernusClient
from modules.ui_widgets import HorizontalSlider, ImageInputBox, ModelPickerWidget, ParagraphInputBox, SingleLineInputBox
from modules.utils import base64_to_images, image_to_base64

class SdxlTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs = tabs
        self.gallery_tab = self.tabs.widget(0)
        self.gallery = self.gallery_tab.gallery
        self.queue_tab = self.tabs.widget(1)
        self.queue_view = self.queue_tab.queue_view

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.prompt_label = ParagraphInputBox("Prompt")
        self.negative_prompt_label = ParagraphInputBox("Negative Prompt")
        self.model_picker = ModelPickerWidget("sdxl")
        self.scheduler_list = QComboBox()
        self.lora_list = QListWidget()
        self.lora_list.setSelectionMode(QListWidget.MultiSelection)
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.add_random_artist_checkbox = QCheckBox("Add Random Artist")
        self.width_label = SingleLineInputBox("Width:", placeholder_text="1024")
        self.height_label = SingleLineInputBox("Height:", placeholder_text="1024")
        self.steps_label = SingleLineInputBox("Steps:", placeholder_text="30")
        self.batch_size_label = SingleLineInputBox("Batch Size:", placeholder_text="4")
        self.guidance_scale_label = SingleLineInputBox("Guidance Scale:", placeholder_text="5.0")
        self.seed_label = SingleLineInputBox("Seed", placeholder_text="42")

        self.i2i_image_label = ImageInputBox(self, "i2i", "assets/chili.png")
        self.i2i_strength_label = HorizontalSlider("Strength", 0, 100, 70, enable_ticks=False)
        self.ipadapter_image_label = ImageInputBox(self, "IP Adapter", "assets/chili.png")
        self.ipadapter_strength_label = HorizontalSlider("Strength", 0, 100, 60, enable_ticks=False)
        self.controlnet_image_label = ImageInputBox(self, "Controlnet", "assets/chili.png")
        self.controlnet_list = QComboBox()
        self.controlnet_conditioning_scale = HorizontalSlider("Strength", 0, 100, 50, enable_ticks=False)

        self.main_layout = QHBoxLayout()
        self.input_layout = QVBoxLayout()
        self.prompt_layout = QHBoxLayout()
        self.config_widgets_layout = QVBoxLayout()
        self.config_widgets_layout.setAlignment(Qt.AlignTop)
        self.image_input_layout = QHBoxLayout()
        self.i2i_layout = QVBoxLayout()
        self.ip_adapter_layout = QVBoxLayout()
        self.controlnet_layout = QVBoxLayout()

        self.prompt_layout.addLayout(self.prompt_label)
        self.prompt_layout.addLayout(self.negative_prompt_label)

        self.config_widgets_layout.addLayout(self.model_picker)
        self.config_widgets_layout.addWidget(self.scheduler_list)
        self.config_widgets_layout.addWidget(self.lora_list)
        self.config_widgets_layout.addWidget(self.prompt_enhance_checkbox)
        self.config_widgets_layout.addWidget(self.add_random_artist_checkbox)
        self.config_widgets_layout.addLayout(self.width_label)
        self.config_widgets_layout.addLayout(self.height_label)
        self.config_widgets_layout.addLayout(self.steps_label)
        self.config_widgets_layout.addLayout(self.batch_size_label)
        self.config_widgets_layout.addLayout(self.guidance_scale_label)
        self.config_widgets_layout.addLayout(self.seed_label)
        self.config_widgets_layout.addWidget(self.submit_button)

        self.image_input_layout.addLayout(self.i2i_layout)
        self.image_input_layout.addLayout(self.ip_adapter_layout)
        self.image_input_layout.addLayout(self.controlnet_layout)

        self.i2i_layout.addLayout(self.i2i_image_label)
        self.i2i_layout.addLayout(self.i2i_strength_label)
        self.ip_adapter_layout.addLayout(self.ipadapter_image_label)
        self.ip_adapter_layout.addLayout(self.ipadapter_strength_label)
        self.controlnet_layout.addLayout(self.controlnet_image_label)
        self.controlnet_layout.addWidget(self.controlnet_list)
        self.controlnet_layout.addLayout(self.controlnet_conditioning_scale)

        self.input_layout.addLayout(self.prompt_layout, stretch=1)
        self.input_layout.addLayout(self.image_input_layout, stretch=1)

        self.main_layout.addLayout(self.input_layout)
        self.main_layout.addLayout(self.config_widgets_layout)
        self.setLayout(self.main_layout)

    @asyncSlot()
    async def on_submit(self):
        prompt = self.prompt_label.input.toPlainText()
        negative_prompt = self.negative_prompt_label.input.toPlainText()
        width = self.width_label.input.text()
        height = self.height_label.input.text()
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

        strength = round(float(self.i2i_strength_label.slider.value() * 0.01), 2)
        ip_adapter_strength = round(float(self.ipadapter_strength_label.slider.value() * 0.01), 2)
        controlnet_strength = round(float(self.controlnet_conditioning_scale.slider.value() * 0.01), 2)
        controlnet_processor = self.controlnet_list.currentText()
        i2i_image_enable = self.i2i_image_label.enable_checkbox.isChecked()
        if i2i_image_enable is True:
            i2i_image = self.i2i_image_label.input_image
        else:
            i2i_image = None
        ip_adapter_enable = self.ipadapter_image_label.enable_checkbox.isChecked()
        if ip_adapter_enable is True:
            ip_adapter_image = self.ipadapter_image_label.input_image
        else:
            ip_adapter_image = None
        controlnet_enable = self.controlnet_image_label.enable_checkbox.isChecked()
        if controlnet_enable is True:
            controlnet_image = self.controlnet_image_label.input_image
        else:
            controlnet_image = None
        enhance_prompt = self.prompt_enhance_checkbox.isChecked()
        add_artist = self.add_random_artist_checkbox.isChecked()

        try:
            request = SDXLRequest(avernus_client=self.avernus_client,
                                  gallery=self.gallery,
                                  tabs=self.tabs,
                                  prompt=prompt,
                                  negative_prompt=negative_prompt,
                                  width=width,
                                  height=height,
                                  steps=steps,
                                  batch_size=batch_size,
                                  guidance_scale=guidance_scale,
                                  lora_name=lora_name,
                                  strength=strength,
                                  ip_adapter_strength=ip_adapter_strength,
                                  controlnet_strength=controlnet_strength,
                                  controlnet_processor=controlnet_processor,
                                  i2i_image_enabled=i2i_image_enable,
                                  i2i_image=i2i_image,
                                  ip_adapter_enabled=ip_adapter_enable,
                                  ip_adapter_image=ip_adapter_image,
                                  controlnet_enabled=controlnet_enable,
                                  controlnet_image=controlnet_image,
                                  enhance_prompt=enhance_prompt,
                                  add_artist=add_artist,
                                  model_name=model_name,
                                  scheduler=scheduler,
                                  seed=seed)
            queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#1E3A5F")
            request.ui_item = queue_item
            self.tabs.parent().pending_requests.append(request)
            self.tabs.parent().request_event.set()
        except Exception as e:
            print(f"SDXL on_submit EXCEPTION: {e}")

    @asyncSlot()
    async def make_lora_list(self):
        self.lora_list.clear()
        loras = await self.avernus_client.list_sdxl_loras()
        self.lora_list.insertItems(0, loras)

    @asyncSlot()
    async def make_controlnet_list(self):
        self.controlnet_list.clear()
        controlnets = await self.avernus_client.list_sdxl_controlnets()
        for controlnet in controlnets:
            self.controlnet_list.addItem(controlnet)

    @asyncSlot()
    async def make_scheduler_list(self):
        self.scheduler_list.clear()
        schedulers = await self.avernus_client.list_sdxl_schedulers()
        for scheduler in schedulers:
            self.scheduler_list.addItem(scheduler)

class SDXLRequest:
    def __init__(self, avernus_client, gallery, tabs, prompt, negative_prompt, width, height, steps, batch_size,
                 lora_name, guidance_scale, strength, ip_adapter_strength, controlnet_strength, controlnet_processor,
                 i2i_image_enabled, i2i_image, ip_adapter_enabled, ip_adapter_image, controlnet_enabled,
                 controlnet_image, enhance_prompt, model_name, scheduler, seed, add_artist):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.width = width
        self.height = height
        self.steps = steps
        self.batch_size = batch_size
        self.guidance_scale = guidance_scale
        self.seed = seed
        self.model_name = model_name
        self.scheduler = scheduler
        self.lora_name = lora_name
        self.strength = strength
        self.ip_adapter_strength = ip_adapter_strength
        self.controlnet_strength = controlnet_strength
        self.controlnet_processor = controlnet_processor
        self.i2i_image_enabled = i2i_image_enabled
        self.i2i_image = i2i_image
        self.ip_adapter_enabled = ip_adapter_enabled
        self.ip_adapter_image = ip_adapter_image
        self.controlnet_enabled = controlnet_enabled
        self.controlnet_image = controlnet_image
        self.enhance_prompt = enhance_prompt
        self.add_artist = add_artist
        if self.width == "":
            self.width = 1024
        if self.height == "":
            self.height = 1024
        self.queue_info = f"{self.width}x{self.height}, {self.model_name}, {self.lora_name},EP:{self.enhance_prompt},I2I:{self.i2i_image_enabled},IPA:{self.ip_adapter_enabled},CN:{self.controlnet_enabled}"

    async def run(self):
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        self.ui_item.status_label.setText("Finished")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")


    @asyncSlot()
    async def generate(self):
        """API call to generate the images and convert them from base64"""
        print(f"SDXL: {self.prompt}, {self.negative_prompt}, {self.width}, {self.height}, {self.steps}, {self.batch_size}, {self.lora_name}, {self.strength}")

        kwargs = {}
        if self.negative_prompt != "": kwargs["negative_prompt"] = self.negative_prompt
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.batch_size != "": kwargs["batch_size"] = int(self.batch_size)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.lora_name != "<None>": kwargs["lora_name"] = self.lora_name
        kwargs["model_name"] = str(self.model_name)
        kwargs["scheduler"] = str(self.scheduler)
        kwargs["width"] = int(self.width)
        kwargs["height"] = int(self.height)

        if self.i2i_image_enabled is True:
            self.i2i_image.save("temp.png", quality=100)
            image = image_to_base64("temp.png", kwargs["width"], kwargs["height"])
            kwargs["image"] = str(image)
            if self.strength != "":
                kwargs["strength"] = float(self.strength)
        if self.ip_adapter_enabled is True:
            self.ip_adapter_image.save("temp.png", quality=100)
            ip_adapter_image = image_to_base64("temp.png", kwargs["width"], kwargs["height"])
            kwargs["ip_adapter_image"] = str(ip_adapter_image)
            if self.ip_adapter_strength != "":
                kwargs["ip_adapter_strength"] = float(self.ip_adapter_strength)
        if self.controlnet_enabled is True:
            self.controlnet_image.save("temp.png", quality=100)
            controlnet_image = image_to_base64("temp.png", kwargs["width"], kwargs["height"])
            kwargs["controlnet_image"] = str(controlnet_image)
            kwargs["controlnet_processor"] = str(self.controlnet_processor)
            if self.controlnet_strength != "":
                kwargs["controlnet_conditioning"] = float(self.controlnet_strength)

        if self.enhance_prompt is True:
            self.enhanced_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            if self.add_artist is True:
                random_artist_prompt = await self.get_random_artist_prompt()
                self.enhanced_prompt = f"{random_artist_prompt}. {self.enhanced_prompt}"
            try:
                base64_images = await self.avernus_client.sdxl_image(self.enhanced_prompt, **kwargs)
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            except Exception as e:
                print(f"SDXL EXCEPTION: {e}")
        else:
            if self.add_artist is True:
                random_artist_prompt = await self.get_random_artist_prompt()
                self.prompt = f"{random_artist_prompt}. {self.prompt}"
            try:
                base64_images = await self.avernus_client.sdxl_image(self.prompt, **kwargs)
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            except Exception as e:
                print(f"SDXL EXCEPTION: {e}")

    @asyncSlot()
    async def display_images(self, images):
        for image in images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.getvalue())
            self.gallery.gallery.add_pixmap(pixmap, self.tabs)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    @asyncSlot()
    async def get_random_artist_prompt(self):
        with open('assets/artist.json', 'r') as file:
            data = json.load(file)
            selected_artist = random.choice(data)
            return selected_artist.get('prompt')