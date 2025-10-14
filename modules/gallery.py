from PySide6.QtWidgets import QHBoxLayout, QWidget

from modules.avernus_client import AvernusClient
from modules.ui_widgets import ImageGallery


class GalleryTab(QWidget):
    def __init__(self,
                 avernus_client: AvernusClient, ultrahal):
        super().__init__()
        self.avernus_client = avernus_client
        self.ultrahal = ultrahal
        self.gallery = ImageGallery(self)
        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.gallery, stretch=6)
        self.setLayout(self.main_layout)
