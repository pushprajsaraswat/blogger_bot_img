"""Main chat screen — list of bubbles + input bar."""
from __future__ import annotations
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.metrics import dp
from ui.widgets.message_bubble import MessageBubble
from database.repositories import list_conversations, get_messages, add_message, create_conversation
from providers.registry import get_provider
from core.events import bus
from core.streaming import TokenStream
import asyncio
import uuid

class ChatScreen(BoxLayout):
    def __init__(self, conversation_id: str | None = None, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.conversation_id = conversation_id
        self._stream_task = None

        # History list
        self.history = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8), padding=dp(8))
        self.history.bind(minimum_height=self.history.setter('height'))
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.scroll.add_widget(self.history)
        self.add_widget(self.scroll)

        # Input bar
        bar = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(4), padding=dp(4))
        self.input = TextInput(hint_text='Message…', multiline=False, size_hint_x=0.85)
        self.input.bind(on_text_validate=self._on_send)
        send_btn = Button(text='➤', size_hint_x=0.15)
        send_btn.bind(on_press=lambda _: self._on_send(self.input))
        bar.add_widget(self.input)
        bar.add_widget(send_btn)
        self.add_widget(bar)

        # Load or create conversation
        Clock.schedule_once(lambda _: asyncio.create_task(self._init_conversation()))

    async def _init_conversation(self):
        if not self.conversation_id:
            # create new with defaults from settings
            from database.repositories import get_setting
            pid = await get_setting("default_provider", "openrouter")
            mid = await get_setting("default_model", f"{pid}_anthropic/claude-3.5-sonnet")
            self.conversation_id = await create_conversation(pid, mid)
        await self._load_history()

    async def _load_history(self):
        msgs = await get_messages(self.conversation_id)
        for m in msgs:
            self._add_bubble(m["role"], m["content"], is_streaming=False)
        self._scroll_bottom()

    def _add_bubble(self, role: str, content: str, is_streaming: bool = False) -> MessageBubble:
        bubble = MessageBubble(role, content, is_streaming)
        self.history.add_widget(bubble)
        return bubble

    def _scroll_bottom(self):
        Clock.schedule_once(lambda _: setattr(self.scroll, 'scroll_y', 0), 0)

    def _on_send(self, instance):
        text = self.input.text.strip()
        if not text:
            return
        self.input.text = ""
        # user bubble
        self._add_bubble("user", text)
        asyncio.create_task(self._run_assistant(text))

    async def _run_assistant(self, user_text: str):
        # persist user msg
        await add_message(self.conversation_id, "user", user_text)

        # build request
        from database.repositories import get_conversation
        conv = await get_conversation(self.conversation_id)
        msgs = [{"role": "system", "content": conv["system_prompt"] or ""}] if conv["system_prompt"] else []
        history = await get_messages(self.conversation_id)
        for m in history:
            msgs.append({"role": m["role"], "content": m["content"]})

        req = {
            "model": conv["model_id"].split("_", 1)[1],  # strip provider_
            "messages": msgs,
            "temperature": conv["temperature"],
            "top_p": conv["top_p"],
            "max_tokens": conv["max_tokens"],
            "stream": True,
        }

        provider = await get_provider(conv["provider_id"])
        assistant_bubble = self._add_bubble("assistant", "", is_streaming=True)

        stream = TokenStream(on_token=lambda t: Clock.schedule_once(lambda _: assistant_bubble.append_token(t)))

        try:
            await provider.chat(req, on_token=stream.on_token)
            await stream.wait_done()
            full = stream.text()
            assistant_bubble.finalize()
            await add_message(self.conversation_id, "assistant", full)
        except Exception as e:
            assistant_bubble.append_token(f"\n[Error: {e}]")
            assistant_bubble.finalize()
        self._scroll_bottom()
