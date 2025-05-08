from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox, QComboBox
from PySide6.QtGui import QPixmap
from qasync import asyncSlot
from modules.client import AvernusClient
from modules.ui_widgets import ImageGalleryViewer, ImageInputBox, ParagraphInputBox, SingleLineInputBox
from modules.utils import base64_to_images, image_to_base64

class Flux(QWidget):
    def __init__(self, avernus_client):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client

        self.gallery = ImageGalleryViewer()
        self.prompt_label = ParagraphInputBox("Prompt")
        self.i2i_image_label = ImageInputBox(self,"assets/chili.png", 250)
        self.i2i_strength_label = SingleLineInputBox("i2i Strength", placeholder_text="0.7")
        self.lora_list = QComboBox()
        self.width_label = SingleLineInputBox("Width:", placeholder_text="1024")
        self.height_label = SingleLineInputBox("Height:", placeholder_text="1024")
        self.steps_label = SingleLineInputBox("Steps:", placeholder_text="30")
        self.batch_size_label = SingleLineInputBox("Batch Size:", placeholder_text="4")
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)

        self.image_layout = QVBoxLayout()
        self.config_layout = QVBoxLayout()
        self.main_layout = QHBoxLayout()

        self.image_layout.addWidget(self.gallery, stretch=5)
        self.config_layout.addLayout(self.prompt_label)
        self.config_layout.addLayout(self.i2i_image_label)
        self.config_layout.addLayout(self.i2i_strength_label)
        self.config_layout.addWidget(self.lora_list)
        self.config_layout.addLayout(self.width_label)
        self.config_layout.addLayout(self.height_label)
        self.config_layout.addLayout(self.steps_label)
        self.config_layout.addLayout(self.batch_size_label)
        self.config_layout.addWidget(self.prompt_enhance_checkbox)
        self.config_layout.addWidget(self.submit_button)
        self.main_layout.addLayout(self.image_layout, stretch=5)  # Left section
        self.main_layout.addLayout(self.config_layout, stretch=1)
        self.setLayout(self.main_layout)

        self.make_lora_list()

    @asyncSlot()
    async def on_submit(self):
        self.submit_button.setText("Generating")
        self.submit_button.setDisabled(True)
        try:
            await self.generate()
        except Exception as e:
            print(f"Flux on_submit EXCEPTION: {e}")
        self.submit_button.setText("Submit")
        self.submit_button.setDisabled(False)

    async def generate(self):
        """API call to generate the images and convert them from base64"""
        prompt = self.prompt_label.input.toPlainText()
        width = self.width_label.input.text()
        height = self.height_label.input.text()
        steps = self.steps_label.input.text()
        batch_size = self.batch_size_label.input.text()
        lora_name = self.lora_list.currentText()
        strength = self.i2i_strength_label.input.text()

        kwargs = {}
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
            image = image_to_base64(self.i2i_image_label.image_file_path, kwargs["width"], kwargs["height"])
            kwargs["image"] = str(image)
            if strength != "":
                kwargs["strength"] = float(strength)
        if self.prompt_enhance_checkbox.isChecked():
            prompt = await self.avernus_client.llm_chat(f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {prompt}")

        try:
            base64_images = await self.avernus_client.flux_image(prompt, **kwargs)
            images = await base64_to_images(base64_images)
            await self.display_images(images)
        except Exception as e:
            print(f"Flux EXCEPTION: {e}")

    async def display_images(self, images):
        #self.gallery.gallery.clear()
        for image in images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.getvalue())
            self.gallery.add_pixmap(pixmap)
        self.gallery.tile_images()
        self.gallery.update()

    @asyncSlot()
    async def make_lora_list(self):
        self.lora_list.clear()
        self.lora_list.addItem("<None>")
        loras = await self.avernus_client.list_flux_loras()
        for lora in loras:
            self.lora_list.addItem(lora)