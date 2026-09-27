import os
import subprocess
import sys
from pathlib import Path

import pytest

from minigit_pkg.cli import COMMANDS, general_help

ROOT = Path(__file__).resolve().parent.parent


# --- minigit --help ---

@pytest.mark.parametrize("args", [("--help",), ("-h",), ("help",)])
def test_general_help(tmp_path, monkeypatch, run, args):
    monkeypatch.chdir(tmp_path)  # works outside a repository
    status, out = run(*args)
    assert status == 0
    assert out == general_help() + "\n"
    assert out.startswith("Usage: minigit <command> [<args>]\n")


def test_general_help_lists_every_command():
    text = general_help()
    for command, (usage, summary, _) in COMMANDS.items():
        assert f"  {usage[len('minigit '):]}" in text
        assert summary in text


def test_no_command_shows_help_and_fails(tmp_path, monkeypatch, run):
    monkeypatch.chdir(tmp_path)
    assert run() == (1, general_help() + "\n")


# --- minigit <command> --help ---

@pytest.mark.parametrize("command", list(COMMANDS))
@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_command_help(tmp_path, monkeypatch, run, command, flag):
    monkeypatch.chdir(tmp_path)
    usage, summary, _ = COMMANDS[command]
    status, out = run(command, flag)
    assert status == 0
    assert out.startswith(f"Usage: {usage}\n\n{summary}.")
    assert not (tmp_path / ".minigit").exists()  # help never runs the command


@pytest.mark.parametrize("command", list(COMMANDS))
def test_help_command_for_one_command(run, command):
    usage = COMMANDS[command][0]
    status, out = run("help", command)
    assert status == 0
    assert out.startswith(f"Usage: {usage}\n")


@pytest.mark.parametrize("args", [("help", "bogus"), ("help", "add", "commit")])
def test_help_for_unknown_command(run, args):
    status, out = run(*args)
    assert status == 1
    assert out.startswith("Unknown command: ")


def test_help_flag_only_counts_as_first_argument(repo, run):
    # A commit message of "--help" is a message, not a request for help
    (repo / "a.txt").write_bytes(b"a\n")
    run("add", "a.txt")
    status, out = run("commit", "-m", "--help")
    assert status == 0
    assert out.startswith("Committed as ")


# --- python -m minigit_pkg ---

def run_module(cwd, *args):
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "minigit_pkg", *args],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def test_python_m_runs_commands(tmp_path):
    result = run_module(tmp_path, "init")
    assert result.returncode == 0
    assert result.stdout == "Initialized empty minigit repository.\n"
    assert (tmp_path / ".minigit").is_dir()


def test_python_m_passes_on_exit_status(tmp_path):
    result = run_module(tmp_path, "log")
    assert result.returncode == 1
    assert result.stdout == "Error: not a minigit repository (run 'init' first)\n"


def test_python_m_help(tmp_path):
    result = run_module(tmp_path, "--help")
    assert result.returncode == 0
    assert result.stdout.replace("\r\n", "\n") == general_help() + "\n"
