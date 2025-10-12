from __future__ import annotations

from click.testing import CliRunner
from collections.abc import Mapping, Sequence
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from typing import Protocol, TypedDict

from pytest import MonkeyPatch

import scripts.build as build
import scripts.cli as cli
import scripts.dev as dev
import scripts.install as install
import scripts.run_cli as run_cli
import scripts.test as test_script
from scripts._utils import RunResult
from scripts import _utils
from scripts import target_metadata


RunCommand = Sequence[str] | str
ModuleLike = ModuleType | SimpleNamespace


class RecordedOptions(TypedDict):
    check: bool
    capture: bool
    cwd: str | None
    env: Mapping[str, str] | None
    dry_run: bool


RunRecord = tuple[RunCommand, RecordedOptions]


class RunStub(Protocol):
    def __call__(
        self,
        cmd: RunCommand,
        *,
        check: bool = True,
        capture: bool = True,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        dry_run: bool = False,
    ) -> RunResult: ...


def _make_run_recorder(record: list[RunRecord]) -> RunStub:
    def _run(
        cmd: RunCommand,
        *,
        check: bool = True,
        capture: bool = True,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        dry_run: bool = False,
    ) -> RunResult:
        record.append(
            (
                cmd,
                {
                    "check": check,
                    "capture": capture,
                    "cwd": cwd,
                    "env": env,
                    "dry_run": dry_run,
                },
            ),
        )
        return RunResult(0, "", "")

    return _run


def test_get_project_metadata_fields():
    meta = _utils.get_project_metadata()
    assert meta.name == "lib_cli_exit_tools"
    assert meta.slug == "lib-cli-exit-tools"
    assert meta.import_package == "lib_cli_exit_tools"
    assert meta.coverage_source == "src/lib_cli_exit_tools"
    assert meta.github_tarball_url("1.2.3").endswith("/bitranox/lib_cli_exit_tools/archive/refs/tags/v1.2.3.tar.gz")


def test_build_script_uses_metadata(monkeypatch: MonkeyPatch) -> None:
    recorded: list[RunRecord] = []
    monkeypatch.setattr(build, "run", _make_run_recorder(recorded))
    runner = CliRunner()
    result = runner.invoke(cli.main, ["build"])
    assert result.exit_code == 0
    commands = [" ".join(cmd) if not isinstance(cmd, str) else cmd for cmd, _ in recorded]
    assert any("python -m build" in cmd for cmd in commands)


def test_dev_script_installs_dev_extras(monkeypatch: MonkeyPatch) -> None:
    recorded: list[RunRecord] = []
    monkeypatch.setattr(dev, "run", _make_run_recorder(recorded))
    runner = CliRunner()
    result = runner.invoke(cli.main, ["dev"])
    assert result.exit_code == 0
    first_command, _options = recorded[0]
    assert isinstance(first_command, list)
    assert first_command == [sys.executable, "-m", "pip", "install", "-e", ".[dev]"]


def test_install_script_installs_package(monkeypatch: MonkeyPatch) -> None:
    recorded: list[RunRecord] = []
    monkeypatch.setattr(install, "run", _make_run_recorder(recorded))
    runner = CliRunner()
    result = runner.invoke(cli.main, ["install"])
    assert result.exit_code == 0
    first_command, _options = recorded[0]
    assert isinstance(first_command, list)
    assert first_command == [sys.executable, "-m", "pip", "install", "-e", "."]


def test_run_cli_imports_dynamic_package(monkeypatch: MonkeyPatch) -> None:
    seen: list[str] = []

    def _run_cli_main(_args: Sequence[str] | None = None) -> int:
        return 0

    def fake_import(name: str) -> ModuleLike:
        seen.append(name)
        if name.endswith(".__main__"):
            return SimpleNamespace()
        if name.endswith(".cli"):
            return SimpleNamespace(main=_run_cli_main)
        raise AssertionError(f"unexpected import {name}")

    monkeypatch.setattr(run_cli, "import_module", fake_import)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["run"])
    assert result.exit_code == 0
    package = run_cli.PROJECT.import_package
    assert f"{package}.cli" in seen
    if len(seen) == 2:
        assert seen == [f"{package}.__main__", f"{package}.cli"]


def test_test_script_uses_pyproject_configuration(monkeypatch: MonkeyPatch) -> None:
    recorded: list[RunRecord] = []

    def _noop() -> None:
        return None

    def _always_false(_name: str) -> bool:
        return False

    monkeypatch.setattr(test_script, "bootstrap_dev", _noop)
    monkeypatch.setattr(_utils, "cmd_exists", _always_false)
    monkeypatch.setattr(test_script, "run", _make_run_recorder(recorded))
    runner = CliRunner()
    result = runner.invoke(cli.main, ["test"])
    assert result.exit_code == 0
    pytest_commands: list[list[str]] = []
    for cmd, _ in recorded:
        if isinstance(cmd, str):
            continue
        command_list = list(cmd)
        if command_list[:3] == ["python", "-m", "pytest"]:
            pytest_commands.append(command_list)
    assert pytest_commands, "pytest not invoked"
    assert any(f"--cov={test_script.COVERAGE_TARGET}" in " ".join(sequence) for sequence in pytest_commands)


def test_run_coverage_invokes_python_module(monkeypatch: MonkeyPatch) -> None:
    recorded: list[RunRecord] = []
    bootstrap_calls: list[str] = []

    def _bootstrap() -> None:
        bootstrap_calls.append("bootstrap")

    monkeypatch.setattr(test_script, "bootstrap_dev", _bootstrap)
    monkeypatch.setattr(test_script, "run", _make_run_recorder(recorded))

    # create stale coverage artefacts to ensure cleanup happens first
    Path(".coverage.stale").write_text("stale", encoding="utf-8")
    Path("coverage.xml").write_text("old", encoding="utf-8")
    Path("codecov.xml").write_text("old", encoding="utf-8")

    test_script.run_coverage()

    assert bootstrap_calls == ["bootstrap"]
    assert len(recorded) == 2

    first_cmd, first_opts = recorded[0]
    assert isinstance(first_cmd, list)
    assert first_cmd[:4] == [sys.executable, "-m", "coverage", "run"]
    assert first_cmd[4:7] == ["-m", "pytest", "-vv"]
    assert first_opts["capture"] is True
    assert first_opts["env"] is not None
    assert first_opts["env"].get("COVERAGE_NO_SQL") == "1"
    coverage_file = first_opts["env"].get("COVERAGE_FILE", "")
    assert coverage_file.endswith(".coverage")
    assert coverage_file != ".coverage"
    assert Path(coverage_file).is_absolute()

    second_cmd, second_opts = recorded[1]
    assert isinstance(second_cmd, list)
    assert second_cmd[:5] == [sys.executable, "-m", "coverage", "report", "-m"]
    assert second_opts["capture"] is True
    assert second_opts["env"] is not None
    assert second_opts["env"].get("COVERAGE_NO_SQL") == "1"
    assert second_opts["env"].get("COVERAGE_FILE") == coverage_file

    assert not Path(".coverage.stale").exists()
    assert not Path("coverage.xml").exists()
    assert not Path("codecov.xml").exists()


def test_cli_coverage_command_toggles_verbose(monkeypatch: MonkeyPatch) -> None:
    invoked: dict[str, bool] = {}

    def _cover(*, verbose: bool) -> None:
        invoked["verbose"] = verbose

    monkeypatch.setattr(test_script, "run_coverage", _cover)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["coverage", "--verbose"])

    assert result.exit_code == 0
    assert invoked == {"verbose": True}


def test_target_metadata_includes_coverage_entry() -> None:
    targets = target_metadata.get_targets()
    coverage_entries = [t for t in targets if t.name == "coverage"]
    assert coverage_entries
    (entry,) = coverage_entries
    assert entry.description.startswith("Run python -m coverage")
