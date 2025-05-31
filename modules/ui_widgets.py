import sys
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QGraphicsView, QGraphicsScene,
                               QGraphicsPixmapItem, QLabel, QLineEdit, QCheckBox, QMenu, QFileDialog, QSlider, QWidget,
                               QFrame, QSizePolicy, QScrollArea)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt


class ClickablePixmap(QGraphicsPixmapItem):
    def __init__(self, original_pixmap, gallery, parent, source_tab):
        super().__init__(original_pixmap)
        self.parent = parent
        self.source_tab = source_tab
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self.original_pixmap = original_pixmap
        self.gallery = gallery
        self.is_fullscreen = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.is_fullscreen is True:
                self.is_fullscreen = False
                self.gallery.setScene(self.gallery.gallery)
                self.gallery.centerOn(0, 0)
            else:
                width = self.gallery.viewport().width()
                self.gallery.full_image_view.clear()
                scaled_pixmap = self.original_pixmap.scaledToWidth(width, Qt.SmoothTransformation)
                fullscreen_pixmap = ClickablePixmap(self.original_pixmap, self.gallery, self.parent, self.source_tab)
                fullscreen_pixmap.setPixmap(scaled_pixmap)
                fullscreen_pixmap.is_fullscreen = True
                self.gallery.full_image_view.addItem(fullscreen_pixmap)
                self.gallery.centerOn(0, 0)
                self.gallery.setScene(self.gallery.full_image_view)
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())

    def show_context_menu(self, global_pos):
        menu = QMenu()
        save_action = menu.addAction("Save Image As...")
        copy_action = menu.addAction("Copy Image")
        send_to_i2i_action = menu.addAction("Send to i2i")
        send_to_ip_adapter_action = menu.addAction("Send to IP Adapter")
        send_to_controlnet_action = menu.addAction("Send to Controlnet")
        action = menu.exec(global_pos)
        if action == save_action:
            self.save_image_dialog()
        if action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.original_pixmap)
        if action == send_to_i2i_action:
            self.source_tab.i2i_image_label.input_image = self.original_pixmap
            self.source_tab.i2i_image_label.image_view.add_pixmap(self.original_pixmap)
        if action == send_to_ip_adapter_action:
            self.source_tab.ipadapter_image_label.input_image = self.original_pixmap
            self.source_tab.ipadapter_image_label.image_view.add_pixmap(self.original_pixmap)
        if action == send_to_controlnet_action:
            self.source_tab.controlnet_image_label.input_image = self.original_pixmap
            self.source_tab.controlnet_image_label.image_view.add_pixmap(self.original_pixmap)

    def save_image_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Image",
            "image.png",
            "Images (*.png *.jpg *.bmp)"
        )
        if file_path:
            self.original_pixmap.save(file_path)

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
        if enable_ticks is True:
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
        self.clear_gallery_checkbox = QCheckBox("Clear Gallery")
        self.gallery = ImageGalleryViewer(self, self.parent)
        self.column_slider.slider.valueChanged.connect(self.gallery.tile_images)

        config_layout = QHBoxLayout()
        config_layout.addLayout(self.column_slider)
        config_layout.addWidget(self.clear_gallery_checkbox)
        self.addLayout(config_layout)
        self.addWidget(self.gallery)


class ImageGalleryViewer(QGraphicsView):
    def __init__(self, top_layout, parent):
        super().__init__()
        self.parent = parent
        self.top_layout = top_layout
        self.gallery = QGraphicsScene()
        self.full_image_view = QGraphicsScene()
        self.setScene(self.gallery)

    def add_pixmap(self, pixmap, source_tab):
        pixmap_item: ClickablePixmap = ClickablePixmap(pixmap, self, self.parent, source_tab)
        self.gallery.addItem(pixmap_item)

    def tile_images(self):
        cur_x = 0
        cur_y = 0
        image_height = 0
        width = self.viewport().width()
        tile_width = width / self.top_layout.column_slider.slider.value()
        for image in self.gallery.items():
            scaled_pixmap = image.original_pixmap.scaledToWidth(tile_width, Qt.SmoothTransformation)
            if scaled_pixmap.size().height() > image_height:
                image_height = scaled_pixmap.size().height()
        for image in self.gallery.items():
            scaled_pixmap = image.original_pixmap.scaledToWidth(tile_width, Qt.SmoothTransformation)
            image.setPixmap(scaled_pixmap)
            image.setPos(cur_x, cur_y)
            if cur_x + tile_width >= width:
                cur_y = cur_y + image_height
                cur_x = 0
            else:
                cur_x = cur_x + tile_width
        self.gallery.setSceneRect(0, 0, width, cur_y + image_height)


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

        self.enable_checkbox = QCheckBox(f"Enable {name} input")
        self.load_image_button = QPushButton("Load")
        self.load_image_button.clicked.connect(self.load_image)
        self.image_view = ScalingImageView()

        self.image_layout = QVBoxLayout()
        self.enable_layout = QHBoxLayout()
        self.enable_layout.addWidget(self.enable_checkbox)
        self.enable_layout.addWidget(self.load_image_button)
        self.image_layout.addLayout(self.enable_layout)
        self.image_layout.addWidget(self.image_view)
        self.addLayout(self.image_layout)

    def load_image(self):
        self.image_file_path = QFileDialog.getOpenFileName(self.source_widget, str("Open Image"), "~", str("Image Files (*.png *.jpg *.webp)"))[0]
        self.input_image = QPixmap(self.image_file_path)
        self.image_view.add_pixmap(self.input_image)


class ParagraphInputBox(QVBoxLayout):
    def __init__(self, label):
        super().__init__()
        self.label = QLabel(label)
        self.addWidget(self.label)
        self.input = QTextEdit(acceptRichText=False)
        self.addWidget(self.input)

class QueueObjectWidget(QFrame):
    def __init__(self, queue_object, hex_color, request_queue, queue_view):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

        self.queue_object = queue_object
        self.hex_color = hex_color
        self.request_queue = request_queue
        self.queue_view = queue_view

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

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

        self.type_label = QLabel(self.queue_object.__class__.__name__)
        self.prompt_separator = QFrame(frameShape=QFrame.Shape.HLine, frameShadow=QFrame.Shadow.Plain, lineWidth=10)
        self.prompt_separator.setStyleSheet(f"color: #888888; background-color: #888888;")
        self.prompt_label = QLabel(self.queue_object.prompt, wordWrap=True)
        self.status_label = QLabel("Queued")

        self.main_layout.addWidget(self.prompt_container, stretch=20)
        self.main_layout.addWidget(self.status_container)
        self.prompt_layout.addWidget(self.type_label)
        self.prompt_layout.addWidget(self.prompt_separator)
        self.prompt_layout.addWidget(self.prompt_label)
        self.status_layout.addWidget(self.status_label)


class QueueViewer(QScrollArea):
    def __init__(self):
        super().__init__()
        self.container_widget = QWidget()
        self.setWidget(self.container_widget)
        self.setWidgetResizable(True)

        self.main_layout = QVBoxLayout(self.container_widget)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.addStrut(250)

    def add_queue_item(self, queue_item, request_queue, queue_view, hex_color):
        queue_widget = QueueObjectWidget(queue_item, hex_color, request_queue, queue_view)
        self.main_layout.addWidget(queue_widget)
        return queue_widget

    def del_queue_item(self, queue_item):
        self.main_layout.removeWidget(queue_item)


class ScalingImageView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.gallery = QGraphicsScene()
        self.setScene(self.gallery)
        self.default_image = QPixmap("assets/chili.png")
        self.original_image = self.default_image
        self.add_pixmap(self.default_image)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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