import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QSizePolicy
from PySide6.QtCore import QTimer
from qasync import asyncSlot
from modules.ui_widgets import SingleLineInputBox, ModelPickerWidget, LLMHistoryWidget


class LlmTab(QWidget):
    def __init__(self, avernus_client, tabs):
        super().__init__()
        self.avernus_client = avernus_client
        self.tabs = tabs
        self.queue_tab = self.tabs.widget(1)
        self.queue_view = self.queue_tab.queue_view

        self.text_input = QTextEdit(acceptRichText=False)
        self.history_viewer = LLMHistoryWidget(self)
        self.model_picker = ModelPickerWidget("llm")
        self.clear_history_button = QPushButton("Clear History")
        self.clear_history_button.clicked.connect(self.clear_history)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setStyleSheet("""
                    QPushButton {
                        font-size: 20px;
                    }
                """)

        main_layout = QHBoxLayout()
        chat_layout = QVBoxLayout()
        config_layout = QVBoxLayout()
        config_layout.addStretch(1)
        main_layout.addLayout(chat_layout, stretch=3)
        main_layout.addLayout(config_layout)
        chat_layout.addWidget(self.history_viewer, stretch=5)
        chat_layout.addWidget(self.text_input, stretch=1)
        config_layout.addLayout(self.model_picker)
        config_layout.addWidget(self.clear_history_button, stretch=1)
        config_layout.addWidget(self.submit_button)

        self.setLayout(main_layout)

    def clear_history(self):
        self.history_viewer.clear_history()

    @asyncSlot()
    async def on_submit(self):
        self.submit_button.setDisabled(True)
        input_text = self.text_input.toPlainText()
        model_name = self.model_picker.model_list_picker.currentText()
        request = LLMRequest(self.avernus_client, self, input_text, model_name)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#3F1507")
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

    @asyncSlot()
    async def on_reroll(self, input_text, history):
        self.submit_button.setDisabled(True)
        model_name = self.model_picker.model_list_picker.currentText()
        request = LLMRerollRequest(self.avernus_client, self, input_text, model_name, history)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, "#5F3527")
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

    async def add_history(self, role, content, hex_color="#444444"):
        """Adds each message to the history."""
        self.history_viewer.add_message(role=role, message=content, hex_color=hex_color)


class LLMRequest:
    def __init__(self, avernus_client, tab, input_text, model_name):
        self.avernus_client = avernus_client
        self.tab = tab
        self.prompt = input_text
        self.model_name = model_name
        self.queue_info = None

    async def run(self):
        start_time = time.time()
        self.ui_item.status_label.setText("Running")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #004400;")
        await self.generate()
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.ui_item.status_label.setText(f"Finished\n{elapsed_time:.2f}s")
        self.ui_item.status_container.setStyleSheet(f"color: #ffffff; background-color: #440000;")

    async def generate(self):
        if self.model_name == "":
            self.model_name = "Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4"
        print(f"LLM: {self.prompt}, {self.model_name}")
        if self.tab.history_viewer.get_history() is None:
            response = await self.avernus_client.llm_chat(self.prompt, model_name=self.model_name)
        else:
            gen_history = self.tab.history_viewer.get_history()
            response = await self.avernus_client.llm_chat(self.prompt, messages=gen_history, model_name=self.model_name)
        if isinstance(response, str):
            await self.tab.add_history("user", self.prompt, "#002200")
            await self.tab.add_history("assistant", response, "#000022")
            self.tab.text_input.clear()
            self.tab.submit_button.setDisabled(False)


class LLMRerollRequest(LLMRequest):
    def __init__(self, avernus_client, tab, input_text, model_name, history):
        super().__init__(avernus_client, tab, input_text, model_name)
        self.history = history

    async def generate(self):
        if self.model_name == "":
            self.model_name = "Goekdeniz-Guelmez/Josiefied-Qwen2.5-14B-Instruct-abliterated-v4"
        print(f"LLM: {self.prompt}, {self.model_name}")
        if self.tab.history_viewer.get_history() is None:
            response = await self.avernus_client.llm_chat(self.prompt, model_name=self.model_name)
        else:
            gen_history = self.tab.history_viewer.get_history()
            response = await self.avernus_client.llm_chat(self.prompt, messages=gen_history, model_name=self.model_name)
        if isinstance(response, str):
            await self.tab.add_history("user", self.prompt, "#002200")
            await self.tab.add_history("assistant", response, "#000022")
            self.tab.text_input.clear()
            self.tab.submit_button.setDisabled(False)
