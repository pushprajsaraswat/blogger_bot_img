"""Single message bubble with streaming support."""
from __future__ import annotations
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp
from ui.widgets.markdown_view import MarkdownView

class MessageBubble(BoxLayout):
    def __init__(self, role: str, content: str = "", is_streaming: bool = False, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, padding=dp(8), spacing=dp(4), **kwargs)
        self.role = role
        self.is_streaming = is_streaming
        self._content = content

        # Role badge
        badge = Label(text=role.capitalize(), size_hint_y=None, height=dp(20),
                      halign='left', valign='middle', bold=True,
                      color=(0.6,0.6,0.6,1) if role=='assistant' else (0.3,0.6,1,1))
        self.add_widget(badge)

        # Content
        self.view = MarkdownView(content)
        self.add_widget(self.view)
        self.bind(minimum_height=self.setter('height'))

    def append_token(self, token: str):
        self._content += token
        self.view.set_markdown(self._content)  # re-render (simple, ok for Phase 1)

    def finalize(self):
        self.is_streaming = False
