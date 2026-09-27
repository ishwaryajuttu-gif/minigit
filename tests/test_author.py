import re

import pytest

from minigit_pkg import repository
from minigit_pkg.objects import hash_object, write_object
from minigit_pkg.repository import describe_author, read_commit, read_head


def make_commit(repo, run, message="change"):
    path = repo / "a.txt"
    path.write_bytes(message.encode() + b"\n")
    assert run("add", "a.txt")[0] == 0
    assert run("commit", "-m", message)[0] == 0
    return read_commit(str(repo), read_head(str(repo)))


# --- what gets recorded ---

def test_commit_records_author_and_time(repo, run, monkeypatch):
    monkeypatch.setenv("MINIGIT_AUTHOR_NAME", "Ada Lovelace")
    monkeypatch.setenv("MINIGIT_AUTHOR_EMAIL", "ada@example.com")
    monkeypatch.setattr(repository.time, "time", lambda: 1700000000.9)
    author = make_commit(repo, run).author
    assert re.fullmatch(r"Ada Lovelace <ada@example\.com> 1700000000 [+-]\d{4}", author)


def test_author_line_sits_between_parent_and_message(repo, run):
    make_commit(repo, run, "hello")
    content = (repo / ".minigit" / "objects" / read_head(str(repo))).read_text()
    lines = content.split("\n")
    assert lines[0].startswith("tree ")
    assert lines[1].startswith("parent ")
    assert lines[2].startswith("author ")
    assert content.endswith("\n\nhello")


def test_timezone_offset_format():
    seconds, zone = repository.author_timestamp().split()
    assert seconds.isdigit()
    assert re.fullmatch(r"[+-]\d{4}", zone)


# --- where the author comes from ---

def test_falls_back_to_login_name(repo, run, monkeypatch):
    monkeypatch.setattr(repository, "login_name", lambda: "someone")
    assert make_commit(repo, run).author.startswith("someone <> ")


def test_repository_config(repo, run):
    assert run("config", "user.name", "Grace Hopper") == (0, "Set user.name to Grace Hopper\n")
    assert run("config", "user.email", "grace@example.com") == (0, "Set user.email to grace@example.com\n")
    assert run("config", "user.name") == (0, "Grace Hopper\n")
    assert make_commit(repo, run).author.startswith("Grace Hopper <grace@example.com> ")
    assert "[user]" in (repo / ".minigit" / "config").read_text()


def test_global_config(repo, run, isolated_home):
    assert run("config", "--global", "user.name", "Alan Turing") == (0, "Set user.name to Alan Turing for all repositories\n")
    assert (isolated_home / ".minigitconfig").exists()
    assert run("config", "user.name") == (0, "Alan Turing\n")
    assert make_commit(repo, run).author.startswith("Alan Turing <> ")


def test_global_config_works_outside_a_repository(tmp_path, monkeypatch, run):
    monkeypatch.chdir(tmp_path)
    assert run("config", "--global", "user.email", "me@example.com")[0] == 0
    assert run("config", "--global", "user.email") == (0, "me@example.com\n")


def test_repository_config_beats_global(repo, run):
    run("config", "--global", "user.name", "Global Name")
    run("config", "user.name", "Repo Name")
    assert make_commit(repo, run).author.startswith("Repo Name <")


def test_environment_beats_config(repo, run, monkeypatch):
    run("config", "user.name", "Config Name")
    run("config", "user.email", "config@example.com")
    monkeypatch.setenv("MINIGIT_AUTHOR_NAME", "Env Name")
    monkeypatch.setenv("MINIGIT_AUTHOR_EMAIL", "env@example.com")
    assert make_commit(repo, run).author.startswith("Env Name <env@example.com> ")


# --- config errors ---

@pytest.mark.parametrize("args, message", [
    (("user.name",), "Error: user.name is not set"),
    (("core.editor", "vim"), "Error: unknown config key core.editor (use user.name or user.email)"),
    (("user.name", "   "), "Error: user.name cannot be empty"),
    (("user.name", "Bad <Name>"), "Error: user.name cannot contain '<', '>' or line breaks"),
    (("user.email", "a\nb"), "Error: user.email cannot contain '<', '>' or line breaks"),
    ((), "Usage: minigit config [--global] <key> [<value>]"),
    (("user.name", "a", "b"), "Usage: minigit config [--global] <key> [<value>]"),
])
def test_config_errors(repo, run, args, message):
    assert run("config", *args) == (1, message + "\n")


def test_repository_config_needs_a_repository(tmp_path, monkeypatch, run):
    monkeypatch.chdir(tmp_path)
    assert run("config", "user.name", "X") == (1, "Error: not a minigit repository (run 'init' first)\n")


def test_bad_author_from_environment(repo, run, monkeypatch):
    monkeypatch.setenv("MINIGIT_AUTHOR_NAME", "Bad <Name>")
    (repo / "a.txt").write_bytes(b"a\n")
    run("add", "a.txt")
    assert run("commit", "-m", "x") == (1, "Error: author name cannot contain '<', '>' or line breaks\n")
    assert read_head(str(repo)) == ""


def test_unreadable_config_file(repo, run):
    (repo / ".minigit" / "config").write_text("this is not a config file\n")
    status, out = run("config", "user.name")
    assert status == 1
    assert out.startswith("Error: can't read config file")


# --- showing authors in log ---

@pytest.mark.parametrize("author, expected", [
    ("Ada <ada@example.com> 1700000000 +0530", ("Ada <ada@example.com>", "Wed Nov 15 03:43:20 2023 +0530")),
    ("Ada <ada@example.com> 1700000000 -0800", ("Ada <ada@example.com>", "Tue Nov 14 14:13:20 2023 -0800")),
    ("Ada Lovelace <> 1700000000 +0000", ("Ada Lovelace <>", "Tue Nov 14 22:13:20 2023 +0000")),
    ("Ada <ada@example.com> soon +0530", ("Ada <ada@example.com> soon +0530", "unknown")),
    ("Ada <ada@example.com> 1700000000 IST", ("Ada <ada@example.com> 1700000000 IST", "unknown")),
    ("no email here 1700000000 +0530", ("no email here 1700000000 +0530", "unknown")),
])
def test_describe_author(author, expected):
    assert describe_author(author) == expected


def test_log_shows_author_and_date(repo, run, monkeypatch):
    monkeypatch.setenv("MINIGIT_AUTHOR_NAME", "Ada Lovelace")
    monkeypatch.setenv("MINIGIT_AUTHOR_EMAIL", "ada@example.com")
    monkeypatch.setattr(repository, "author_timestamp", lambda: "1700000000 -0800")
    make_commit(repo, run, "hello")
    assert run("log") == (0, (
        f"commit {read_head(str(repo))}\n"
        "Author: Ada Lovelace <ada@example.com>\n"
        "Date:   Tue Nov 14 14:13:20 2023 -0800\n"
        "\n"
        "    hello\n"
        "\n"
    ))


def test_log_mixes_old_and_new_commits(repo, run, monkeypatch):
    # A commit from before authors were recorded, followed by a new one
    objects = str(repo / ".minigit")
    blob = write_object(b"old\n", objects)
    tree = write_object(f"a.txt {blob}\n".encode(), objects)
    old = write_object(f"tree {tree}\nparent \n\nold commit".encode(), objects)
    (repo / ".minigit" / "HEAD").write_text(old)
    (repo / ".minigit" / "index").write_bytes(f"a.txt {blob}\n".encode())
    monkeypatch.setenv("MINIGIT_AUTHOR_NAME", "Ada")
    monkeypatch.setattr(repository, "author_timestamp", lambda: "1700000000 +0000")
    new = make_commit(repo, run, "new commit")
    assert new.parent == old
    assert run("log") == (0, (
        f"commit {old}\n    old commit\n\n"
        f"commit {read_head(str(repo))}\n"
        "Author: Ada <>\nDate:   Tue Nov 14 22:13:20 2023 +0000\n\n    new commit\n\n"
    ))


def test_each_commit_records_its_own_time(repo, run, monkeypatch):
    times = iter([1700000000.0, 1700000060.0])
    monkeypatch.setattr(repository.time, "time", lambda: next(times))
    first = make_commit(repo, run, "one")
    (repo / "a.txt").write_bytes(b"two\n")
    run("add", "a.txt")
    run("commit", "-m", "one")
    assert read_commit(str(repo), read_head(str(repo))).author != first.author
