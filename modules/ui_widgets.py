import json
import os
import sys
import shutil
import tempfile

import cv2
from pydub import AudioSegment
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QGraphicsView,
                               QGraphicsScene, QGraphicsPixmapItem, QLabel, QLineEdit, QCheckBox, QMenu, QFileDialog,
                               QSlider, QWidget, QFrame, QSizePolicy, QScrollArea, QMessageBox, QDialog, QGridLayout,
                               QLayout, QComboBox, QInputDialog, QButtonGroup, QGraphicsProxyWidget, QGraphicsItem,
                               QPlainTextEdit, QStyle, QGraphicsWidget, QListWidget, QStackedWidget, QListWidgetItem,
                               QStyledItemDelegate)
from PySide6.QtGui import (QMouseEvent, QPixmap, QPainter, QPaintEvent, QPen, QTextDocument, QColor, QCursor, QFont,
                           QIcon, QImage)
from PySide6.QtCore import Qt, QSize, QSizeF, QUrl, QMimeData, Signal, QRectF, QObject, QModelIndex
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem

class CheckableComboBox(QComboBox):
    """A QComboBox with checkable items for multi-selection."""
    selectionChanged = Signal(list)

    def __init__(self):
        super().__init__()
        self.setEditable(False)
        self._updating_text = False
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMaximumWidth(200)

        # Use this delegate to prevent highlighting/flicker
        delegate = QStyledItemDelegate()
        self.setItemDelegate(delegate)

        # Connect the view press to our custom handler
        self.view().pressed.connect(self.on_item_pressed)

    def on_item_pressed(self, index):
        """Toggle check state without changing the current index."""
        item = self.model().itemFromIndex(index)
        if item is not None:
            # Toggle state
            item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
            self._update_display_text()

    def add_checkable_item(self, text, checked=False):
        self.addItem(text)
        item = self.model().item(self.count() - 1)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setData(Qt.Checked if checked else Qt.Unchecked, Qt.CheckStateRole)
        self._update_display_text()

    def checked_items(self):
        return [
            self.model().item(i).text()
            for i in range(self.count())
            if self.model().item(i).checkState() == Qt.Checked
        ]

    def set_checked_items(self, items):
        for i in range(self.count()):
            item = self.model().item(i)
            item.setCheckState(Qt.Checked if item.text() in items else Qt.Unchecked)
        self._update_display_text()

    def _update_display_text(self):
        """Show checked items in the combo text."""
        self._updating_text = True
        checked = self.checked_items()
        display = ", ".join(checked) if checked else "Select prompts..."
        self.setCurrentText(display)
        self.selectionChanged.emit(checked)
        self._updating_text = False

class CircleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_green: bool = False
        self.setFixedSize(QSize(20, 20))

    def toggle_color(self):
        """Toggle between green and red."""
        self.is_green = not self.is_green
        self.update()  # Trigger a repaint

    def set_color(self, state):
        if state == 1:
            self.is_green = True
        else:
            self.is_green = False
        self.update()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Choose color based on state
        color = QColor("green") if self.is_green else QColor("red")
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)

        # Draw the circle centered in the widget
        rect = self.rect()
        diameter = min(rect.width(), rect.height()) - 10  # Padding
        x = (rect.width() - diameter) // 2
        y = (rect.height() - diameter) // 2

        painter.drawEllipse(x, y, diameter, diameter)


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
            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as tmp_mp3:
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


class Console(QHBoxLayout):
    def __init__(self):
        super().__init__()
        self.text_display = QTextEdit(readOnly=True)
        self.text_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.addWidget(self.text_display)
        sys.stdout = self

    def write(self, message):
        self.text_display.insertPlainText(message)

    def flush(self):
        pass

class HorizontalSlider(QHBoxLayout):
    def __init__(self, label, min, max, default=1, interval=1, enable_ticks=True):
        super().__init__()
        self.label = QLabel(f"{label}:")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(min)
        self.slider.setMaximum(max)
        if enable_ticks:
            self.slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
            self.slider.setTickInterval(interval)
        self.slider.setValue(default)
        self.slider.valueChanged.connect(self.update_value)
        self.value_label = QLabel(f"{self.slider.value()}")

        self.addWidget(self.label)
        self.addWidget(self.value_label)
        self.addWidget(self.slider)

    def update_value(self):
        self.value_label.setText(f"{self.slider.value()}")

class ImageGallery(QVBoxLayout):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.column_slider = HorizontalSlider("Gallery Columns", 1, 10, 4, 1)
        self.clear_gallery_button = QPushButton("Clear Gallery")
        self.clear_gallery_button.clicked.connect(self.clear_gallery)
        self.gallery = ImageGalleryViewer(self, self.parent)
        self.column_slider.slider.valueChanged.connect(self.gallery.tile_images)

        config_layout = QHBoxLayout()
        config_layout.addLayout(self.column_slider)
        config_layout.addWidget(self.clear_gallery_button)
        self.addLayout(config_layout)
        self.addWidget(self.gallery)

    def clear_gallery(self):
        self.gallery.gallery.clear()
        self.gallery.tile_images()
        self.update()


class ImageGalleryViewer(QGraphicsView):
    def __init__(self, top_layout, parent):
        super().__init__()
        self.parent = parent
        self.top_layout = top_layout
        self.gallery = QGraphicsScene()
        self.scaled_image_view = QGraphicsScene()
        self.full_image_view = QGraphicsScene()
        self.setScene(self.gallery)
        self.gallery.parent_view = self

    def add_item(self, item: QGraphicsItem):
        self.gallery.addItem(item)

    def tile_images(self):
        cur_x = 0
        cur_y = 0
        width = self.viewport().width()
        columns = self.top_layout.column_slider.slider.value()
        tile_width = width / columns
        spacing = 0

        row_max_height = 0
        current_row = []

        for item in self.gallery.items():
            if isinstance(item, ClickablePixmap):
                scaled_pixmap = item.original_pixmap.scaledToWidth(tile_width, Qt.SmoothTransformation)
                item.setPixmap(scaled_pixmap)
            elif isinstance(item, ClickableAudio):
                widget = item.widget()
                widget.setFixedWidth(tile_width)
                widget.adjustSize()
            elif isinstance(item, ClickableVideo):
                tile_width = width / columns
                item.resize(tile_width, item.sizeHint(Qt.PreferredSize).height())

            else:
                continue  # unsupported type

            item.setPos(cur_x, cur_y)
            current_row.append(item)
            item_height = item.boundingRect().height()
            row_max_height = max(row_max_height, item_height)
            cur_x += tile_width + spacing

            if len(current_row) >= columns:
                cur_y += row_max_height + spacing
                cur_x = 0
                row_max_height = 0
                current_row = []

        self.gallery.setSceneRect(0, 0, width, cur_y + row_max_height + spacing)

    def resizeEvent(self, event):
        """Resize event to ensure the images fit within the view and re-tile them."""
        super().resizeEvent(event)
        self.tile_images()  # Fit the image to the window size


class ImageInputBox(QHBoxLayout):
    def __init__(self, source_widget, name="", default_image_path="assets/chili.png"):
        super().__init__()
        self.source_widget = source_widget
        self.default_image_path = default_image_path
        self.image_file_path = None

        self.resolution_label = QLabel("")
        self.enable_checkbox = QCheckBox(f"Enable {name}")
        self.paste_image_button = QPushButton("Paste")
        self.paste_image_button.clicked.connect(self.paste_image)
        self.load_image_button = QPushButton("Load")
        self.load_image_button.clicked.connect(self.load_image)
        self.image_view = ScalingImageView(self.source_widget.tabs)
        self.input_image = QPixmap("assets/chili.png")
        self.image_layout = QVBoxLayout()
        self.enable_layout = QHBoxLayout()
        self.enable_layout.addWidget(self.resolution_label)
        self.enable_layout.addWidget(self.enable_checkbox)
        self.enable_layout.addWidget(self.paste_image_button)
        self.enable_layout.addWidget(self.load_image_button)
        self.image_layout.addLayout(self.enable_layout)
        self.image_layout.addWidget(self.image_view)
        self.addLayout(self.image_layout)
        self.load_image(default_image_path)

    def load_image(self, file_path=None):
        if file_path is False:
            self.image_file_path = QFileDialog.getOpenFileName(self.source_widget, str("Open Image"), "~", str("Image Files (*.png *.jpg *.webp)"))[0]
            if self.image_file_path == "":
                return
        else:
            self.image_file_path = file_path
        try:
            self.input_image = QPixmap(self.image_file_path)
            self.image_view.add_pixmap(self.input_image)
            self.resolution_label.setText(f"{self.input_image.width()}x{self.input_image.height()}")
        except Exception as e:
            print(e)

    def load_pixmap(self, pixmap=None):
        self.input_image = pixmap
        self.image_view.add_pixmap(self.input_image)
        self.resolution_label.setText(f"{self.input_image.width()}x{self.input_image.height()}")


    def paste_image(self):
        clipboard = QApplication.clipboard()
        mimedata = clipboard.mimeData()
        if mimedata.hasImage():
            self.input_image = QPixmap(mimedata.imageData())
            self.image_view.add_pixmap(self.input_image)
            self.resolution_label.setText(f"{self.input_image.width()}x{self.input_image.height()}")

class LLMHistoryWidget(QScrollArea):
    def __init__(self, tab):
        super().__init__()
        self.tab = tab
        self.messages = []
        self.container_widget = QWidget()
        self.setWidget(self.container_widget)
        self.setWidgetResizable(True)

        self.main_layout = QVBoxLayout(self.container_widget)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)  # tiny gap between messages


        self.verticalScrollBar().rangeChanged.connect(
            lambda min_val, max_val: self.verticalScrollBar().setValue(max_val)
        )
        self.setStyleSheet("""
                 border: none;
                 background-color: #2c2c31;
                 color: #ddd;
                 font-size: 14px;
                 border: 2px solid solid;
                 border-color: #28282f;
                 border-radius: 8px; /* rounded corners */
                 """)

    def add_message(self, role, message, hex_color):
        message_item = LLMHistoryObjectWidget(role, message, hex_color)
        self.main_layout.addWidget(message_item)
        self.messages.append(message_item)
        message_item.removeRequested.connect(self.handle_remove_request)
        message_item.rerollRequested.connect(self.handle_reroll_request)

    def clear_history(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.messages.clear()

    def get_history(self):
        history_list = []
        for i in range(self.main_layout.count()):
            item = self.main_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, LLMHistoryObjectWidget):
                history_list.append({
                    "role": widget.role,
                    "content": widget.message
                })
        return history_list

    def handle_remove_request(self, widget):
        if widget not in self.messages:
            return

        index = self.messages.index(widget)

        if widget.role == "user":
            # delete user + assistant after
            widgets_to_delete = [widget]
            if index + 1 < len(self.messages) and self.messages[index + 1].role == "assistant":
                widgets_to_delete.append(self.messages[index + 1])
        elif widget.role == "assistant":
            # delete assistant + user before
            widgets_to_delete = [widget]
            if index - 1 >= 0 and self.messages[index - 1].role == "user":
                widgets_to_delete.insert(0, self.messages[index - 1])
        else:
            widgets_to_delete = [widget]  # fallback

        # remove widgets
        for w in widgets_to_delete:
            self.main_layout.removeWidget(w)
            self.messages.remove(w)
            w.setParent(None)
            w.deleteLater()

    def handle_reroll_request(self, widget):
        index = self.messages.index(widget)

        if widget.role == "user":
            input_text = widget.message
            remove_from_index = index  # remove this user message and everything after
        elif widget.role == "assistant":
            # Reroll assistant → use previous user message
            if index - 1 >= 0 and self.messages[index - 1].role == "user":
                input_text = self.messages[index - 1].message
                remove_from_index = index - 1  # remove that user message and everything after
            else:
                # no valid previous user message, cannot reroll
                return
        else:
            return  # unknown role, ignore

        # Build truncated history up to the message BEFORE remove_from_index
        history = []
        for i in range(remove_from_index):  # messages before the one being rerolled
            w = self.messages[i]
            if isinstance(w, LLMHistoryObjectWidget):
                history.append({"role": w.role, "content": w.message})

        # Remove widgets from remove_from_index onward
        for w in self.messages[remove_from_index:]:
            self.main_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()

        # Keep only the truncated messages
        self.messages = self.messages[:remove_from_index]

        # Call reroll
        self.tab.on_reroll(input_text, history)

class LLMHistoryObjectWidget(QFrame):
    removeRequested = Signal(object)
    rerollRequested = Signal(object)
    def __init__(self, role, message, hex_color):
        super().__init__()
        self.role = role
        self.message = message
        self.hex_color = hex_color

        # make the frame hug its contents tightly
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWidth(0)
        self.setMidLineWidth(0)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)  # small horizontal gap

        # --- prompt container ---
        self.prompt_layout = QVBoxLayout()
        self.prompt_layout.setAlignment(Qt.AlignTop)
        self.prompt_layout.setContentsMargins(0, 0, 0, 0)  # padding inside bubble
        self.prompt_layout.setSpacing(0)

        self.prompt_container = QWidget()
        self.prompt_container.setStyleSheet(
            f"color: #ffffff; background-color: {self.hex_color}; border-radius: 6px;"
        )
        self.prompt_container.setLayout(self.prompt_layout)

        # --- buttons ---
        self.button_layout = QVBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(2)

        self.remove_button = QPushButton("❌")
        self.remove_button.setFixedSize(28, 28)
        self.remove_button.setStyleSheet("margin: 0; padding: 0;")
        self.remove_button.clicked.connect(self.remove_from_history)

        self.reroll_button = QPushButton("↻")
        self.reroll_button.setFixedSize(28, 28)
        self.reroll_button.setStyleSheet("margin: 0; padding: 0;")
        self.reroll_button.clicked.connect(self.reroll)

        # --- labels ---
        self.type_label = WordWrapLabel(self.role)
        self.type_label.setContentsMargins(0, 0, 0, 0)
        self.type_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.type_label.setWordWrap(True)

        self.prompt_separator = QFrame(
            frameShape=QFrame.Shape.HLine,
            frameShadow=QFrame.Shadow.Plain
        )
        self.prompt_separator.setFixedHeight(1)
        self.prompt_separator.setStyleSheet("background-color: #888888; margin: 0;")

        self.prompt_label = WordWrapLabel(self.message)
        self.prompt_label.setContentsMargins(0, 0, 0, 0)
        self.prompt_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.prompt_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.prompt_label.setWordWrap(True)

        # --- assemble layouts ---
        self.main_layout.addWidget(self.prompt_container)
        self.main_layout.addLayout(self.button_layout)

        self.prompt_layout.addWidget(self.type_label)
        self.prompt_layout.addWidget(self.prompt_separator)
        self.prompt_layout.addWidget(self.prompt_label)

        self.button_layout.addWidget(self.remove_button)
        self.button_layout.addWidget(self.reroll_button)
        self.button_layout.addStretch()

    def reroll(self):
        self.rerollRequested.emit(self)

    def remove_from_history(self):
        self.removeRequested.emit(self)


class ModelPickerWidget(QHBoxLayout):
    def __init__(self, model_arch, label=None):
        super().__init__()
        self.data_list = []
        self.model_arch = model_arch
        self.json_path = f"assets/{self.model_arch}.json"

        # Load or create the JSON file
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r") as f:
                    self.data_list = json.load(f)
            except json.JSONDecodeError:
                QMessageBox.warning(None, "Load Error", f"Failed to parse {self.json_path}. Starting fresh.")
                self.data_list = []
        else:
            self._save_model_list()  # Create blank file if it doesn't exist

        self.model_list_picker = QComboBox()
        self.model_list_picker.insertItems(0, self.data_list)
        self.model_list_picker.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.model_list_picker.setMaximumWidth(650)        # ⬅️ limit width
        self.model_list_picker.setMinimumWidth(120)
        self.model_list_picker.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.addStretch()
        if label is not None:
            self.model_label = QLabel(label)
            self.addWidget(self.model_label)
        self.addWidget(self.model_list_picker)
        self.add_model_button = QPushButton("+ Model")
        self.add_model_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.add_model_button.setMaximumWidth(50)
        self.add_model_button.clicked.connect(self.add_model)
        self.remove_model_button = QPushButton("- Model")
        self.remove_model_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.remove_model_button.setMaximumWidth(50)
        self.remove_model_button.clicked.connect(self.remove_model)
        self.addWidget(self.add_model_button)
        self.addWidget(self.remove_model_button)



    def add_model(self):
        text, ok = QInputDialog.getText(None, "Add Model", "Enter model name:")
        if ok and text.strip():
            model_name = text.strip()
            if model_name in self.data_list:
                QMessageBox.warning(None, "Duplicate Model", f"'{model_name}' already exists.")
                return
            self.data_list.append(model_name)
            self.model_list_picker.addItem(model_name)
            self._save_model_list()

    def _save_model_list(self):
        with open(self.json_path, "w") as f:
            json.dump(self.data_list, f, indent=2)

    def remove_model(self):
        current_index = self.model_list_picker.currentIndex()
        if current_index == -1:
            QMessageBox.information(None, "No Selection", "Please select a model to remove.")
            return

        model_name = self.model_list_picker.currentText()
        confirm = QMessageBox.question(
            None,
            "Remove Model",
            f"Are you sure you want to remove '{model_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.model_list_picker.removeItem(current_index)
            self.data_list.remove(model_name)
            self._save_model_list()


class OutpaintingWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.main_layout = QHBoxLayout()
        self.button_layout = QGridLayout()
        self.button_layout.setSpacing(1)
        self.button_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.config_layout = QVBoxLayout()

        self.align_northwest_button = SquareButton("↖")
        self.align_north_button = SquareButton("🡩")
        self.align_northeast_button = SquareButton("↗")
        self.align_west_button = SquareButton("←")
        self.align_center_button = SquareButton("O")
        self.align_east_button = SquareButton("→")
        self.align_southwest_button = SquareButton("↙")
        self.align_south_button = SquareButton("↓")
        self.align_southeast_button = SquareButton("↘")
        self.align_northwest_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_north_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_northeast_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_west_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_center_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_east_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_southwest_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_south_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_southeast_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.align_northwest_button.setCheckable(True)
        self.align_north_button.setCheckable(True)
        self.align_northeast_button.setCheckable(True)
        self.align_west_button.setCheckable(True)
        self.align_center_button.setCheckable(True)
        self.align_east_button.setCheckable(True)
        self.align_southwest_button.setCheckable(True)
        self.align_south_button.setCheckable(True)
        self.align_southeast_button.setCheckable(True)

        self.expand_pixels_input = SingleLineInputBox("# of pixels to expand:")
        self.enable_outpainting_checkbox = QCheckBox("Enable outpainting")

        self.button_layout.addWidget(self.align_northwest_button, 0 ,0)
        self.button_layout.addWidget(self.align_north_button, 0, 1)
        self.button_layout.addWidget(self.align_northeast_button, 0, 2)
        self.button_layout.addWidget(self.align_west_button, 1, 0)
        self.button_layout.addWidget(self.align_center_button, 1, 1)
        self.button_layout.addWidget(self.align_east_button, 1, 2)
        self.button_layout.addWidget(self.align_southwest_button, 2, 0)
        self.button_layout.addWidget(self.align_south_button, 2, 1)
        self.button_layout.addWidget(self.align_southeast_button, 2, 2)

        self.config_layout.addWidget(self.enable_outpainting_checkbox)
        self.config_layout.addLayout(self.expand_pixels_input)

        self.main_layout.addLayout(self.config_layout)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)

        self.alignment_button_group = QButtonGroup(self)
        self.alignment_button_group.setExclusive(True)
        self.alignment_button_group.addButton(self.align_northwest_button)
        self.alignment_button_group.addButton(self.align_north_button)
        self.alignment_button_group.addButton(self.align_northeast_button)
        self.alignment_button_group.addButton(self.align_west_button)
        self.alignment_button_group.addButton(self.align_center_button)
        self.alignment_button_group.addButton(self.align_east_button)
        self.alignment_button_group.addButton(self.align_southwest_button)
        self.alignment_button_group.addButton(self.align_south_button)
        self.alignment_button_group.addButton(self.align_southeast_button)

    def get_selected_alignment(self):
        button = self.alignment_button_group.checkedButton()
        if button:
            return button.text()  # or use custom data if you set any
        return None


class PainterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_image = QPixmap("assets/chili.png")
        self.original_image = self.input_image
        self.mask_pixmap = QPixmap(self.input_image.size())
        self.mask_pixmap.fill(QColor(0, 0, 0, 0))
        self.original_mask = self.mask_pixmap
        self.image_file_path = None

        self.previous_pos = None
        self.painter = QPainter()
        self.pen = QPen()
        self.pen.setWidth(40)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.pen.setColor(Qt.GlobalColor.white)

    def paintEvent(self, event: QPaintEvent):
        with QPainter(self) as painter:
            painter.drawPixmap(0, 0, self.input_image)
            painter.drawPixmap(0, 0, self.mask_pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        self.previous_pos = event.position().toPoint()

        self.painter.begin(self.mask_pixmap)
        self.painter.setRenderHints(QPainter.RenderHint.Antialiasing, True)
        self.painter.setPen(self.pen)
        self.painter.drawPoint(self.previous_pos)
        self.painter.end()

        self.original_mask = self.mask_pixmap.scaledToWidth(self.input_image.width())
        self.update()

        QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event: QMouseEvent):
        current_pos = event.position().toPoint()
        self.painter.begin(self.mask_pixmap)
        self.painter.setRenderHints(QPainter.RenderHint.Antialiasing, True)
        self.painter.setPen(self.pen)
        self.painter.drawLine(self.previous_pos, current_pos)
        self.painter.end()
        self.original_mask = self.mask_pixmap.scaledToWidth(self.input_image.width())
        self.previous_pos = current_pos
        self.update()

        QWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.previous_pos = None
        QWidget.mouseReleaseEvent(self, event)

    def clear(self):
        self.mask_pixmap.fill(QColor(0, 0, 0, 0))
        self.update()

    def resizeEvent(self, event):
        self.resize_image()
        super().resizeEvent(event)

    def resize_image(self):
        self.input_image = self.original_image.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.mask_pixmap = self.original_mask.scaled(self.input_image.size(), Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation)

    def load_image(self):
        self.image_file_path = QFileDialog.getOpenFileName(self, str("Open Image"), "~", str("Image Files (*.png *.jpg *.webp)"))[0]
        if self.image_file_path != "":
            self.original_image = QPixmap(self.image_file_path)
            self.original_mask = self.original_mask.scaled(QSize(self.original_image.width(), self.original_image.height()))
            self.resize_image()

    def set_image(self, pixmap):
        self.original_image = pixmap
        self.original_mask = self.original_mask.scaled(QSize(self.original_image.width(), self.original_image.height()))
        self.resize_image()

    def paste_image(self):
        clipboard = QApplication.clipboard()
        mimedata = clipboard.mimeData()
        if mimedata.hasImage():
            self.original_image = QPixmap(mimedata.imageData())
            self.original_mask = self.original_mask.scaled(QSize(self.original_image.width(), self.original_image.height()))
            self.resize_image()
            self.update()

    def update_cursor(self):
        size = self.pen.width() * 2
        diameter = size
        hotspot_offset = diameter // 2

        pixmap = QPixmap(diameter + 2, diameter + 2)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(1, 1, diameter, diameter)
        painter.end()

        cursor = QCursor(pixmap, hotspot_offset + 1, hotspot_offset + 1)
        self.setCursor(cursor)

    def enterEvent(self, event):
        self.update_cursor()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)


class ParagraphInputBox(QVBoxLayout):
    def __init__(self, label):
        super().__init__()
        self.label = QLabel(label)
        self.addWidget(self.label)
        self.input = QTextEdit(acceptRichText=False)
        self.addWidget(self.input)
        self.input.setStyleSheet("""
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

class PromptManager(QObject):
    promptsUpdated = Signal(list)
    _instance = None
    _initialized = False

    def __new__(cls, json_path="assets/prompts.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, json_path="assets/prompts.json"):
        # prevent QObject reinitialization
        if self._initialized:
            return
        super().__init__()
        self._initialized = True

        self.json_path = json_path
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        self._prompts = self._load_from_file()

    def _load_from_file(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError
                return data
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            return []

    def get_prompts(self):
        return list(self._prompts)

    def save_prompts(self):
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self._prompts, f, ensure_ascii=False, indent=4)

    def add_prompt(self, text):
        text = text.strip()
        if text and text not in self._prompts:
            self._prompts.append(text)
            self.save_prompts()
            self.promptsUpdated.emit(self._prompts)

    def remove_prompts(self, prompts_to_remove):
        updated = [p for p in self._prompts if p not in prompts_to_remove]
        if updated != self._prompts:
            self._prompts = updated
            self.save_prompts()
            self.promptsUpdated.emit(self._prompts)

class PromptPickerWidget(QWidget):
    """Compact prompt selector using a checkable dropdown."""
    def __init__(self):
        super().__init__()
        self.manager = PromptManager()

        # Main horizontal layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)

        # --- Combo Box ---
        self.combo = CheckableComboBox()
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.combo.setMaximumWidth(250)        # ⬅️ limit width
        self.combo.setMinimumWidth(120)
        self.combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.layout.addStretch()
        self.layout.addWidget(self.combo)

        # --- Buttons ---
        self.add_button = QPushButton("+ Prompt")
        self.add_button.setFixedWidth(55)
        self.remove_button = QPushButton("– Prompt")
        self.remove_button.setFixedWidth(55)

        self.layout.addWidget(self.add_button)
        self.layout.addWidget(self.remove_button)

        # Load data
        self.reload_list()

        # Connections
        self.add_button.clicked.connect(self.add_item)
        self.remove_button.clicked.connect(self.remove_selected_items)
        self.manager.promptsUpdated.connect(self.on_prompts_updated)

    def reload_list(self):
        self.combo.clear()
        for item in self.manager.get_prompts():
            self.combo.add_checkable_item(item)

    def on_prompts_updated(self, new_prompts):
        self.reload_list()

    def add_item(self):
        text, ok = QInputDialog.getText(self, "Add Prompt", "Enter new prompt:")
        if ok and text.strip():
            self.manager.add_prompt(text.strip())

    def remove_selected_items(self):
        selected = self.combo.checked_items()
        if not selected:
            QMessageBox.information(self, "No Selection", "Select one or more prompts to remove.")
            return
        self.manager.remove_prompts(selected)

    def get_selected_items(self):
        return self.combo.checked_items()

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

class QueueViewer(QScrollArea):
    def __init__(self):
        super().__init__()
        self.container_widget = QWidget()
        self.setWidget(self.container_widget)
        self.setWidgetResizable(True)
        self.clear_queue_button = QPushButton("Clear Queue")
        self.clear_queue_button.clicked.connect(self.clear_queue)

        self.main_layout = QVBoxLayout(self.container_widget)
        self.queue_layout = QVBoxLayout()
        self.queue_layout.setAlignment(Qt.AlignTop)
        self.queue_layout.addStrut(250)

        self.main_layout.addLayout(self.queue_layout, stretch=10)
        self.main_layout.addWidget(self.clear_queue_button)

    def add_queue_item(self, queue_item, queue_view, hex_color):
        queue_widget = QueueObjectWidget(queue_item, hex_color, queue_view)
        self.queue_layout.addWidget(queue_widget)
        return queue_widget

    def del_queue_item(self, queue_widget):
        self.queue_layout.removeWidget(queue_widget)
        queue_widget.setParent(None)
        queue_widget.deleteLater()

    def clear_queue(self):
        while self.queue_layout.count():
            item = self.queue_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:

                widget.setParent(None)
                widget.deleteLater()

class ResolutionInput(QWidget):
    def __init__(self, placeholder_x="1024", placeholder_y="1024"):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.swap_button = QPushButton("↕")
        self.swap_button.setFixedWidth(20)
        self.swap_button.clicked.connect(self.swap_resolution)
        self.swap_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.width_label = SingleLineInputBox("Width:", placeholder_text=placeholder_x)
        self.height_label = SingleLineInputBox("Height:", placeholder_text=placeholder_y)

        layout = QHBoxLayout(self)
        self.input_layout = QVBoxLayout()

        self.input_layout.addLayout(self.width_label)
        self.input_layout.addLayout(self.height_label)

        layout.addWidget(self.swap_button)
        layout.addLayout(self.input_layout)


    def swap_resolution(self):
        current_height = self.height_label.input.text()
        current_width = self.width_label.input.text()
        self.height_label.input.setText(current_width)
        self.width_label.input.setText(current_height)


class ScalingImageView(QGraphicsView):
    def __init__(self, tabs):
        super().__init__()
        self.tabs = tabs
        self.gallery = QGraphicsScene()
        self.setScene(self.gallery)
        self.original_image = None
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            show_context_menu(self.tabs, self.original_image)

    def add_pixmap(self, pixmap):
        self.gallery.clear()
        pixmap_item = QGraphicsPixmapItem(pixmap)
        self.original_image = pixmap
        self.gallery.addItem(pixmap_item)
        self.resize_image()

    def resize_image(self):
        width = self.viewport().width()
        for image in self.gallery.items():
            scaled_pixmap = self.original_image.scaledToWidth(width, Qt.SmoothTransformation)
            image.setPixmap(scaled_pixmap)
            image.setPos(0, 0)

    def resizeEvent(self, event):
        """Resize event to ensure the images fit within the view and re-tile them."""
        super().resizeEvent(event)
        self.resize_image()  # Fit the image to the window size

class SelectableMessageBox(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(message)
        self.text_edit.setReadOnly(True)  # Prevent editing but allow selection
        layout.addWidget(self.text_edit)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)


class SingleLineInputBox(QHBoxLayout):
    def __init__(self, label, placeholder_text=None):
        super().__init__()
        self.label = QLabel(label)
        if placeholder_text:
            self.input = QLineEdit(placeholderText=placeholder_text)
        else:
            self.input = QLineEdit()
        self.addWidget(self.label)
        self.addWidget(self.input)

class SquareButton(QPushButton):
    def __init__(self, text, font_size=16):  # Default font size
        super().__init__(text)

        font = QFont()
        font.setPointSize(font_size)
        self.setFont(font)

class VerticalTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.list = QListWidget()
        self.stack = QStackedWidget()

        # When user selects a new item in the list, change stacked widget page
        self.list.currentRowChanged.connect(self.stack.setCurrentIndex)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list)
        layout.addWidget(self.stack)
        self.setLayout(layout)
        self.setStyleSheet("""
            QListWidget {
                background-color: #2c2c31;
                color: #ddd;
                font-size: 14px;
                border-right: 1px solid #444; /* Optional: separates list from content */
            }

            QListWidget::item {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 8px; /* rounded corners */
                padding: 0px 0px;
                margin: 1px;
            }

            QListWidget::item:hover {
                background-color: #3a3a3f;
                border: 1px solid #555;
            }

            QListWidget::item:selected {
                background-color: #444;
                border: 1px solid #666;
                border-radius: 8px;
                color: white;
            }
        """)

        # Optional style
        self.list.setFixedWidth(120)
        self.list.setSpacing(0)

    # ---- API Compatibility with QTabWidget ----
    def addTab(self, widget: QWidget, label: str, icon: QIcon = None):
        item = QListWidgetItem(icon, label) if icon else QListWidgetItem(label)
        self.list.addItem(item)
        self.stack.addWidget(widget)
        if self.list.count() == 1:
            self.list.setCurrentRow(0)

    def insertTab(self, index: int, widget: QWidget, label: str):
        self.list.insertItem(index, label)
        self.stack.insertWidget(index, widget)

    def widget(self, index: int) -> QWidget:
        return self.stack.widget(index)

    def named_widget(self, name: str) -> QWidget | None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.text() == name:
                return self.stack.widget(i)
        return None

    def count(self) -> int:
        return self.stack.count()

    def currentIndex(self) -> int:
        return self.stack.currentIndex()

    def setCurrentIndex(self, index: int):
        self.list.setCurrentRow(index)
        self.stack.setCurrentIndex(index)

    def indexOf(self, widget: QWidget) -> int:
        return self.stack.indexOf(widget)

    def setTabText(self, index: int, text: str):
        item = self.list.item(index)
        if item:
            item.setText(text)

    def tabText(self, index: int) -> str:
        item = self.list.item(index)
        return item.text() if item else ""

    def setTabIcon(self, index: int, icon: QIcon):
        item = self.list.item(index)
        if item:
            item.setIcon(icon)

class VideoInputWidget(QWidget):
    def __init__(self, name):
        super().__init__()
        self.file_path = None
        layout = QVBoxLayout(self)
        enable_layout = QHBoxLayout()
        self.enable_checkbox = QCheckBox(f"Enable {name}")
        self.load_button = QPushButton("Select Video File")
        self.load_button.clicked.connect(self.load_video)
        self.image_label = QLabel("No video selected")
        self.image_label.setAlignment(Qt.AlignCenter)
        enable_layout.addWidget(self.enable_checkbox)
        enable_layout.addWidget(self.load_button)
        layout.addLayout(enable_layout)
        layout.addWidget(self.image_label, stretch=1)

    def load_video(self):
        self.file_path, _ = QFileDialog.getOpenFileName(self,
                                                   "Select Video File",
                                                   "",
                                                   "Video Files (*.mp4 *.avi *.mov *.mkv)")
        if not self.file_path:
            return
        cap = cv2.VideoCapture(self.file_path)
        if not cap.isOpened():
            self.image_label.setText("Failed to open video.")
            return

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            self.image_label.setText("Empty or invalid video.")
            cap.release()
            return

        middle_frame = frame_count // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            self.image_label.setText("Could not read frame.")
            return

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        # Convert to QImage
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        # Display as QPixmap
        pixmap = QPixmap.fromImage(qimg)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

class WordWrapLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    def heightForWidth(self, width):
        doc = QTextDocument()
        doc.setDefaultFont(self.font())
        doc.setTextWidth(width)
        doc.setPlainText(self.text())
        return int(doc.size().height())

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setHeight(self.heightForWidth(self.width()))
        return hint

    def resizeEvent(self, event):
        self.setMaximumWidth(self.parent().width() if self.parent() else self.width())
        super().resizeEvent(event)

def show_context_menu(tabs, pixmap):

    chroma_tab = tabs.named_widget("Chroma")
    flux_tab = tabs.named_widget("Flux")
    flux_inpaint_tab = tabs.named_widget("Flux Inpaint")
    flux_fill_tab = tabs.named_widget("Flux Fill")
    framepack_tab = tabs.named_widget("Framepack")
    qwen_image_tab = tabs.named_widget("Qwen")
    qwen_image_inpaint_tab = tabs.named_widget("Qwen Inpaint")
    qwen_image_edit_tab = tabs.named_widget("Qwen Edit+")
    sd15_tab = tabs.named_widget("SD 1.5")
    sd15_inpaint_tab = tabs.named_widget("SD 1.5 Inpaint")
    sdxl_tab = tabs.named_widget("SDXL")
    sdxl_inpaint_tab = tabs.named_widget("SDXL Inpaint")
    wan_tab = tabs.named_widget("Wan")
    wan_vace_tab = tabs.named_widget("Wan VACE")
    menu = QMenu()
    save_action = menu.addAction("Save Image As...")
    copy_action = menu.addAction("Copy Image")

    chroma_menu = menu.addMenu("Chroma")
    flux_menu = menu.addMenu("Flux")
    framepack_menu = menu.addMenu("Framepack")
    sd15_menu = menu.addMenu("SD 1.5")
    sdxl_menu = menu.addMenu("SDXL")
    qwen_menu = menu.addMenu("Qwen")
    wan_menu = menu.addMenu("Wan")

    chroma_send_to_i2i = chroma_menu.addAction("Send to Chroma I2I")
    sd15_send_to_i2i = sd15_menu.addAction("Send to SD 1.5 I2I")
    sd15_send_to_inpaint = sd15_menu.addAction("Send to SD 1.5 Inpaint")
    sdxl_send_to_i2i = sdxl_menu.addAction("Send to SDXL I2I")
    sdxl_send_to_ipadapter = sdxl_menu.addAction("Send to SDXL IP Adapter")
    sdxl_sent_to_controlnet = sdxl_menu.addAction("Send to SDXL Controlnet")
    sdxl_send_to_inpaint = sdxl_menu.addAction("Send to SDXL Inpaint")
    flux_send_to_i2i = flux_menu.addAction("Send to Flux I2I")
    flux_send_to_ipadapter = flux_menu.addAction("Send to Flux IP Adapter")
    flux_sent_to_kontext = flux_menu.addAction("Send to Flux Kontext")
    flux_send_to_inpaint = flux_menu.addAction("Send to Flux Inpaint")
    flux_send_to_fill = flux_menu.addAction("Send to Flux Fill")
    framepack_send_to_first_frame = framepack_menu.addAction("Send to Framepack First Frame")
    framepack_send_to_last_frame = framepack_menu.addAction("Send to Framepack Last Frame")
    qwen_image_send_to_i2i = qwen_menu.addAction("Send to Qwen Image")
    qwen_image_send_to_edit = qwen_menu.addAction("Send to Qwen Image Edit")
    qwen_image_send_to_inpaint = qwen_menu.addAction("Send to Qwen Image Inpaint")
    qwen_image_edit_send_to_1 = qwen_menu.addAction("Send to Qwen Image Edit Plus image 1")
    qwen_image_edit_send_to_2 = qwen_menu.addAction("Send to Qwen Image Edit Plus image 2")
    qwen_image_edit_send_to_3 = qwen_menu.addAction("Send to Qwen Image Edit Plus image 3")
    wan_send_to_i2v = wan_menu.addAction("Send to Wan I2V")
    wan_vace_send_to_first_frame = wan_menu.addAction("Send to WAN VACE First Frame")
    wan_vace_send_to_last_frame = wan_menu.addAction("Send to WAN VACE Last Frame")


    action = menu.exec(QCursor.pos())
    if action == save_action:
        save_image_dialog(pixmap)
    if action == copy_action:
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)

    if action == chroma_send_to_i2i:
        chroma_tab.i2i_image_label.load_pixmap(pixmap)

    if action == sd15_send_to_i2i:
        sd15_tab.i2i_image_label.load_pixmap(pixmap)
    if action == sd15_send_to_inpaint:
        sd15_inpaint_tab.paint_area.set_image(pixmap)

    if action == sdxl_send_to_i2i:
        sdxl_tab.i2i_image_label.load_pixmap(pixmap)
    if action == sdxl_send_to_ipadapter:
        sdxl_tab.ipadapter_image_label.load_pixmap(pixmap)
    if action == sdxl_sent_to_controlnet:
        sdxl_tab.controlnet_image_label.load_pixmap(pixmap)

    if action == sdxl_send_to_inpaint:
        sdxl_inpaint_tab.paint_area.set_image(pixmap)

    if action == flux_send_to_i2i:
        flux_tab.i2i_image_label.load_pixmap(pixmap)
    if action == flux_send_to_ipadapter:
        flux_tab.ipadapter_image_label.load_pixmap(pixmap)
    if action == flux_sent_to_kontext:
        flux_tab.kontext_image_label.load_pixmap(pixmap)

    if action == flux_send_to_inpaint:
        flux_inpaint_tab.paint_area.set_image(pixmap)
    if action == flux_send_to_fill:
        flux_fill_tab.paint_area.set_image(pixmap)

    if action == framepack_send_to_first_frame:
        framepack_tab.first_frame_label.load_pixmap(pixmap)
    if action == framepack_send_to_last_frame:
        framepack_tab.last_frame_label.load_pixmap(pixmap)

    if action == qwen_image_send_to_i2i:
        qwen_image_tab.i2i_image_label.load_pixmap(pixmap)
    if action == qwen_image_send_to_edit:
        qwen_image_tab.edit_image_label.load_pixmap(pixmap)
    if action == qwen_image_send_to_inpaint:
        qwen_image_inpaint_tab.paint_area.set_image(pixmap)
    if action == qwen_image_edit_send_to_1:
        qwen_image_edit_tab.edit_image_1_label.load_pixmap(pixmap)
    if action == qwen_image_edit_send_to_2:
        qwen_image_edit_tab.edit_image_2_label.load_pixmap(pixmap)
    if action == qwen_image_edit_send_to_3:
        qwen_image_edit_tab.edit_image_3_label.load_pixmap(pixmap)

    if action == wan_send_to_i2v:
        wan_tab.i2v_image_label.load_pixmap(pixmap)
    if action == wan_vace_send_to_first_frame:
        wan_vace_tab.first_frame_label.load_pixmap(pixmap)
    if action == wan_vace_send_to_last_frame:
        wan_vace_tab.last_frame_label.load_pixmap(pixmap)


def save_image_dialog(pixmap):
    file_path, _ = QFileDialog.getSaveFileName(
        None,
        "Save Image",
        "image.png",
        "Images (*.png *.jpg *.bmp)"
    )
    if file_path:
        pixmap.save(file_path)
