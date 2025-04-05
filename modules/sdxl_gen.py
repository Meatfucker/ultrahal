import asyncio
import base64
import io
import math
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QPushButton, QGraphicsView, QGraphicsScene,
                               QGraphicsPixmapItem, QLabel, QLineEdit, QCheckBox, QMenu, QFileDialog)
from PySide6.QtGui import QPixmap, QContextMenuEvent
from PySide6.QtCore import Qt
from modules.client import AvernusClient

class SdxlGen(QWidget):
    def __init__(self, avernus_client):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.original_images = []  # Store the original images
        self.scaled_images = []  # Store the scaled images
        # Main layout (horizontal)
        main_layout = QHBoxLayout()

        image_layout = QVBoxLayout()
        # Graphics View for Image Display
        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHint(self.graphics_view.renderHints())  # Enable smooth rendering
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        # Load and display default image
        self.default_image = QPixmap("assets/chili.png")
        self.pixmap_item = QGraphicsPixmapItem(self.default_image)
        self.scene.addItem(self.pixmap_item)
        image_layout.addWidget(self.graphics_view, stretch=5)
        main_layout.addLayout(image_layout, stretch=3)  # Left section

        config_layout = QVBoxLayout()
        # Prompt input label and box
        self.prompt_label = QLabel("Prompt")
        config_layout.addWidget(self.prompt_label)
        self.prompt_input = ShiftEnterTextEdit(on_shift_enter_callback=self.on_submit)
        config_layout.addWidget(self.prompt_input)
        # Negative prompt input label and box
        self.negative_prompt_label = QLabel("Negative Prompt")
        config_layout.addWidget(self.negative_prompt_label)
        self.negative_prompt_input = ShiftEnterTextEdit(on_shift_enter_callback=self.on_submit)

        config_layout.addWidget(self.negative_prompt_input)
        # Width layout containing label and input box
        width_layout = QHBoxLayout()
        self.width_label = QLabel("Width:")
        self.width_input = QLineEdit()
        width_layout.addWidget(self.width_label)
        width_layout.addWidget(self.width_input)
        config_layout.addLayout(width_layout)
        # Height layout containing label and input box
        height_layout = QHBoxLayout()
        self.height_label = QLabel("Height:")
        self.height_input = QLineEdit()
        height_layout.addWidget(self.height_label)
        height_layout.addWidget(self.height_input)
        config_layout.addLayout(height_layout)
        # Steps layout containing label and input box
        steps_layout = QHBoxLayout()
        self.steps_label = QLabel("Steps:")
        self.steps_input = QLineEdit()
        steps_layout.addWidget(self.steps_label)
        steps_layout.addWidget(self.steps_input)
        config_layout.addLayout(steps_layout)
        # Batch size layout containing label and input box
        batch_size_layout = QHBoxLayout()
        self.batch_size_label = QLabel("Batch Size:")
        self.batch_size_input = QLineEdit()
        batch_size_layout.addWidget(self.batch_size_label)
        batch_size_layout.addWidget(self.batch_size_input)
        config_layout.addLayout(batch_size_layout)
        self.prompt_enhance_checkbox = QCheckBox("Enhance Prompt")
        config_layout.addWidget(self.prompt_enhance_checkbox)
        # Submit button
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        config_layout.addWidget(self.submit_button)
        main_layout.addLayout(config_layout, stretch=1)  # Left section



        self.setLayout(main_layout)

        # Ensure the image fits initially
        self.update_image_fit()


    def resizeEvent(self, event):
        """Resize event to ensure the images fit within the view and re-tile them."""
        super().resizeEvent(event)
        self.update_image_fit()  # Fit the image to the window size
        self.retile_images()  # Retile the images to fit the new size

    def retile_images(self):
        """Re-tile the images to fit the resized window."""
        view_width = self.graphics_view.viewport().width()
        view_height = self.graphics_view.viewport().height()
        images = self.scene.items()
        if not images:
            return

        num_images = len(images)
        grid_size = math.ceil(math.sqrt(num_images))  # Find the closest integer greater than or equal to the sqrt of num_images
        tile_width = view_width // grid_size
        tile_height = view_height // grid_size
        x_offset = 0
        y_offset = 0

        for i, pixmap_item in enumerate(images):
            if isinstance(pixmap_item, QGraphicsPixmapItem):  # Ensure we only modify the image items
                pixmap_item.setPos(x_offset, y_offset)
                # Calculate the next image's position
                if (i + 1) % grid_size == 0:  # If we've reached the end of the row, move to the next row
                    x_offset = 0
                    y_offset += tile_height
                else:
                    x_offset += tile_width


    def update_image_fit(self):
        """Scale the view to fit all pixmap items in the scene."""
        scene_rect = self.scene.itemsBoundingRect()
        self.graphics_view.fitInView(scene_rect, Qt.KeepAspectRatio)

    def on_submit(self):
        """Wrapper to call the async generate function properly."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.generate())
        finally:
            loop.close()

    async def generate(self):
        """API call to generate the images and convert them from base64"""
        prompt = self.prompt_input.toPlainText()
        negative_prompt = self.negative_prompt_input.toPlainText()
        width = self.width_input.text()
        height = self.height_input.text()
        steps = self.steps_input.text()
        batch_size = self.batch_size_input.text()
        kwargs = {}
        if negative_prompt != "":
            kwargs["negative_prompt"] = negative_prompt
        if width != "":
            kwargs["width"] = int(width)
        if height != "":
            kwargs["height"] = int(height)
        if steps != "":
            kwargs["steps"] = int(steps)
        if batch_size != "":
            kwargs["batch_size"] = int(batch_size)
        if self.prompt_enhance_checkbox.isChecked():
            prompt = await self.avernus_client.llm_chat(f"Turn the following prompt into a three sentence visual description of it. Here is the prompt: {prompt}")
        base64_images = await self.avernus_client.sdxl_image(prompt, **kwargs)
        images = await self.base64_to_images(base64_images)
        await self.display_images(images)

    async def display_images(self, images):
        """Display images in a tiled grid pattern."""
        self.scene.clear()
        view_width = self.graphics_view.viewport().width()
        view_height = self.graphics_view.viewport().height()
        num_images = len(images)
        grid_size = math.ceil(math.sqrt(num_images))  # Find the closest integer greater than or equal to the sqrt of num_images
        tile_width = view_width // grid_size
        tile_height = view_height // grid_size
        x_offset = 0
        y_offset = 0

        for i, img_file in enumerate(images):
            pixmap = QPixmap()
            pixmap.loadFromData(img_file.getvalue())
            # Resize the image to fit within the tile size
            scaled_pixmap = pixmap.scaled(tile_width, tile_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Store the original image in the list (unscaled)
            self.original_images.append(img_file)
            # Add the scaled image to the scene
            pixmap_item = ClickablePixmapItem(scaled_pixmap, original_pixmap=pixmap)
            self.scene.addItem(pixmap_item)
            # Add the scaled image to the scaled_images list for reference
            self.scaled_images.append(pixmap_item)
            # Calculate the next image's position
            if (i + 1) % grid_size == 0:  # If we've reached the end of the row, move to the next row
                x_offset = 0
                y_offset += tile_height
            else:
                x_offset += tile_width

        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.retile_images()  # Retile the images to fit the new size
        self.update_image_fit()

    @staticmethod
    async def base64_to_images(base64_images):
        """Converts a list of base64 images into a list of file-like objects."""
        image_files = []
        for base64_image in base64_images:
            img_data = base64.b64decode(base64_image)  # Decode base64 string
            img_file = io.BytesIO(img_data)  # Convert to file-like object
            image_files.append(img_file)

        return image_files


class ClickablePixmapItem(QGraphicsPixmapItem):
    def __init__(self, pixmap, original_pixmap, parent=None):
        super().__init__(pixmap, parent)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        self.is_full_screen = False
        self.original_pos = None
        self.original_size = pixmap.size()
        self.original_pixmap = original_pixmap

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_full_screen()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.screenPos())

    def toggle_full_screen(self):
        """Toggle between full-screen and original view."""
        if self.is_full_screen:
            # Return to original size and position
            self.setPixmap(self.pixmap().scaled(self.original_size))  # Reset the image to original size
            self.setPos(self.original_pos)  # Reset the position
            self.setZValue(0)  # Reset the Z-order to default
            self.is_full_screen = False  # Set full-screen mode off
        else:
            # Save the current position and size for restoring later
            self.original_pos = self.pos()
            self.original_size = self.pixmap().size()

            # Set the image to fill the display area
            view_width = self.scene().views()[0].viewport().width()  # Get the width of the view
            view_height = self.scene().views()[0].viewport().height()  # Get the height of the view

            scaled_pixmap = self.original_pixmap.scaled(view_width, view_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled_pixmap)  # Set the image to fill the view

            self.setPos(0, 0)  # Move the image to the top-left corner

            self.setZValue(1)  # Set the Z-order to be above the other images
            self.is_full_screen = True  # Set full-screen mode on

    def show_context_menu(self, global_pos):
        menu = QMenu()
        save_action = menu.addAction("Save Image As...")
        action = menu.exec(global_pos)
        if action == save_action:
            self.save_image_dialog()

    def save_image_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Image",
            "image.png",
            "Images (*.png *.jpg *.bmp)"
        )
        if file_path:
            self.original_pixmap.save(file_path)


class ShiftEnterTextEdit(QTextEdit):
    def __init__(self, parent=None, on_shift_enter_callback=None):
        super().__init__(parent, acceptRichText=False)
        self.on_shift_enter_callback = on_shift_enter_callback

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)) and (event.modifiers() & Qt.ShiftModifier):
            if self.on_shift_enter_callback:
                self.on_shift_enter_callback()
        else:
            super().keyPressEvent(event)

