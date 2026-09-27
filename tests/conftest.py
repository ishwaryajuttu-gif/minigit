import sys

import pytest

from minigit_pkg import cli


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
