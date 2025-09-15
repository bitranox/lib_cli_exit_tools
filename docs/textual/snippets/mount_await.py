from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button


class MountAwaitApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Button("Add Box", id="add")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            box = Static("I was mounted and styled!")
            await self.mount(box)
            box.styles.border = ("tall", "green")


if __name__ == "__main__":
    MountAwaitApp().run()
