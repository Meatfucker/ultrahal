from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
from qasync import asyncSlot
from modules.ui_widgets import SingleLineInputBox


class LlmTab(QWidget):
    def __init__(self, avernus_client):
        super().__init__()
        self.avernus_client = avernus_client
        self.history = None

        self.text_display = QTextEdit(readOnly=True)
        self.text_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_input = QTextEdit(acceptRichText=False)
        self.model_repo_label = SingleLineInputBox("Model Repo:", placeholder_text="Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4")
        self.clear_history_button = QPushButton("Clear History")
        self.clear_history_button.clicked.connect(self.clear_history)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)

        main_layout = QHBoxLayout()
        chat_layout = QVBoxLayout()
        config_layout = QVBoxLayout()
        config_layout.addStretch(1)
        main_layout.addLayout(chat_layout, stretch=3)
        main_layout.addLayout(config_layout, stretch=1)
        chat_layout.addWidget(self.text_display, stretch=5)
        chat_layout.addWidget(self.text_input, stretch=1)
        chat_layout.addWidget(self.submit_button)
        config_layout.addLayout(self.model_repo_label)
        config_layout.addWidget(self.clear_history_button, stretch=1)

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
        model_name = self.model_repo_label.input.text()
        if model_name == "":
            model_name = "Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4"
        print(f"LLM: {input_text}, {model_name}")
        if self.history is None:
            response = await self.avernus_client.llm_chat(input_text, model_name=model_name)
        else:
            gen_history = self.history.get("history", [])
            response = await self.avernus_client.llm_chat(input_text, messages=gen_history, model_name=model_name)
        if isinstance(response, str):
            await self.add_history("user", input_text)
            await self.add_history("assistant", response)
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
