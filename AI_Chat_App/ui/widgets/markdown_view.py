"""Markdown -> Kivy markup (subset) + code blocks with Pygments."""
from __future__ import annotations
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.codeinput import CodeInput
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments import highlight
import markdown
import re

class MarkdownView(BoxLayout):
    def __init__(self, md_text: str = "", **kwargs):
        super().__init__(orientation='vertical', spacing=4, size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter('height'))
        self.set_markdown(md_text)

    def set_markdown(self, md: str):
        self.clear_widgets()
        if not md.strip():
            return
        html = markdown.markdown(md, extensions=['fenced_code', 'tables', 'codehilite'])
        # Very simple HTML->Kivy widget conversion (good enough for Phase 1)
        for block in re.split(r'(<pre><code[^>]*>.*?</code></pre>)', html, flags=re.DOTALL):
            if block.startswith('<pre><code'):
                lang = re.search(r'class="language-(\w+)"', block)
                code = re.sub(r'<.*?>', '', block).strip()
                lexer = get_lexer_by_name(lang.group(1)) if lang else guess_lexer(code)
                # Use a read-only CodeInput for syntax highlight
                ci = CodeInput(text=code, readonly=True, lexer=lexer,
                               size_hint_y=None, height=min(300, len(code.splitlines())*20 + 20))
                self.add_widget(ci)
            else:
                # strip tags, keep simple markup
                clean = re.sub(r'<[^>]+>', '', block)
                if clean.strip():
                    lbl = Label(text=clean, markup=True, size_hint_y=None,
                                halign='left', valign='top', text_size=(self.width - 20, None))
                    lbl.bind(texture_size=lambda i, s: setattr(i, 'height', s[1]))
                    self.add_widget(lbl)
