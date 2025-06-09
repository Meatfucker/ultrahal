import json
import os
import sys
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QGraphicsView, QGraphicsScene,
                               QGraphicsPixmapItem, QLabel, QLineEdit, QCheckBox, QMenu, QFileDialog, QSlider, QWidget,
                               QFrame, QSizePolicy, QScrollArea, QMessageBox, QDialog, QGridLayout, QLayout, QComboBox,
                               QInputDialog, QButtonGroup)
from PySide6.QtGui import QMouseEvent, QPixmap, QPainter, QPaintEvent, QPen, QColor, QCursor, QFont
from PySide6.QtCore import Qt, QSize


class ClickablePixmap(QGraphicsPixmapItem):
    def __init__(self, original_pixmap, gallery, parent, tabs):
        super().__init__(original_pixmap)
        self.parent = parent
        self.tabs = tabs
        self.queue_tab = self.tabs.widget(1)
        self.sdxl_tab = self.tabs.widget(3)
        self.sdxl_inpaint_tab = self.tabs.widget(4)
        self.flux_tab = self.tabs.widget(5)
        self.flux_inpaint_tab = self.tabs.widget(6)
        self.flux_fill_tab = self.tabs.widget(7)
        self.queue_view = self.queue_tab.queue_view
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
                scaled_to_fit_pixmap = ClickablePixmap(self.original_pixmap, self.gallery, self.parent, self.tabs)
                scaled_to_fit_pixmap.setPixmap(scaled_pixmap)
                scaled_to_fit_pixmap.view_state = 2
                self.gallery.scaled_image_view.addItem(scaled_to_fit_pixmap)
                self.gallery.centerOn(0, 0)
                self.gallery.setScene(self.gallery.scaled_image_view)
            elif self.view_state == 2:
                width = self.gallery.viewport().width()
                self.gallery.full_image_view.clear()
                scaled_fullscreen_pixmap = self.original_pixmap.scaledToWidth(width, Qt.SmoothTransformation)
                fullscreen_pixmap = ClickablePixmap(self.original_pixmap, self.gallery, self.parent, self.tabs)
                fullscreen_pixmap.setPixmap(scaled_fullscreen_pixmap)
                fullscreen_pixmap.view_state = 3
                self.gallery.full_image_view.addItem(fullscreen_pixmap)
                self.gallery.centerOn(0, 0)
                self.gallery.setScene(self.gallery.full_image_view)
            elif self.view_state == 3:
                self.gallery.setScene(self.gallery.gallery)
                self.gallery.centerOn(0, 0)

        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())

    def show_context_menu(self, global_pos):
        menu = QMenu()
        save_action = menu.addAction("Save Image As...")
        copy_action = menu.addAction("Copy Image")
        sdxl_menu = menu.addMenu("SDXL")
        sdxl_inpaint_menu = menu.addMenu("SDXL Inpaint")
        flux_menu = menu.addMenu("Flux")
        flux_inpaint_menu = menu.addMenu("Flux Inpaint")
        sdxl_send_to_i2i = sdxl_menu.addAction("Send to I2I")
        sdxl_send_to_ipadapter = sdxl_menu.addAction("Send to IP Adapter")
        sdxl_sent_to_controlnet = sdxl_menu.addAction("Send to Controlnet")
        sdxl_send_to_inpaint = sdxl_inpaint_menu.addAction("Send to SDXL Inpaint")
        flux_send_to_i2i = flux_menu.addAction("Send to I2I")
        flux_send_to_ipadapter = flux_menu.addAction("Send to IP Adapter")
        flux_sent_to_controlnet = flux_menu.addAction("Send to Controlnet")
        flux_send_to_inpaint = flux_inpaint_menu.addAction("Send to Flux Inpaint")
        flux_send_to_fill = flux_inpaint_menu.addAction("Send to Flux Fill")


        action = menu.exec(global_pos)
        if action == save_action:
            self.save_image_dialog()
        if action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.original_pixmap)

        if action == sdxl_send_to_i2i:
            self.sdxl_tab.i2i_image_label.input_image = self.original_pixmap
            self.sdxl_tab.i2i_image_label.image_view.add_pixmap(self.original_pixmap)
        if action == sdxl_send_to_ipadapter:
            self.sdxl_tab.ipadapter_image_label.input_image = self.original_pixmap
            self.sdxl_tab.ipadapter_image_label.image_view.add_pixmap(self.original_pixmap)
        if action == sdxl_sent_to_controlnet:
            self.sdxl_tab.controlnet_image_label.input_image = self.original_pixmap
            self.sdxl_tab.controlnet_image_label.image_view.add_pixmap(self.original_pixmap)

        if action == sdxl_send_to_inpaint:
            self.sdxl_inpaint_tab.paint_area.set_image(self.original_pixmap)

        if action == flux_send_to_i2i:
            self.flux_tab.i2i_image_label.input_image = self.original_pixmap
            self.flux_tab.i2i_image_label.image_view.add_pixmap(self.original_pixmap)
        if action == flux_send_to_ipadapter:
            self.flux_tab.ipadapter_image_label.input_image = self.original_pixmap
            self.flux_tab.ipadapter_image_label.image_view.add_pixmap(self.original_pixmap)
        if action == flux_sent_to_controlnet:
            self.flux_tab.controlnet_image_label.input_image = self.original_pixmap
            self.flux_tab.controlnet_image_label.image_view.add_pixmap(self.original_pixmap)

        if action == flux_send_to_inpaint:
            self.flux_inpaint_tab.paint_area.set_image(self.original_pixmap)
        if action == flux_send_to_fill:
            self.flux_fill_tab.paint_area.set_image(self.original_pixmap)

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

    def add_pixmap(self, pixmap, tabs):
        pixmap_item: ClickablePixmap = ClickablePixmap(pixmap, self, self.parent, tabs)
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
        if self.image_file_path != "":
            self.input_image = QPixmap(self.image_file_path)
            self.image_view.add_pixmap(self.input_image)

class ModelPickerWidget(QVBoxLayout):
    def __init__(self, model_arch):
        super().__init__()
        self.data_list = []
        self.model_arch = model_arch
        self.json_path = f"{self.model_arch}.json"

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
        self.addWidget(self.model_list_picker)

        self.button_layout = QHBoxLayout()
        self.add_model_button = QPushButton("Add Model")
        self.add_model_button.clicked.connect(self.add_model)
        self.remove_model_button = QPushButton("Remove Model")
        self.remove_model_button.clicked.connect(self.remove_model)
        self.button_layout.addWidget(self.add_model_button)
        self.button_layout.addWidget(self.remove_model_button)

        self.addLayout(self.button_layout)

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
        with open(f"{self.model_arch}.json", "w") as f:
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

        self.main_layout = QVBoxLayout(self.container_widget)
        self.main_layout.setAlignment(Qt.AlignTop)
        self.main_layout.addStrut(250)

    def add_queue_item(self, queue_item, queue_view, hex_color):
        queue_widget = QueueObjectWidget(queue_item, hex_color, queue_view)
        self.main_layout.addWidget(queue_widget)
        return queue_widget

    def del_queue_item(self, queue_widget):
        self.main_layout.removeWidget(queue_widget)
        queue_widget.setParent(None)
        queue_widget.deleteLater()


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

    def sizeHint(self):
        #size = super().sizeHint()
        #side = max(size.width(), size.height())
        return QSize(20, 20)