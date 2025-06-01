import asyncio
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import  QApplication, QCheckBox, QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from qasync import asyncSlot
from modules.avernus_client import AvernusClient
from modules.ui_widgets import HorizontalSlider, ImageInputBox, ParagraphInputBox, SingleLineInputBox
from modules.utils import base64_to_images, image_to_base64

class FluxTab(QWidget):
    def __init__(self, avernus_client, request_queue, tabs):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.request_queue = request_queue
        self.tabs = tabs
        self.gallery_tab = self.tabs.widget(0)
        self.gallery = self.gallery_tab.gallery
        self.queue_tab = self.tabs.widget(1)
        self.queue_view = self.queue_tab.queue_view

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.prompt_label = ParagraphInputBox("Prompt")
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

        self.config_layout = QHBoxLayout()
        self.config_widgets_layout = QVBoxLayout()
        self.config_widgets_layout.setAlignment(Qt.AlignTop)
        self.image_input_layout = QHBoxLayout()
        self.i2i_layout = QVBoxLayout()
        self.ip_adapter_layout = QVBoxLayout()
        self.controlnet_layout = QVBoxLayout()
        self.main_layout = QVBoxLayout()

        self.config_layout.addLayout(self.prompt_label)
        self.config_layout.addLayout(self.config_widgets_layout)

        self.config_widgets_layout.addWidget(self.lora_list)
        self.config_widgets_layout.addWidget(self.prompt_enhance_checkbox)
        self.config_widgets_layout.addLayout(self.width_label)
        self.config_widgets_layout.addLayout(self.height_label)
        self.config_widgets_layout.addLayout(self.steps_label)
        self.config_widgets_layout.addLayout(self.batch_size_label)
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

        self.main_layout.addLayout(self.config_layout, stretch=1)
        self.main_layout.addLayout(self.image_input_layout, stretch=1)
        self.setLayout(self.main_layout)

    @asyncSlot()
    async def on_submit(self):
        prompt = self.prompt_label.input.toPlainText()
        width = self.width_label.input.text()
        height = self.height_label.input.text()
        steps = self.steps_label.input.text()
        batch_size = self.batch_size_label.input.text()
        lora_name = self.lora_list.currentText()
        strength = round(float(self.i2i_strength_label.slider.value() * 0.01), 2)
        ip_adapter_strength = round(float(self.ipadapter_strength_label.slider.value() * 0.01), 2)
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

        try:
            request = FluxRequest(avernus_client=self.avernus_client,
                                  gallery=self.gallery,
                                  tabs=self.tabs,
                                  prompt=prompt,
                                  width=width,
                                  height=height,
                                  steps=steps,
                                  batch_size=batch_size,
                                  lora_name=lora_name,
                                  strength=strength,
                                  ip_adapter_strength=ip_adapter_strength,
                                  controlnet_processor=controlnet_processor,
                                  i2i_image_enabled=i2i_image_enable,
                                  i2i_image=i2i_image,
                                  ip_adapter_enabled=ip_adapter_enable,
                                  ip_adapter_image=ip_adapter_image,
                                  controlnet_enabled=controlnet_enable,
                                  controlnet_image=controlnet_image,
                                  enhance_prompt=enhance_prompt)
            queue_item = self.queue_view.add_queue_item(request, self.request_queue, self.queue_view, "#000055")
            request.ui_item = queue_item
            await self.request_queue.put(request)
        except Exception as e:
            print(f"SDXL on_submit EXCEPTION: {e}")

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

class FluxRequest:
    def __init__(self, avernus_client, gallery, tabs, prompt, width, height, steps, batch_size, lora_name,
                 strength, ip_adapter_strength, controlnet_processor, i2i_image_enabled,
                 i2i_image, ip_adapter_enabled, ip_adapter_image, controlnet_enabled, controlnet_image, enhance_prompt):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.width = width
        self.height = height
        self.steps = steps
        self.batch_size = batch_size
        self.lora_name = lora_name
        self.strength = strength
        self.ip_adapter_strength = ip_adapter_strength
        self.controlnet_processor = controlnet_processor
        self.i2i_image_enabled = i2i_image_enabled
        self.i2i_image = i2i_image
        self.ip_adapter_enabled = ip_adapter_enabled
        self.ip_adapter_image = ip_adapter_image
        self.controlnet_enabled = controlnet_enabled
        self.controlnet_image = controlnet_image
        self.enhance_prompt = enhance_prompt

    async def run(self):
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        self.ui_item.status_label.setText("Finished")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")


    @asyncSlot()
    async def generate(self):
        """API call to generate the images and convert them from base64"""
        print(f"FLUX: {self.prompt}, {self.width}, {self.height}, {self.steps}, {self.batch_size}, {self.lora_name}, {self.strength}")

        kwargs = {}
        if self.steps != "": kwargs["steps"] = int(self.steps)
        if self.batch_size != "": kwargs["batch_size"] = int(self.batch_size)
        if self.lora_name != "<None>": kwargs["lora_name"] = str(self.lora_name)
        if self.width != "":
            kwargs["width"] = int(self.width)
        else:
            kwargs["width"] = 1024
        if self.height != "":
            kwargs["height"] = int(self.height)
        else:
            kwargs["height"] = 1024

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

        if self.enhance_prompt is True:
            self.enhanced_prompt = await self.avernus_client.llm_chat(
                f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {self.prompt}")
            try:
                base64_images = await self.avernus_client.flux_image(self.enhanced_prompt, **kwargs)
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            except Exception as e:
                print(f"FLUX EXCEPTION: {e}")
        else:
            try:
                base64_images = await self.avernus_client.flux_image(self.prompt, **kwargs)
                images = await base64_to_images(base64_images)
                await self.display_images(images)
            except Exception as e:
                print(f"FLUX EXCEPTION: {e}")

    @asyncSlot()
    async def display_images(self, images):
        if self.gallery.clear_gallery_checkbox.isChecked():
            self.gallery.gallery.gallery.clear()
        for image in images:
            pixmap = QPixmap()
            pixmap.loadFromData(image.getvalue())
            self.gallery.gallery.add_pixmap(pixmap, self.tabs)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()