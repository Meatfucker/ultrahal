from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
import sys


class Console(QWidget):
    def __init__(self):
        super().__init__()
        self.text_display = QTextEdit(readOnly=True)
        self.text_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        self.main_layout = QHBoxLayout()
        self.main_layout.addWidget(self.text_display)
        self.setLayout(self.main_layout)

        sys.stdout = self

    def write(self, message):
        self.text_display.insertPlainText(message)

    def flush(self):
        pass