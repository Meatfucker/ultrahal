import asyncio
import shutil
import tempfile
import time

from pydub import AudioSegment
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QPushButton, QGraphicsPixmapItem, QLabel, QMenu,
                               QFileDialog, QSlider, QWidget, QFrame, QSizePolicy, QGraphicsProxyWidget, QPlainTextEdit,
                               QStyle, QGraphicsWidget)
from PySide6.QtGui import (QPixmap, QIcon)
from PySide6.QtCore import Qt, QSize, QSizeF, QUrl, QMimeData, QRectF
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.ui_widgets import ImageGallery, SelectableMessageBox, show_context_menu, VerticalTabWidget




class BaseAudioRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 ):
        self.avernus_client: AvernusClient = avernus_client
        self.gallery: ImageGallery = gallery
        self.tabs = tabs
        self.status = None
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = ""
        self.prompt = ""
        self.lyrics = ""

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        elapsed_time = time.time() - start_time
        self.ui_item.status_label.setText(f"{self.status}\n{elapsed_time:.2f}s")
        if self.status == "Failed":
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #000000;")
        else:
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        pass

    @asyncSlot()
    async def display_audio(self, response):
        audio_item = self.load_audio_from_bytes(response)
        self.gallery.gallery.add_item(audio_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    def load_audio_from_bytes(self, audio_bytes):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_bytes)
            f.flush()
            return ClickableAudio(f.name, self.prompt, self.lyrics)

class BaseImageRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 ):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.status = None
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = ""

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.ui_item.status_label.setText(f"{self.status}\n{elapsed_time:.2f}s")
        if self.status == "Failed":
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #000000;")
        else:
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        pass

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

class BaseTextRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 tab,
                 ):
        self.avernus_client = avernus_client
        self.tab = tab
        self.status = None
        self.queue_info = None
        self.ui_item: QueueObjectWidget | None = None

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.ui_item.status_label.setText(f"{self.status}\n{elapsed_time:.2f}s")
        if self.status == "Failed":
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #000000;")
        else:
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    async def generate(self):
        pass


class BaseVideoRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 gallery: ImageGallery,
                 tabs: VerticalTabWidget,
                 ):
        self.avernus_client = avernus_client
        self.gallery = gallery
        self.tabs = tabs
        self.status = None
        self.ui_item: QueueObjectWidget | None = None
        self.queue_info = None

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        elapsed_time = time.time() - start_time
        self.ui_item.status_label.setText(f"{self.status}\n{elapsed_time:.2f}s")
        if self.status == "Failed":
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #000000;")
        else:
            self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    @asyncSlot()
    async def generate(self):
        pass

    @asyncSlot()
    async def display_video(self, response):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_file.write(response)
        temp_file.close()
        video_item = self.load_video_from_file(temp_file.name)
        self.gallery.gallery.add_item(video_item)
        self.gallery.gallery.tile_images()
        self.gallery.update()
        await asyncio.sleep(0)  # Let the event loop breathe
        QApplication.processEvents()

    def load_video_from_file(self, video_path):
        return ClickableVideo(video_path, self.prompt)

class ClickableAudio(QGraphicsProxyWidget):
    def __init__(self, audio_path: str, prompt: str, lyrics: str):
        super().__init__()
        self.audio_path: str = audio_path
        self.prompt: str = prompt
        self.lyrics: str = lyrics

        widget = QWidget()
        layout = QVBoxLayout()

        self.prompt_label = QLabel("Prompt:")
        self.prompt_display = QPlainTextEdit(readOnly=True)
        self.prompt_display.setPlainText(prompt)
        self.prompt_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.prompt_display.setMaximumHeight(50)
        self.lyrics_label = QLabel("Lyrics:")
        self.lyrics_display = QPlainTextEdit(readOnly=True)
        self.lyrics_display.setPlainText(lyrics)
        self.lyrics_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.lyrics_display.setMaximumHeight(100)
        self.lyrics_display.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setEnabled(False)
        self.time_label = QLabel("0:00 / 0:00")
        self.play_button = QPushButton("▶")
        self.play_button.setFocusPolicy(Qt.NoFocus)

        layout.addWidget(self.prompt_label)
        layout.addWidget(self.prompt_display)
        layout.addWidget(self.lyrics_label)
        layout.addWidget(self.lyrics_display)
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.time_label)
        layout.addLayout(progress_layout)
        layout.addWidget(self.play_button)
        widget.setLayout(layout)

        # Media player setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(audio_path))

        self.player.positionChanged.connect(self.update_slider_position)
        self.player.durationChanged.connect(self.update_slider_range)
        self.progress_slider.sliderMoved.connect(self.seek_position)
        self.play_button.clicked.connect(self.toggle_play)

        self.setWidget(widget)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_button.setText("▶")
        else:
            self.player.play()
            self.play_button.setText("⏸︎")

    def update_slider_range(self, duration):
        self.progress_slider.setEnabled(True)
        self.progress_slider.setMaximum(duration)
        self.update_time_label(self.player.position(), duration)

    def update_slider_position(self, position):
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(position)
        self.update_time_label(position, self.player.duration())

    def seek_position(self, position):
        self.player.setPosition(position)

    def update_time_label(self, position, duration):
        def ms_to_min_sec(ms):
            minutes = int(ms / 60000)
            seconds = int((ms % 60000) / 1000)
            return f"{minutes}:{seconds:02}"

        current = ms_to_min_sec(position)
        total = ms_to_min_sec(duration) if duration > 0 else "0:00"
        self.time_label.setText(f"{current} / {total}")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, global_pos):
        menu = QMenu()
        save_action = menu.addAction("Save WAV As...")
        copy_action = menu.addAction("Copy WAV")
        save_mp3_action = menu.addAction("Save MP3 As...")
        copy_mp3_action = menu.addAction("Copy MP3")

        action = menu.exec(global_pos)
        if action == save_action:
            self.save_wav_dialog()
        if action == copy_action:
            self.copy_wav_to_clipboard()
        if action == save_mp3_action:
            self.save_mp3_dialog()
        if action == copy_mp3_action:
            self.copy_mp3_to_clipboard()

    def save_wav_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save WAV",
            "ace_step.wav",
            "WAV (*.wav)"
        )
        if file_path:
            try:
                shutil.copyfile(self.audio_path, file_path)
            except Exception as e:
                print(f"Failed to save audio file: {e}")

    def save_mp3_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save MP3",
            "audio.mp3",
            "MP3 Files (*.mp3)"
        )
        if file_path:
            self.convert_wav_to_mp3(self.audio_path, file_path)

    def copy_wav_to_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(self.audio_path)])
        clipboard.setMimeData(mime_data)

    def copy_mp3_to_clipboard(self):
        try:
            # Create a temporary MP3 file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                mp3_path = tmp_mp3.name

            # Convert WAV to MP3
            audio = AudioSegment.from_wav(self.audio_path)
            audio.export(mp3_path, format="mp3")

            # Copy the MP3 file path to clipboard as URL
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(mp3_path)])
            QApplication.clipboard().setMimeData(mime_data)

            print(f"Copied MP3 to clipboard: {mp3_path}")
        except Exception as e:
            print(f"Failed to copy MP3 to clipboard: {e}")

    def convert_wav_to_mp3(self, wav_path: str, mp3_path: str):
        try:
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3")
            print(f"Converted to MP3: {mp3_path}")
        except Exception as e:
            print(f"Failed to convert WAV to MP3: {e}")


class ClickablePixmap(QGraphicsPixmapItem):
    def __init__(self, original_pixmap: QPixmap, gallery, tabs):
        super().__init__(original_pixmap)
        self.tabs = tabs
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self.original_pixmap = original_pixmap
        self.gallery = gallery
        self.view_state = 1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.view_state == 1:
                width = self.gallery.viewport().width()
                height = self.gallery.viewport().height()
                self.gallery.scaled_image_view.clear()
                scaled_pixmap = self.original_pixmap.scaled(QSize(width, height), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                scaled_to_fit_pixmap = ClickablePixmap(self.original_pixmap, self.gallery, self.tabs)
                scaled_to_fit_pixmap.setPixmap(scaled_pixmap)
                scaled_to_fit_pixmap.view_state = 2
                self.gallery.scaled_image_view.addItem(scaled_to_fit_pixmap)
                self.gallery.centerOn(0, 0)
                self.gallery.setScene(self.gallery.scaled_image_view)
            elif self.view_state == 2:
                width = self.gallery.viewport().width()
                self.gallery.full_image_view.clear()
                scaled_fullscreen_pixmap = self.original_pixmap.scaledToWidth(width, Qt.SmoothTransformation)
                fullscreen_pixmap = ClickablePixmap(self.original_pixmap, self.gallery, self.tabs)
                fullscreen_pixmap.setPixmap(scaled_fullscreen_pixmap)
                fullscreen_pixmap.view_state = 3
                self.gallery.full_image_view.addItem(fullscreen_pixmap)
                self.gallery.centerOn(0, 0)
                self.gallery.setScene(self.gallery.full_image_view)
            elif self.view_state == 3:
                self.gallery.setScene(self.gallery.gallery)
                self.gallery.centerOn(0, 0)

        elif event.button() == Qt.RightButton:
            show_context_menu(self.tabs, self.original_pixmap)


class ClickableVideo(QGraphicsWidget):
    def __init__(self, video_path: str, prompt: str, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.prompt = prompt
        self._aspect_ratio = 16 / 9

        self._video_item = QGraphicsVideoItem(self)
        self._video_item.nativeSizeChanged.connect(self._on_native_size_changed)
        self._audio_output = QAudioOutput()

        self._player = QMediaPlayer()
        self._player.setLoops(QMediaPlayer.Loops.Infinite)
        self._player.setAudioOutput(self._audio_output)
        self._player.setVideoOutput(self._video_item)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)

        self._controls_widget = QWidget()
        self._controls_widget.setContentsMargins(0, 0, 0, 0)
        controls_layout = QHBoxLayout(self._controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)

        style = self._controls_widget.style()

        self._prompt_label = QLabel(self.prompt)
        self._prompt_label.setAlignment(Qt.AlignCenter)
        self._prompt_label.setWordWrap(True)
        self._prompt_proxy = QGraphicsProxyWidget(self)
        self._prompt_proxy.setWidget(self._prompt_label)
        self._play_button = QPushButton()
        self._play_button.setIcon(QIcon.fromTheme("media-playback-start",
                                                  style.standardIcon(QStyle.SP_MediaPlay)))
        self._play_button.clicked.connect(self._toggle_playback)
        controls_layout.addWidget(self._play_button)

        self._controls_proxy = QGraphicsProxyWidget(self)
        self._controls_proxy.setContentsMargins(0, 0, 0, 0)
        self._controls_proxy.setWidget(self._controls_widget)

        self.load_video(self.video_path)

    def resizeEvent(self, event):
        w = self.geometry().width()
        h = self.geometry().height()

        prompt_height = self._prompt_label.sizeHint().height()
        controls_height = self._controls_widget.sizeHint().height()
        video_area_height = h - (prompt_height + controls_height)

        # Fit video into available area, maintain aspect ratio
        video_w = w
        video_h = min(video_w / self._aspect_ratio, video_area_height)

        # Place elements
        self._prompt_proxy.setGeometry(QRectF(0, 0, w, prompt_height))
        self._video_item.setSize(QSizeF(video_w, video_h))
        self._video_item.setPos(0, prompt_height)
        self._controls_proxy.setGeometry(QRectF(0, h - controls_height, w, controls_height))
        self._player.play()
        self._player.pause()

        super().resizeEvent(event)

    # --- Media handling ---
    def load_video(self, video_path: str):
        url = QUrl.fromLocalFile(video_path)
        self._player.setSource(url)


    def _toggle_playback(self):
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
            self._play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self._player.play()
            self._play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self._play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self._player.play()
            self._player.stop()

        if status == QMediaPlayer.LoadedMedia:
            # Video is now loaded, native size should be valid
            size = self._video_item.nativeSize()
            if not size.isEmpty():
                self._aspect_ratio = size.width() / size.height()
            # Trigger re-layout
            self.updateGeometry()
            self.update()
            if self.scene() and hasattr(self.scene(), 'parent_view') and self.scene().parent_view:
                self.scene().parent_view.tile_images()

    def _on_native_size_changed(self, size: QSizeF):
        if not size.isEmpty():
            self._aspect_ratio = size.width() / size.height()
            self.updateGeometry()  # let the layout know the size hint changed
            self.update()
            if self.scene() and hasattr(self.scene(), 'parent_view') and self.scene().parent_view:
                self.scene().parent_view.tile_images()

    def sizeHint(self, which, constraint=QSizeF()):
        # Report preferred size for layout calculations
        width = constraint.width() if constraint.width() > 0 else 320  # default width
        prompt_height = self._prompt_label.sizeHint().height()
        controls_height = self._controls_widget.sizeHint().height()
        video_height = width / self._aspect_ratio
        total_height = prompt_height + video_height + controls_height
        return QSizeF(width, total_height)


    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, global_pos):
        menu = QMenu()
        save_action = menu.addAction("Save As...")
        copy_action = menu.addAction("Copy")

        action = menu.exec(global_pos)
        if action == save_action:
            self.save_dialog()
        if action == copy_action:
            self.copy_to_clipboard()

    def save_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save",
            "wan.mp4",
            "MP4 (*.mp4)"
        )
        if file_path:
            try:
                shutil.copyfile(self.video_path, file_path)
            except Exception as e:
                print(f"Failed to save video file: {e}")

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(self.video_path)])
        clipboard.setMimeData(mime_data)

class QueueObjectWidget(QFrame):
    def __init__(self, queue_object, hex_color, queue_view):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.queue_object = queue_object
        self.hex_color = hex_color
        self.queue_view = queue_view

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(0)

        self.prompt_layout = QVBoxLayout()
        self.prompt_layout.setAlignment(Qt.AlignTop)
        self.prompt_layout.setContentsMargins(0, 0, 0, 0)
        self.prompt_layout.setSpacing(0)
        self.prompt_container = QWidget()
        self.prompt_container.setStyleSheet(f"color: #ffffff; background-color: {self.hex_color};")
        self.prompt_container.setLayout(self.prompt_layout)

        self.status_layout = QVBoxLayout()
        self.status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_container = QWidget()
        self.status_container.setStyleSheet(f"color: #ffffff; background-color: #444400;")
        self.status_container.setLayout(self.status_layout)

        self.button_layout = QVBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_from_queue)
        self.info_button = QPushButton("Info")
        self.info_button.clicked.connect(self.info)

        if self.queue_object.queue_info:
            self.type_label = QLabel(f"{self.queue_object.__class__.__name__} | {self.queue_object.queue_info}")
        else:
            self.type_label = QLabel(self.queue_object.__class__.__name__)
        self.type_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.prompt_separator = QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Plain, lineWidth=10)
        self.prompt_separator.setStyleSheet(f"color: #888888; background-color: #888888;")
        self.prompt_label = QLabel(self.queue_object.prompt, wordWrap=True)
        self.status_label = QLabel("Queued")

        self.main_layout.addWidget(self.prompt_container, stretch=20)
        self.main_layout.addWidget(self.status_container)
        self.main_layout.addLayout(self.button_layout)
        self.prompt_layout.addWidget(self.type_label)
        self.prompt_layout.addWidget(self.prompt_separator)
        self.prompt_layout.addWidget(self.prompt_label)
        self.status_layout.addWidget(self.status_label)
        self.button_layout.addWidget(self.remove_button)
        self.button_layout.addWidget(self.info_button)

    def info(self):
        prompt = getattr(self.queue_object, "enhanced_prompt", None)
        if prompt and str(prompt).strip():
            info_box = SelectableMessageBox("Generation Info", prompt)
        else:
            prompt = getattr(self.queue_object, "prompt", None)
            info_box = SelectableMessageBox("Generation Info", prompt)
        info_box.exec()

    def remove_from_queue(self):

        if self.queue_object in self.queue_view.parent().parent().parent().parent().pending_requests:
            self.queue_view.parent().parent().parent().parent().pending_requests.remove(self.queue_object)
        self.queue_view.del_queue_item(self)