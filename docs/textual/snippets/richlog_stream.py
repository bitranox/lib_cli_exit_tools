from __future__ import annotations

import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Button
from textual.containers import Horizontal


class StreamApp(App):
    CSS = """
    RichLog { border: tall $accent; }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        self.log = RichLog(highlight=True)
        yield self.log
        with Horizontal():
            yield Button("Run", id="run")
            yield Button("Cancel", id="cancel")
        yield Footer()

    async def _run_cmd(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            "python",
            "-c",
            "import time; [print(i) or time.sleep(0.3) for i in range(10)]",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def pump(stream, label: str):
            assert stream is not None
            while True:
                line = await stream.readline()
                if not line:
                    break
                self.log.write(f"{label} {line.decode().rstrip()}\n")

        await asyncio.gather(pump(self._proc.stdout, "stdout:"), pump(self._proc.stderr, "stderr:"))
        rc = await self._proc.wait()
        self.log.write(f"exit={rc}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            self.set_timer(0, lambda: asyncio.create_task(self._run_cmd()))
        elif event.button.id == "cancel":
            if getattr(self, "_proc", None):
                try:
                    self._proc.send_signal(getattr(asyncio.subprocess, "signal", __import__("signal")).SIGINT)
                except Exception:
                    self._proc.terminate()


if __name__ == "__main__":
    StreamApp().run()
