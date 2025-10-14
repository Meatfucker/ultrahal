import time
from typing import cast

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
from qasync import asyncSlot

from modules.avernus_client import AvernusClient
from modules.queue import QueueTab
from modules.ui_widgets import LLMHistoryWidget, ModelPickerWidget, QueueObjectWidget, QueueViewer, VerticalTabWidget


class LlmTab(QWidget):
    def __init__(self, avernus_client: AvernusClient, tabs: VerticalTabWidget):
        super().__init__()
        self.avernus_client: AvernusClient = avernus_client
        self.tabs: VerticalTabWidget = tabs
        self.queue_tab: QueueTab = cast(QueueTab, self.tabs.named_widget("Queue"))
        self.queue_view: QueueViewer = self.queue_tab.queue_view
        self.queue_color: str = "#4c493d"

        self.text_input = QTextEdit(acceptRichText=False)
        self.history_viewer = LLMHistoryWidget(self)
        self.model_picker = ModelPickerWidget("llm")
        self.clear_history_button = QPushButton("Clear History")
        self.clear_history_button.clicked.connect(self.clear_history)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.on_submit)
        self.submit_button.setStyleSheet("""QPushButton {font-size: 20px;}""")

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
        self.setStyleSheet("""QTextEdit {border: none; background-color: #25252a; color: #ddd; font-size: 14px;}
                           LLMHistoryWidget {background-color: #25252a; color: #ddd; font-size: 14px;}""")

    def clear_history(self):
        self.history_viewer.clear_history()

    @asyncSlot()
    async def on_submit(self):
        self.queue_color: str = "#4c493d"
        input_text = self.text_input.toPlainText()
        model_name = self.model_picker.model_list_picker.currentText()
        request = LLMRequest(self.avernus_client, self, input_text, model_name)

        queue_item = self.queue_view.add_queue_item(request, self.queue_view, self.queue_color)
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

    @asyncSlot()
    async def on_reroll(self, input_text, history):
        self.queue_color: str = "#666152"
        model_name = self.model_picker.model_list_picker.currentText()
        request = LLMRerollRequest(self.avernus_client, self, input_text, model_name, history)
        queue_item = self.queue_view.add_queue_item(request, self.queue_view, self.queue_color)
        request.ui_item = queue_item
        self.tabs.parent().pending_requests.append(request)
        self.tabs.parent().request_event.set()

    async def add_history(self, role, content, hex_color="#444444"):
        """Adds each message to the history."""
        self.history_viewer.add_message(role=role, message=content, hex_color=hex_color)


class LLMRequest:
    def __init__(self,
                 avernus_client: AvernusClient,
                 tab: LlmTab,
                 input_text: str,
                 model_name: str):
        self.avernus_client = avernus_client
        self.tab = tab
        self.prompt = input_text
        self.model_name = model_name
        self.queue_info = None
        self.ui_item: QueueObjectWidget | None = None

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
            await self.tab.add_history("user", self.prompt, "#303040")
            await self.tab.add_history("assistant", response, "#303050")
            self.tab.text_input.clear()
            self.tab.submit_button.setDisabled(False)


class LLMRerollRequest(LLMRequest):
    def __init__(self,
                 avernus_client: AvernusClient,
                 tab: LlmTab,
                 input_text: str,
                 model_name: str,
                 history: list):
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
