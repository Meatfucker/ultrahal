from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QLineEdit
from PySide6.QtCore import Qt
from qasync import asyncSlot


class LlmChat(QWidget):
    def __init__(self, avernus_client):
        super().__init__()
        self.avernus_client = avernus_client
        self.history = None

        # Main layout (horizontal)
        main_layout = QHBoxLayout()

        # Left-side chat layout
        chat_layout = QVBoxLayout()
        self.text_display = QTextEdit(readOnly=True)
        self.text_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        chat_layout.addWidget(self.text_display, stretch=5)
        self.text_input = ShiftEnterTextEdit(on_shift_enter_callback=self.on_submit)
        chat_layout.addWidget(self.text_input, stretch=1)
        main_layout.addLayout(chat_layout, stretch=3)  # Left section

        # Right-side config layout
        config_layout = QVBoxLayout()
        config_layout.addStretch(1)
        # Group label and input in a horizontal layout
        model_repo_layout = QHBoxLayout()
        self.model_repo_label = QLabel("Model Repo:")
        self.model_repo_input = QLineEdit()
        model_repo_layout.addWidget(self.model_repo_label)
        model_repo_layout.addWidget(self.model_repo_input)
        config_layout.addLayout(model_repo_layout)

        self.clear_history_button = QPushButton("Clear History")
        self.clear_history_button.clicked.connect(self.clear_history)
        config_layout.addWidget(self.clear_history_button, stretch=1)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        config_layout.addWidget(self.submit_button)
        main_layout.addLayout(config_layout, stretch=1)  # Right section

        self.setLayout(main_layout)

    def clear_history(self):
        self.history = None
        self.text_display.clear()

    @asyncSlot()
    async def on_submit(self):
        self.submit_button.setText("Generating")
        self.submit_button.setDisabled(True)
        self.text_input.setDisabled(True)
        await self.generate()
        self.submit_button.setText("Submit")
        self.submit_button.setDisabled(False)
        self.text_input.setDisabled(False)

    async def generate(self):
        input_text = self.text_input.toPlainText()
        model_name = self.model_repo_input.text()
        if model_name == "":
            model_name = "Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4"

        if self.history is None:
            response = await self.avernus_client.llm_chat(input_text, model_name=model_name)
        else:
            gen_history = self.history.get("history", [])
            response = await self.avernus_client.llm_chat(input_text, messages=gen_history, model_name=model_name)
        if isinstance(response, str):
            await self.add_history("user", input_text)
            await self.add_history("assistant", response)
            # formatted_input = self.ansi_to_html(input_text)
            # formatted_response = self.ansi_to_html(response)
            # self.text_display.insertHtml(f"<br><b>User:</b> {formatted_input}<br>")
            # self.text_display.insertHtml(f"<br><b>Avernus:</b> {formatted_response}<br>")
            font = self.text_display.currentFont()
            font.setBold(True)
            self.text_display.insertPlainText("User: ")
            font.setBold(False)
            self.text_display.insertPlainText(f"{input_text}\n\r")
            self.text_display.insertPlainText(f"Assistant: {response}\n\r")
            self.text_input.clear()

    async def add_history(self, role, content):
        """Adds each message to the history."""
        if self.history is None:
            self.history = {"history": []}
        self.history["history"].append({"role": role, "content": content})

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

