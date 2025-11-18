from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.gallery import GalleryTab
from modules.queue import QueueTab
from modules.ui_widgets import ImageGallery, QueueViewer, SingleLineInputBox, VerticalTabWidget
from modules.request_helpers import BaseAudioRequest, QueueObjectWidget


class ACETab(QWidget):
    def __init__(self,
                 avernus_client: AvernusClient,
                 tabs: VerticalTabWidget):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.gallery_tab: GalleryTab = cast(GalleryTab, self.tabs.named_widget("Gallery"))
        self.gallery: ImageGallery = self.gallery_tab.gallery
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view

        self.prompt_input = SingleLineInputBox("Prompt")
        self.lyrics_label = QLabel("Lyrics")
        self.lyrics_input = QTextEdit(acceptRichText=False)
        self.lyrics_input.setStyleSheet("""
             QTextEdit {
                 border: none;
                 background-color: #2c2c31;
                 color: #ddd;
                 font-size: 14px;
                 border: 2px solid solid;
                 border-color: #28282f;
                 border-radius: 8px; /* rounded corners */
             }
         """)
        self.length_input = SingleLineInputBox("Seconds", placeholder_text="60")
        self.steps_input = SingleLineInputBox("Steps", placeholder_text="27")
        self.guidance_scale_input = SingleLineInputBox("Guidance Scale", placeholder_text="15.0")
        self.omega_scale_input = SingleLineInputBox("Omega Scale", placeholder_text="10.0")
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
        input_layout = QVBoxLayout()
        config_layout = QVBoxLayout()
        config_layout.setAlignment(Qt.AlignTop)

        input_layout.addLayout(self.prompt_input)
        input_layout.addWidget(self.lyrics_label)
        input_layout.addWidget(self.lyrics_input)
        config_layout.addLayout(self.length_input)
        config_layout.addLayout(self.steps_input)
        config_layout.addLayout(self.guidance_scale_input)
        config_layout.addLayout(self.omega_scale_input)
        config_layout.addLayout(self.seed_input)
        config_layout.addStretch()
        config_layout.addWidget(self.submit_button)
        main_layout.addLayout(input_layout)
        main_layout.addLayout(config_layout)
        self.setLayout(main_layout)

    @asyncSlot()
    async def on_submit(self):
        prompt = self.prompt_input.input.text()
        lyrics = self.lyrics_input.toPlainText()
        length = self.length_input.input.text()
        steps = self.steps_input.input.text()
        guidance_scale = self.guidance_scale_input.input.text()
        omega_scale = self.omega_scale_input.input.text()
        seed = self.seed_input.input.text()

        request = ACERequest(self.avernus_client, self.gallery, self.tabs, prompt, lyrics, length, steps,
                             guidance_scale, omega_scale, seed)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view)
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class ACERequest(BaseAudioRequest):
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 prompt: str,
                 lyrics: str,
                 length: str,
                 steps: str,
                 guidance_scale: str,
                 omega_scale: str,
                 seed: str):
        super().__init__(avernus_client, gallery, tabs)
        self.status = None
        self.prompt: str = prompt
        self.lyrics: str = lyrics
        self.length: str = length
        self.steps: str = steps
        self.guidance_scale: str = guidance_scale
        self.omega_scale: str = omega_scale
        self.seed: str = seed
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = f"Duration:{self.length}s, Steps:{self.steps}, Guidance:{self.guidance_scale}, Omega:{self.omega_scale}"

    @asyncSlot()
    async def generate(self):
        print(f"ACE: {self.prompt}, {self.lyrics}, {self.length}")
        kwargs = {}
        kwargs["prompt"] = self.prompt
        kwargs["lyrics"] = self.lyrics
        if self.steps != "": kwargs["infer_step"] = int(self.steps)
        if self.length != "": kwargs["audio_duration"] = float(self.length)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.omega_scale != "": kwargs["omega_scale"] = float(self.omega_scale)
        if self.seed != "": kwargs["actual_seeds"] = int(self.seed)
        try:
            response = await self.avernus_client.ace_music(**kwargs)
            if response["status"] == "True" or response["status"] == True:
                self.status = "Finished"
                await self.display_audio(response["audio"])
            else:
                self.status = "Failed"
        except Exception as e:
            self.status = "Failed"
            print(f"ACE FAILURE: {e}")
