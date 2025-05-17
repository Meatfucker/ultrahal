import asyncio
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import  QApplication, QCheckBox, QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from qasync import asyncSlot
from modules.avernus_client import AvernusClient
from modules.ui_widgets import HorizontalSlider, ImageGallery, ImageInputBox, ParagraphInputBox, SingleLineInputBox
from modules.utils import base64_to_images, image_to_base64

class SdxlTab(QWidget):
    def __init__(self, avernus_client):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.generate_count = 0

        self.gallery = ImageGallery(self)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.prompt_label = ParagraphInputBox("Prompt")
        self.negative_prompt_label = ParagraphInputBox("Negative Prompt")
        self.lora_list = QComboBox()
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.width_label = SingleLineInputBox("Width:", placeholder_text="1024")
        self.height_label = SingleLineInputBox("Height:", placeholder_text="1024")
        self.steps_label = SingleLineInputBox("Steps:", placeholder_text="30")
        self.batch_size_label = SingleLineInputBox("Batch Size:", placeholder_text="4")
        self.i2i_image_label = ImageInputBox(self, "i2i", "assets/chili.png")
        self.i2i_strength_label = HorizontalSlider("Strength", 0, 100, 70, enable_ticks=False)
        self.ipadapter_image_label = ImageInputBox(self, "IP Adapter", "assets/chili.png")
        self.ipadapter_strength_label = HorizontalSlider("Strength", 0, 100, 60, enable_ticks=False)
        self.controlnet_image_label = ImageInputBox(self, "Controlnet", "assets/chili.png")
        self.controlnet_list = QComboBox()
        self.controlnet_conditioning_scale = HorizontalSlider("Strength", 0, 100, 50, enable_ticks=False)

        self.image_layout = QVBoxLayout()
        self.config_layout = QVBoxLayout()
        self.controlnet_layout = QVBoxLayout()
        self.main_layout = QHBoxLayout()

        self.image_layout.addLayout(self.gallery, stretch=5)
        self.config_layout.addLayout(self.prompt_label)
        self.config_layout.addLayout(self.negative_prompt_label)
        self.config_layout.addWidget(self.lora_list)
        self.config_layout.addWidget(self.prompt_enhance_checkbox)
        self.config_layout.addLayout(self.width_label)
        self.config_layout.addLayout(self.height_label)
        self.config_layout.addLayout(self.steps_label)
        self.config_layout.addLayout(self.batch_size_label)
        self.config_layout.addStrut(250)
        self.image_layout.addWidget(self.submit_button)
        self.controlnet_layout.addLayout(self.i2i_image_label)
        self.controlnet_layout.addLayout(self.i2i_strength_label)
        self.controlnet_layout.addLayout(self.ipadapter_image_label)
        self.controlnet_layout.addLayout(self.ipadapter_strength_label)
        self.controlnet_layout.addLayout(self.controlnet_image_label)
        self.controlnet_layout.addWidget(self.controlnet_list)
        self.controlnet_layout.addLayout(self.controlnet_conditioning_scale)
        self.main_layout.addLayout(self.image_layout, stretch=6)  # Left section
        self.main_layout.addLayout(self.config_layout, stretch=1)
        self.main_layout.addLayout(self.controlnet_layout, stretch=1)
        self.setLayout(self.main_layout)

    @asyncSlot()
    async def on_submit(self):
        self.generate_count = self.generate_count + 1
        self.submit_button.setText(f"Generating ({self.generate_count})")
        try:
            await self.generate()
        except Exception as e:
            print(f"SDXL on_submit EXCEPTION: {e}")
        self.generate_count = self.generate_count - 1
        if self.generate_count == 0:
            self.submit_button.setText("Submit")
        else:
            self.submit_button.setText(f"Generating ({self.generate_count})")
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    @asyncSlot()
    async def generate(self):
        """API call to generate the images and convert them from base64"""
        prompt = self.prompt_label.input.toPlainText()
        negative_prompt = self.negative_prompt_label.input.toPlainText()
        width = self.width_label.input.text()
        height = self.height_label.input.text()
        steps = self.steps_label.input.text()
        batch_size = self.batch_size_label.input.text()
        lora_name = self.lora_list.currentText()
        strength = round(float(self.i2i_strength_label.slider.value() * 0.01), 2)
        ip_adapter_strength = round(float(self.ipadapter_strength_label.slider.value() * 0.01), 2)
        controlnet_strength = round(float(self.controlnet_conditioning_scale.slider.value() * 0.01), 2)
        controlnet_processor = self.controlnet_list.currentText()
        print(f"SDXL: {prompt}, {negative_prompt}, {width}, {height}, {steps}, {batch_size}, {lora_name}, {strength}")

        kwargs = {}
        if negative_prompt != "": kwargs["negative_prompt"] = negative_prompt
        if steps != "": kwargs["steps"] = int(steps)
        if batch_size != "": kwargs["batch_size"] = int(batch_size)
        if lora_name != "<None>": kwargs["lora_name"] = str(lora_name)
        if width != "":
            kwargs["width"] = int(width)
        else:
            kwargs["width"] = 1024
        if height != "":
            kwargs["height"] = int(height)
        else:
            kwargs["height"] = 1024

        if self.i2i_image_label.enable_checkbox.isChecked():
            self.i2i_image_label.input_image.save("temp.png", quality=100)
            image = image_to_base64("temp.png", kwargs["width"], kwargs["height"])
            kwargs["image"] = str(image)
            if strength != "":
                kwargs["strength"] = float(strength)
        if self.ipadapter_image_label.enable_checkbox.isChecked():
            self.ipadapter_image_label.input_image.save("temp.png", quality=100)
            ip_adapter_image = image_to_base64("temp.png", kwargs["width"], kwargs["height"])
            kwargs["ip_adapter_image"] = str(ip_adapter_image)
            if ip_adapter_strength != "":
                kwargs["ip_adapter_strength"] = float(ip_adapter_strength)
        if self.controlnet_image_label.enable_checkbox.isChecked():
            self.controlnet_image_label.input_image.save("temp.png", quality=100)
            controlnet_image = image_to_base64("temp.png", kwargs["width"], kwargs["height"])
            kwargs["controlnet_image"] = str(controlnet_image)
            kwargs["controlnet_processor"] = str(controlnet_processor)
            if controlnet_strength != "":
                kwargs["controlnet_conditioning"] = float(controlnet_strength)

        if self.prompt_enhance_checkbox.isChecked():
            prompt = await self.avernus_client.llm_chat(f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {prompt}")

        try:
            base64_images = await self.avernus_client.sdxl_image(prompt, **kwargs)
            images = await base64_to_images(base64_images)
            await self.display_images(images)
        except Exception as e:
            print(f"SDXL EXCEPTION: {e}")

    @asyncSlot()
    async def display_images(self, images):
        if self.gallery.clear_gallery_checkbox.isChecked():
            self.gallery.gallery.gallery.clear()
        for image in images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.getvalue())
            self.gallery.gallery.add_pixmap(pixmap)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    @asyncSlot()
    async def make_lora_list(self):
        self.lora_list.clear()
        self.lora_list.addItem("<None>")
        loras = await self.avernus_client.list_sdxl_loras()
        for lora in loras:
            self.lora_list.addItem(lora)

    @asyncSlot()
    async def make_controlnet_list(self):
        self.controlnet_list.clear()
        controlnets = await self.avernus_client.list_sdxl_controlnets()
        for controlnet in controlnets:
            self.controlnet_list.addItem(controlnet)