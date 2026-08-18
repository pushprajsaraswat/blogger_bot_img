from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from database.repositories import list_providers, upsert_provider, get_provider
from providers.registry import refresh_all_models
import asyncio

class SettingsScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=10, **kwargs)
        self.add_widget(Label(text="Providers (BYOK)", size_hint_y=None, height=40, bold=True))
        self.list_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.list_box.bind(minimum_height=self.list_box.setter('height'))
        self.add_widget(self.list_box)
        self._refresh()

    def _refresh(self):
        self.list_box.clear_widgets()
        asyncio.create_task(self._load())

    async def _load(self):
        providers = await list_providers()
        for p in providers:
            row = BoxLayout(size_hint_y=None, height=60, spacing=5)
            row.add_widget(Label(text=f"{p['name']} ({p['id']})", halign='left'))
            btn = Button(text="Edit Key", size_hint_x=0.3)
            btn.bind(on_press=lambda _, pid=p['id']: self._edit_key(pid))
            row.add_widget(btn)
            self.list_box.add_widget(row)
        # add new
        add_row = BoxLayout(size_hint_y=None, height=60)
        add_row.add_widget(Label(text="+ Add Provider"))
        self.list_box.add_widget(add_row)

    def _edit_key(self, pid):
        # simple popup not implemented in Phase 1 — just print
        print(f"Edit key for {pid} — implement popup later")
