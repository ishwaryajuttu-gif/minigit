import sys

import pytest

from minigit_pkg import cli


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch):
    """Point the home folder at an empty temp folder so tests never touch the real
    ~/.minigitconfig, and clear author variables that could leak in from the shell."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("MINIGIT_AUTHOR_NAME", raising=False)
    monkeypatch.delenv("MINIGIT_AUTHOR_EMAIL", raising=False)
    return home


@pytest.fixture
def run(capsys):
    """Run a minigit command in the current folder; returns (exit status, output)."""
    def run_command(*args):
        old_argv = sys.argv
        sys.argv = ["minigit", *args]
        try:
            status = cli.main()
        finally:
            sys.argv = old_argv
        return status, capsys.readouterr().out
    return run_command


@pytest.fixture
def repo(tmp_path, monkeypatch, run):
    """An empty minigit repository as the current folder."""
    monkeypatch.chdir(tmp_path)
    assert run("init")[0] == 0
    return tmp_path
