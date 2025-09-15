from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static


class BindingApp(App):
    BINDINGS = [
        ("r", "set_bg('red')", "Red"),
        ("g", "set_bg('green')", "Green"),
        ("b", "set_bg('blue')", "Blue"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Press R/G/B to change background")
        yield Footer()

    def action_set_bg(self, color: str) -> None:
        self.screen.styles.background = color


if __name__ == "__main__":
    BindingApp().run()
