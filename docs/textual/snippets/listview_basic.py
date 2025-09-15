from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label


class ListViewDemo(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            ListItem(Label("Install")),
            ListItem(Label("Build")),
            ListItem(Label("Release")),
            id="targets",
        )
        yield Footer()


if __name__ == "__main__":
    ListViewDemo().run()
