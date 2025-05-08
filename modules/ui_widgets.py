from PySide6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QGraphicsView, QGraphicsScene,
                               QGraphicsPixmapItem, QLabel, QLineEdit, QCheckBox, QMenu, QFileDialog)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

class ClickablePixmap(QGraphicsPixmapItem):
    def __init__(self, original_pixmap, gallery):
        super().__init__(original_pixmap)
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
                fullscreen_pixmap = ClickablePixmap(self.original_pixmap, self.gallery)
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
        action = menu.exec(global_pos)
        if action == save_action:
            self.save_image_dialog()
        if action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.original_pixmap)

    def save_image_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Image",
            "image.png",
            "Images (*.png *.jpg *.bmp)"
        )
        if file_path:
            self.original_pixmap.save(file_path)


class ImageGalleryViewer(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.gallery = QGraphicsScene()
        self.full_image_view = QGraphicsScene()
        self.setScene(self.gallery)
        self.default_image = QPixmap("assets/chili.png")
        self.add_pixmap(self.default_image)

    def add_pixmap(self, pixmap):
        pixmap_item: ClickablePixmap = ClickablePixmap(pixmap, self)
        self.gallery.addItem(pixmap_item)

    def tile_images(self):
        cur_x = 0
        cur_y = 0
        image_height = 0
        columns = 3
        width = self.viewport().width()
        tile_width = width / columns
        for image in self.gallery.items():
            scaled_pixmap = image.original_pixmap.scaledToWidth(tile_width, Qt.SmoothTransformation)
            if scaled_pixmap.size().height() > image_height:
                image_height = scaled_pixmap.size().height()
        for image in self.gallery.items():
            scaled_pixmap = image.original_pixmap.scaledToWidth(tile_width, Qt.SmoothTransformation)
            image.setPixmap(scaled_pixmap)
            image.setPos(cur_x, cur_y)
            if cur_x + tile_width == width:
                cur_y = cur_y + image_height
                cur_x = 0
            else:
                cur_x = cur_x + tile_width

    def resizeEvent(self, event):
        """Resize event to ensure the images fit within the view and re-tile them."""
        super().resizeEvent(event)
        self.tile_images()  # Fit the image to the window size


class ImageInputBox(QHBoxLayout):
    def __init__(self, source_widget, default_image_path="assets/chili.png", width=250):
        super().__init__()
        self.source_widget = source_widget
        self.default_image_path = default_image_path
        self.image_file_path = None
        self.width = width

        self.enable_checkbox = QCheckBox("Enable Image input")
        self.load_image_button = QPushButton("Load")
        self.load_image_button.clicked.connect(self.load_image)
        self.input_image = QPixmap(self.default_image_path).scaledToWidth(width)
        self.input_image_label = QLabel()
        self.input_image_label.setPixmap(self.input_image)

        self.image_layout = QVBoxLayout()
        self.enable_layout = QHBoxLayout()
        self.enable_layout.addWidget(self.enable_checkbox)
        self.enable_layout.addWidget(self.load_image_button)
        self.image_layout.addLayout(self.enable_layout)
        self.image_layout.addWidget(self.input_image_label)
        self.addLayout(self.image_layout)

    def load_image(self):
        self.image_file_path = QFileDialog.getOpenFileName(self.source_widget, str("Open Image"), "~", str("Image Files (*.png *.jpg)"))[0]
        self.input_image = QPixmap(self.image_file_path).scaledToWidth(self.width)
        self.input_image_label.setPixmap(self.input_image)

class ParagraphInputBox(QVBoxLayout):
    def __init__(self, label):
        super().__init__()
        self.label = QLabel(label)
        self.addWidget(self.label)
        self.input = QTextEdit(acceptRichText=False)
        self.addWidget(self.input)

class SingleLineInputBox(QHBoxLayout):
    def __init__(self, label, placeholder_text=None, parent=None):
        super().__init__(parent)
        self.label = QLabel(label)
        if placeholder_text:
            self.input = QLineEdit(placeholderText=placeholder_text)
        else:
            self.input = QLineEdit()
        self.addWidget(self.label)
        self.addWidget(self.input)


