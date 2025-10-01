import asyncio
import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QApplication, QSizePolicy
from qasync import asyncSlot
from modules.ui_widgets import SingleLineInputBox, ClickableVideo, ResolutionInput, ImageInputBox, ModelPickerWidget
from modules.utils import base64_to_images, image_to_base64


class WanTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client = avernus_client
        self.tabs = tabs
        self.gallery_tab = self.tabs.widget(0)
        self.gallery = self.gallery_tab.gallery
        self.queue_tab = self.tabs.widget(1)
        self.queue_view = self.queue_tab.queue_view

        self.i2v_image_label = ImageInputBox(self, "i2v", "assets/chili.png")
        self.model_picker_t2v = ModelPickerWidget("wan_t2v", "T2V Model")
        self.model_picker_i2v = ModelPickerWidget("wan_i2v", "I2V Model")
        self.prompt_input = SingleLineInputBox("Prompt")
        self.negative_prompt_input = SingleLineInputBox("Negative Prompt")
        self.frames_input = SingleLineInputBox("Frames", placeholder_text="81")
        self.resolution_input = ResolutionInput(placeholder_x="832", placeholder_y="480")
        self.guidance_scale_input = SingleLineInputBox("Guidance Scale", placeholder_text="5.0")
        self.seed_input = SingleLineInputBox("Seed", placeholder_text="42")
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setMinimumSize(100, 40)
        self.submit_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.submit_button.setStyleSheet("""
                    QPushButton {
                        font-size: 20px;
                    }
                """)

        main_layout = QHBoxLayout()
        image_layout = QVBoxLayout()
        image_layout.setAlignment(Qt.AlignTop)
        input_layout = QVBoxLayout()
        input_layout.setAlignment(Qt.AlignTop)
        image_layout.addLayout(self.i2v_image_label)
        input_layout.addLayout(self.model_picker_t2v)
        input_layout.addLayout(self.model_picker_i2v)
        input_layout.addLayout(self.prompt_input)
        input_layout.addLayout(self.negative_prompt_input)
        input_layout.addLayout(self.frames_input)
        input_layout.addWidget(self.resolution_input)
        input_layout.addLayout(self.guidance_scale_input)
        input_layout.addLayout(self.seed_input)
        input_layout.addStretch()
        input_layout.addWidget(self.submit_button)

        main_layout.addLayout(image_layout)
        main_layout.addLayout(input_layout)
        self.setLayout(main_layout)

    @asyncSlot()
    async def on_submit(self):
        model_name_t2v = self.model_picker_t2v.model_list_picker.currentText()
        model_name_i2v = self.model_picker_i2v.model_list_picker.currentText()
        prompt = self.prompt_input.input.text()
        negative_prompt = self.negative_prompt_input.input.text()
        frames = self.frames_input.input.text()
        width = self.resolution_input.width_label.input.text()
        height = self.resolution_input.height_label.input.text()
        guidance_scale = self.guidance_scale_input.input.text()
        seed = self.seed_input.input.text()
        i2v_image_enable = self.i2v_image_label.enable_checkbox.isChecked()
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
                             width=width,
                             height=height,
                             guidance_scale=guidance_scale,
                             seed=seed,
                             i2v_image_enabled=i2v_image_enable,
                             i2v_image=i2v_image,
                             model_name=model_name
                             )

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#440066")
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class WanRequest:
    def __init__(self, avernus_client, gallery, tabs, prompt, negative_prompt, frames, width, height, guidance_scale,
                 seed, i2v_image_enabled, i2v_image, model_name):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.frames = frames
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.seed = seed
        self.i2v_image_enabled = i2v_image_enabled
        self.i2v_image = i2v_image
        self.model_name = model_name

        self.queue_info = f"I2I:{self.i2v_image_enabled}"

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        elapsed_time = time.time() - start_time
        self.ui_item.status_label.setText(f"Finished\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        print(f"WAN: {self.prompt}, {self.frames}")
        kwargs = {}
        kwargs["prompt"] = self.prompt
        if self.negative_prompt != "": kwargs["negative_prompt"] = str(self.negative_prompt)
        if self.frames != "": kwargs["num_frames"] = int(self.frames)
        if self.width != "": kwargs["width"] = float(self.width)
        if self.height != "": kwargs["height"] = float(self.height)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.seed != "": kwargs["seed"] = int(self.seed)
        if self.model_name != "" or None: kwargs["model_name"] = str(self.model_name)
        if self.i2v_image_enabled is True:
            self.i2v_image.save("temp.png", quality=100)
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
            image = image_to_base64("temp.png", i2v_width, i2v_height)
            kwargs["image"] = str(image)
        response = await self.avernus_client.wan_ti2v(**kwargs)
        await self.display_video(response)

    @asyncSlot()
    async def display_video(self, response):
        video_item = self.load_video_from_file(response)
        self.gallery.gallery.add_item(video_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    def load_video_from_file(self, video_path):
        return ClickableVideo(video_path, self.prompt)

