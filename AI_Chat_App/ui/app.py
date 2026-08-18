"""Kivy App — manages screens, DB init, provider sync."""
from __future__ import annotations
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from database.db import Database
from providers.registry import refresh_all_models, close_all
from ui.screens.chat_screen import ChatScreen
from ui.screens.settings_screen import SettingsScreen
import asyncio

class RootScreen(Screen):
    pass

class ChatApp(App):
    def build(self):
        self.sm = ScreenManager()
        # Chat screen (default)
        chat_scr = Screen(name='chat')
        self.chat_view = ChatScreen()
        chat_scr.add_widget(self.chat_view)
        self.sm.add_widget(chat_scr)

        # Settings screen
        settings_scr = Screen(name='settings')
        settings_scr.add_widget(SettingsScreen())
        self.sm.add_widget(settings_scr)

        # Async init
        Clock.schedule_once(lambda _: asyncio.create_task(self._async_init()))
        return self.sm

    async def _async_init(self):
        await Database.init()
        await refresh_all_models()
        print("[App] Ready")

    def on_stop(self):
        asyncio.create_task(close_all())

if __name__ == '__main__':
    ChatApp().run()
