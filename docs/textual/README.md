 (for this repo)

makThis is a pragmatic quick‑reference for building and debugging Textual UIs that match the versions we use here (Textual ≥ 6.x). It focuses on patterns we implemented in `scripts/menu_tui.py` (ListView + RichLog + async subprocess + Cancel).

## Install

- Dev extras (recommended):
  - `pip install -e .[dev]`
- Or just Textual: `pip install textual`
- Verify: `python -c "import textual,sys; print(sys.version, textual.__version__)"`

## App + compose

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class Hello(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Hello Textual")
        yield Footer()

if __name__ == "__main__":
    Hello().run()
```

## Mounting: schedule vs await

- `self.mount(widget)` schedules. If you need to update/query the widget immediately, `await self.mount(widget)` inside an async handler (e.g. `async def on_mount(...)`).

```python
# See snippets/mount_await.py
```

## ListView (compose safely)

Create items inside `compose` or after mount. For initial items:

```python
from textual.widgets import ListView, ListItem, Label

yield ListView(
    ListItem(Label("Item 1")),
    ListItem(Label("Item 2")),
    id="targets",
)
```

Adding later (after mount):

```python
lv = self.query_one("#targets", ListView)
await lv.append(ListItem(Label("New Item")))   # or lv.append(...) if in compose tick
```

## RichLog (Textual 6.x)

- Use `RichLog` (not `TextLog`).
- Append with `write()`.

```python
from textual.widgets import RichLog
log = RichLog(highlight=True)
log.write("Starting…")
```

## Async subprocess + live streaming

```python
# See snippets/richlog_stream.py
# gist: create_subprocess_exec + read stdout/stderr per line → log.write()
```

POSIX Cancel: `proc.send_signal(signal.SIGINT)`; Windows: `proc.terminate()`.

## Actions & key bindings

Bind keys to actions:

```python
# See snippets/actions_bindings.py
```

## CSS basics (inline)

```python
CSS = """
Screen { layout: horizontal; }
#right { width: 1fr; }
RichLog { border: tall $accent; }
"""
```

## Run the examples

```bash
python docs/textual/snippets/listview_basic.py
python docs/textual/snippets/richlog_stream.py
python docs/textual/snippets/mount_await.py
python docs/textual/snippets/actions_bindings.py
```

## Troubleshooting

- Nothing shows under `make`: ensure stdin/stdout is a TTY. We wire `/dev/tty` in Make.
- Textual import errors: check version (`textual.__version__`), install `pip install -e .[dev]`.
- MountError on ListView: don’t append before the ListView is mounted; yield items in `compose` or `await mount()` first.

