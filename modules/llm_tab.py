from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
from qasync import asyncSlot
from modules.ui_widgets import SingleLineInputBox


class LlmTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client = avernus_client
        self.tabs = tabs
        self.queue_tab = self.tabs.widget(1)
        self.queue_view = self.queue_tab.queue_view
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
        input_text = self.text_input.toPlainText()
        model_name = self.model_repo_label.input.text()
        request = LLMRequest(self.avernus_client, self, input_text, model_name)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#3F1507")
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

    async def add_history(self, role, content):
        """Adds each message to the history."""
        if self.history is None:
            self.history = {"history": []}
        self.history["history"].append({"role": role, "content": content})

class LLMRequest:
    def __init__(self, avernus_client, tab, input_text, model_name):
        self.avernus_client = avernus_client
        self.tab = tab
        self.prompt = input_text
        self.model_name = model_name
        self.queue_info = None

    async def run(self):
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        self.ui_item.status_label.setText("Finished")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    async def generate(self):
        if self.model_name == "":
            self.model_name = "Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4"
        print(f"LLM: {self.prompt}, {self.model_name}")
        if self.tab.history is None:
            response = await self.avernus_client.llm_chat(self.prompt, model_name=self.model_name)
        else:
            gen_history = self.tab.history.get("history", [])
            response = await self.avernus_client.llm_chat(self.prompt, messages=gen_history, model_name=self.model_name)
        if isinstance(response, str):
            await self.tab.add_history("user", self.prompt)
            await self.tab.add_history("assistant", response)
            font = self.tab.text_display.currentFont()
            font.setBold(True)
            self.tab.text_display.insertPlainText("User: ")
            font.setBold(False)
            self.tab.text_display.insertPlainText(f"{self.prompt}\n\r")
            self.tab.text_display.insertPlainText(f"Assistant: {response}\n\r")
            self.tab.text_input.clear()



