import shutil
import subprocess

import pytest

from minigit_pkg import repository
from minigit_pkg.objects import hash_object
from minigit_pkg.repository import read_head, read_index


def index_bytes(repo):
    return (repo / ".minigit" / "index").read_bytes()


def head_tree(repo):
    commit = (repo / ".minigit" / "objects" / read_head(str(repo))).read_bytes().decode()
    return commit.split("\n")[0][len("tree "):]


# --- init ---

def test_init_creates_repository(tmp_path, monkeypatch, run):
    monkeypatch.chdir(tmp_path)
    assert run("init") == (0, "Initialized empty minigit repository.\n")
    assert (tmp_path / ".minigit" / "objects").is_dir()
    assert index_bytes(tmp_path) == b""


def test_init_twice(repo, run):
    assert run("init") == (0, "Already a minigit repository.\n")


# --- commands outside a repository ---

@pytest.mark.parametrize("args", [("add", "a.txt"), ("commit", "-m", "x"), ("log",)])
def test_commands_need_a_repository(tmp_path, monkeypatch, run, args):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("hi\n")
    status, out = run(*args)
    assert status == 1
    assert out == "Error: not a minigit repository (run 'init' first)\n"
    assert not (tmp_path / ".minigit").exists()


# --- add ---

def test_add_stages_git_compatible_hash(repo, run):
    (repo / "a.txt").write_bytes(b"hello world\n")
    assert run("add", "a.txt") == (0, "Added a.txt\n")
    assert index_bytes(repo) == b"a.txt 3b18e512dba79e4c8300dd08aeb37f8e728b8dad\n"


def test_readding_changed_file_replaces_entry(repo, run):
    (repo / "a.txt").write_bytes(b"one\n")
    run("add", "a.txt")
    (repo / "a.txt").write_bytes(b"two\n")
    run("add", "a.txt")
    assert read_index(str(repo)) == {"a.txt": hash_object(b"two\n")}


def test_adding_deleted_file_stages_removal(repo, run):
    (repo / "a.txt").write_text("a\n")
    (repo / "b.txt").write_text("b\n")
    run("add", "a.txt")
    run("add", "b.txt")
    (repo / "b.txt").unlink()
    assert run("add", "b.txt") == (0, "Removed b.txt\n")
    assert list(read_index(str(repo))) == ["a.txt"]


@pytest.mark.parametrize("path, message", [
    ("missing.txt", "file not found: missing.txt"),
    (".", "not a file: ."),
    (".minigit/index", "cannot use files inside .minigit"),
])
def test_add_errors(repo, run, path, message):
    assert run("add", path) == (1, f"Error: {message}\n")
    assert index_bytes(repo) == b""


def test_add_outside_repository(tmp_path, monkeypatch, run):
    (tmp_path / "outside.txt").write_text("x\n")
    (tmp_path / "project").mkdir()
    monkeypatch.chdir(tmp_path / "project")
    run("init")
    status, out = run("add", "../outside.txt")
    assert status == 1
    assert out == "Error: ../outside.txt is outside the repository\n"


def test_file_names_with_spaces(repo, run):
    (repo / "my file.txt").write_bytes(b"x\n")
    run("add", "my file.txt")
    assert read_index(str(repo)) == {"my file.txt": hash_object(b"x\n")}


@pytest.mark.parametrize("name", ["a b.txt", "a b.txt", "a\x85b.txt"])
def test_file_names_with_unicode_line_separators(repo, run, name):
    # str.splitlines() treats these as line breaks; the index must not
    (repo / name).write_bytes(b"x\n")
    (repo / "other.txt").write_bytes(b"y\n")
    assert run("add", name)[0] == 0
    assert run("add", "other.txt")[0] == 0
    assert read_index(str(repo)) == {name: hash_object(b"x\n"), "other.txt": hash_object(b"y\n")}
    assert run("commit", "-m", "unicode names")[0] == 0


def test_add_several_files(repo, run):
    (repo / "a.txt").write_bytes(b"a\n")
    (repo / "b.txt").write_bytes(b"b\n")
    assert run("add", "b.txt", "a.txt") == (0, "Added b.txt\nAdded a.txt\n")
    assert read_index(str(repo)) == {"a.txt": hash_object(b"a\n"), "b.txt": hash_object(b"b\n")}


def test_add_stages_nothing_if_any_file_fails(repo, run):
    (repo / "a.txt").write_bytes(b"a\n")
    assert run("add", "a.txt", "missing.txt") == (1, "Error: file not found: missing.txt\n")
    assert index_bytes(repo) == b""


def test_add_removal_and_update_together(repo, run):
    (repo / "a.txt").write_bytes(b"a\n")
    (repo / "b.txt").write_bytes(b"b\n")
    run("add", "a.txt", "b.txt")
    (repo / "a.txt").unlink()
    (repo / "b.txt").write_bytes(b"b2\n")
    assert run("add", "a.txt", "b.txt") == (0, "Removed a.txt\nAdded b.txt\n")
    assert read_index(str(repo)) == {"b.txt": hash_object(b"b2\n")}


def case_insensitive(folder):
    probe = folder / "CaseProbe.tmp"
    probe.write_bytes(b"")
    try:
        return (folder / "caseprobe.tmp").exists()
    finally:
        probe.unlink()


def test_case_only_rename_reuses_tracked_name(repo, run):
    if not case_insensitive(repo):
        pytest.skip("file system is case-sensitive")
    (repo / "A.txt").write_bytes(b"one\n")
    run("add", "A.txt")
    (repo / "A.txt").write_bytes(b"two\n")
    assert run("add", "a.txt") == (0, "Added A.txt\n")
    assert read_index(str(repo)) == {"A.txt": hash_object(b"two\n")}


def test_different_case_names_are_separate_on_case_sensitive_systems(repo, run):
    if case_insensitive(repo):
        pytest.skip("file system is case-insensitive")
    (repo / "A.txt").write_bytes(b"upper\n")
    (repo / "a.txt").write_bytes(b"lower\n")
    run("add", "A.txt", "a.txt")
    assert read_index(str(repo)) == {"A.txt": hash_object(b"upper\n"), "a.txt": hash_object(b"lower\n")}


def test_index_is_sorted_with_lf_endings(repo, run):
    for name in ["c.txt", "a.txt", "b.txt"]:
        (repo / name).write_text(name + "\n")
        run("add", name)
    lines = index_bytes(repo).split(b"\n")
    assert [line.split(b" ")[0] for line in lines if line] == [b"a.txt", b"b.txt", b"c.txt"]
    assert b"\r" not in index_bytes(repo)


# --- subfolders ---

def test_commands_work_from_subfolder(repo, monkeypatch, run):
    (repo / "sub" / "deep").mkdir(parents=True)
    (repo / "sub" / "deep" / "s.txt").write_text("s\n")
    monkeypatch.chdir(repo / "sub")
    assert run("add", "deep/s.txt") == (0, "Added sub/deep/s.txt\n")
    assert run("commit", "-m", "from sub")[0] == 0
    assert "from sub" in run("log")[1]
    assert list(read_index(str(repo))) == ["sub/deep/s.txt"]


# --- commit ---

def test_commit_links_to_parent(repo, run):
    (repo / "a.txt").write_text("one\n")
    run("add", "a.txt")
    status, out = run("commit", "-m", "first")
    assert status == 0
    first = read_head(str(repo))
    assert out == f"Committed as {first}\n"

    (repo / "a.txt").write_text("two\n")
    run("add", "a.txt")
    run("commit", "-m", "second")
    second = (repo / ".minigit" / "objects" / read_head(str(repo))).read_text()
    assert f"parent {first}\n" in second
    assert second.endswith("\n\nsecond")


def test_nothing_to_commit_in_empty_repository(repo, run):
    assert run("commit", "-m", "x") == (1, "Error: nothing to commit (use 'add' to stage changes)\n")
    assert read_head(str(repo)) == ""


def test_nothing_to_commit_after_commit(repo, run):
    (repo / "a.txt").write_text("a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    head = read_head(str(repo))
    assert run("commit", "-m", "again")[0] == 1
    run("add", "a.txt")  # re-adding the same content changes nothing
    assert run("commit", "-m", "again")[0] == 1
    assert read_head(str(repo)) == head


def test_empty_commit_message_rejected(repo, run):
    (repo / "a.txt").write_text("a\n")
    run("add", "a.txt")
    assert run("commit", "-m", "  ") == (1, "Error: commit message cannot be empty\n")


def test_same_files_give_same_tree_in_any_order(tmp_path, monkeypatch, run):
    trees = []
    for name, order in [("one", ["a.txt", "b.txt"]), ("two", ["b.txt", "a.txt"])]:
        folder = tmp_path / name
        folder.mkdir()
        monkeypatch.chdir(folder)
        run("init")
        for file in order:
            (folder / file).write_text(file + "\n")
            run("add", file)
        run("commit", "-m", "snapshot")
        trees.append(head_tree(folder))
    assert trees[0] == trees[1]


# --- log ---

def test_log_with_no_commits(repo, run):
    assert run("log") == (0, "No commits yet.\n")


def test_log_prints_oldest_first(repo, run, monkeypatch):
    monkeypatch.setenv("MINIGIT_AUTHOR_NAME", "Ada Lovelace")
    monkeypatch.setenv("MINIGIT_AUTHOR_EMAIL", "ada@example.com")
    monkeypatch.setattr(repository, "author_timestamp", lambda: "1700000000 +0530")
    hashes = []
    for i, message in enumerate(["first", "second\nwith detail", "third"]):
        (repo / "a.txt").write_text(f"{i}\n")
        run("add", "a.txt")
        run("commit", "-m", message)
        hashes.append(read_head(str(repo)))
    header = "Author: Ada Lovelace <ada@example.com>\nDate:   Wed Nov 15 03:43:20 2023 +0530\n\n"
    assert run("log") == (0, (
        f"commit {hashes[0]}\n{header}    first\n\n"
        f"commit {hashes[1]}\n{header}    second\n    with detail\n\n"
        f"commit {hashes[2]}\n{header}    third\n\n"
    ))


def test_corrupt_commit_is_reported(repo, run):
    (repo / "a.txt").write_bytes(b"a\n")
    run("add", "a.txt")
    run("commit", "-m", "first")
    head = read_head(str(repo))
    (repo / ".minigit" / "objects" / head).write_bytes(b"garbage")
    message = f"Error: object {head} is corrupt: its content no longer matches its hash\n"
    assert run("log") == (1, message)
    (repo / "b.txt").write_bytes(b"b\n")
    run("add", "b.txt")
    assert run("commit", "-m", "second") == (1, message)
    assert read_head(str(repo)) == head


def test_log_reports_missing_commit(repo, run):
    (repo / ".minigit" / "HEAD").write_text("0" * 40)
    assert run("log") == (1, f"Error: missing commit object {'0' * 40}\n")


# --- repositories made by earlier versions ---

def test_old_index_with_duplicates_and_crlf_loads(repo, run):
    (repo / ".minigit" / "index").write_bytes(b"a.txt 1111\r\nb.txt 2222\r\na.txt 3333\r\n")
    assert read_index(str(repo)) == {"a.txt": "3333", "b.txt": "2222"}


def test_old_repository_log_and_commit(repo, run):
    # Objects laid out exactly as the first version wrote them: CRLF index with duplicates
    objects = repo / ".minigit" / "objects"
    blob = hash_object(b"two\n")
    (objects / blob).write_bytes(b"two\n")
    old_index = f"a.txt {hash_object(b'one')}\r\na.txt {blob}\r\n".encode()
    tree = hash_object(old_index)
    (objects / tree).write_bytes(old_index)
    old_commit = f"tree {tree}\nparent \n\nold commit".encode()
    commit = hash_object(old_commit)
    (objects / commit).write_bytes(old_commit)
    (repo / ".minigit" / "index").write_bytes(old_index)
    (repo / ".minigit" / "HEAD").write_text(commit)

    assert run("log") == (0, f"commit {commit}\n    old commit\n\n")
    # The first commit rewrites the old tree in the new format; after that nothing changed
    assert run("commit", "-m", "normalise")[0] == 0
    assert (objects / head_tree(repo)).read_bytes() == f"a.txt {blob}\n".encode()
    assert run("commit", "-m", "again")[0] == 1


# --- command line ---

@pytest.mark.parametrize("args, message", [
    (("add",), "Usage: minigit add <file>..."),
    (("commit",), 'Usage: minigit commit -m "message"'),
    (("commit", "message"), 'Usage: minigit commit -m "message"'),
    (("commit", "-m", "two", "words"), 'Usage: minigit commit -m "message"'),
    (("init", "extra"), "Usage: minigit init"),
    (("log", "extra"), "Usage: minigit log"),
    (("bogus",), "Unknown command: bogus\nRun 'minigit --help' to see the commands."),
])
def test_usage_errors(repo, run, args, message):
    assert run(*args) == (1, message + "\n")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_staged_hash_matches_git(repo, run):
    (repo / "a.txt").write_bytes(b"line one\r\nline two\n")
    run("add", "a.txt")
    result = subprocess.run(
        ["git", "hash-object", "--no-filters", "a.txt"],
        capture_output=True, text=True, check=True,
    )
    assert read_index(str(repo))["a.txt"] == result.stdout.strip()
