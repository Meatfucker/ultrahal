import asyncio
import tempfile
import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QApplication, QSizePolicy
from qasync import asyncSlot
from modules.ui_widgets import SingleLineInputBox, ClickableAudio


class ACETab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client = avernus_client
        self.tabs = tabs
        self.gallery_tab = self.tabs.widget(0)
        self.gallery = self.gallery_tab.gallery
        self.queue_tab = self.tabs.widget(1)
        self.queue_view = self.queue_tab.queue_view

        self.prompt_input = SingleLineInputBox("Prompt")
        self.lyrics_label = QLabel("Lyrics")
        self.lyrics_input = QTextEdit(acceptRichText=False)
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
                        padding: 15px;
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

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#1F2507")
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()


class ACERequest:
    def __init__(self, avernus_client, gallery, tabs, prompt, lyrics, length, steps, guidance_scale, omega_scale, seed):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.prompt = prompt
        self.lyrics = lyrics
        self.length = length
        self.steps = steps
        self.guidance_scale = guidance_scale
        self.omega_scale = omega_scale
        self.seed = seed

        self.queue_info = None

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
        print(f"ACE: {self.prompt}, {self.lyrics}, {self.length}")
        kwargs = {}
        kwargs["prompt"] = self.prompt
        kwargs["lyrics"] = self.lyrics
        if self.steps != "": kwargs["infer_step"] = int(self.steps)
        if self.length != "": kwargs["audio_duration"] = float(self.length)
        if self.guidance_scale != "": kwargs["guidance_scale"] = float(self.guidance_scale)
        if self.omega_scale != "": kwargs["omega_scale"] = float(self.omega_scale)
        if self.seed != "": kwargs["actual_seeds"] = int(self.seed)

        response = await self.avernus_client.ace_music(**kwargs)
        await self.display_audio(response)

    @asyncSlot()
    async def display_audio(self, response):
        audio_item = self.load_audio_from_bytes(response)
        self.gallery.gallery.add_item(audio_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    def load_audio_from_bytes(self, audio_bytes):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            return ClickableAudio(f.name, self.prompt, self.lyrics, self.gallery.gallery)

