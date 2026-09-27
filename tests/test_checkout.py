import pytest

from minigit_pkg import repository
from minigit_pkg.objects import hash_object, write_object
from minigit_pkg.repository import read_head, read_index


def commit_files(repo, run, message, **files):
    """Write files (name=content bytes; use "__" for "/"), stage them and commit; returns the hash."""
    names = []
    for name, content in files.items():
        path = repo / name.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        names.append(name.replace("__", "/"))
    assert run("add", *names)[0] == 0
    assert run("commit", "-m", message)[0] == 0
    return read_head(str(repo))


@pytest.fixture
def two_commits(repo, run):
    """a.txt changes between two commits; b.txt is only in the second."""
    first = commit_files(repo, run, "first", **{"a.txt": b"one\n"})
    second = commit_files(repo, run, "second", **{"a.txt": b"two\n", "b.txt": b"b\n"})
    return first, second


# --- restoring files ---

def test_restore_file_from_older_commit(repo, run, two_commits):
    first, second = two_commits
    assert run("checkout", first, "a.txt") == (0, "Restored a.txt\n")
    assert (repo / "a.txt").read_bytes() == b"one\n"
    assert read_index(str(repo))["a.txt"] == hash_object(b"one\n")
    assert read_head(str(repo)) == second  # HEAD doesn't move


def test_restored_file_can_be_committed(repo, run, two_commits):
    first, second = two_commits
    run("checkout", first, "a.txt")
    assert run("commit", "-m", "back to one")[0] == 0
    log = run("log")[1]
    assert log.index(first) < log.index(second) < log.index(read_head(str(repo)))


def test_restore_deleted_file_from_head(repo, run, two_commits):
    (repo / "b.txt").unlink()
    assert run("checkout", "HEAD", "b.txt") == (0, "Restored b.txt\n")
    assert (repo / "b.txt").read_bytes() == b"b\n"


def test_restore_file_into_deleted_folder(repo, run):
    commit_files(repo, run, "nested", **{"docs__guide__intro.txt": b"hi\n"})
    (repo / "docs" / "guide" / "intro.txt").unlink()
    (repo / "docs" / "guide").rmdir()
    (repo / "docs").rmdir()
    assert run("checkout", "HEAD", "docs/guide/intro.txt")[0] == 0
    assert (repo / "docs" / "guide" / "intro.txt").read_bytes() == b"hi\n"


def test_restore_several_files(repo, run, two_commits):
    first, second = two_commits
    (repo / "a.txt").write_bytes(b"scratch\n")
    run("add", "a.txt")
    (repo / "b.txt").unlink()
    assert run("checkout", second, "b.txt", "a.txt") == (0, "Restored b.txt\nRestored a.txt\n")
    assert (repo / "a.txt").read_bytes() == b"two\n"


def test_restore_from_subfolder(repo, run, monkeypatch):
    commit_files(repo, run, "nested", **{"sub__s.txt": b"s\n"})
    (repo / "sub" / "s.txt").write_bytes(b"changed\n")
    run("add", "sub/s.txt")
    monkeypatch.chdir(repo / "sub")
    assert run("checkout", "HEAD", "s.txt") == (0, "Restored sub/s.txt\n")
    assert (repo / "sub" / "s.txt").read_bytes() == b"s\n"


# --- restoring a whole snapshot ---

def test_restore_whole_snapshot(repo, run, two_commits):
    first, second = two_commits
    status, out = run("checkout", first)
    assert status == 0
    assert out == f"Restored a.txt\nUnstaged b.txt (not in {first[:7]}; the file is left in place)\n"
    assert (repo / "a.txt").read_bytes() == b"one\n"
    assert (repo / "b.txt").read_bytes() == b"b\n"  # left on disk
    assert read_index(str(repo)) == {"a.txt": hash_object(b"one\n")}
    assert read_head(str(repo)) == second


def test_commit_after_whole_snapshot_matches_old_tree(repo, run, two_commits):
    first, _ = two_commits
    run("checkout", first)
    run("commit", "-m", "restore first")
    trees = [
        (repo / ".minigit" / "objects" / commit).read_text().split("\n")[0]
        for commit in (first, read_head(str(repo)))
    ]
    assert trees[0] == trees[1]


# --- choosing a commit ---

def test_short_hash(repo, run, two_commits):
    first, _ = two_commits
    assert run("checkout", first[:7], "a.txt")[0] == 0
    assert (repo / "a.txt").read_bytes() == b"one\n"


def test_uppercase_hash(repo, run, two_commits):
    first, _ = two_commits
    assert run("checkout", first[:10].upper(), "a.txt")[0] == 0


@pytest.mark.parametrize("ref, message", [
    ("abc", "not a commit: abc (use a hash from 'log', at least 4 characters)"),
    ("main", "not a commit: main (use a hash from 'log', at least 4 characters)"),
    ("0000000", "no commit matches 0000000"),
])
def test_bad_commit_refs(repo, run, two_commits, ref, message):
    assert run("checkout", ref) == (1, f"Error: {message}\n")


def test_blob_hash_is_not_a_commit(repo, run, two_commits):
    # Objects aren't typed, so only commits in the history can be checked out
    blob = hash_object(b"one\n")
    assert run("checkout", blob) == (1, f"Error: no commit matches {blob}\n")


def test_ambiguous_prefix(repo, run, monkeypatch):
    monkeypatch.setattr(repository, "history", lambda root: ["abcd1111", "abcd2222"])
    (repo / ".minigit" / "HEAD").write_text("abcd1111")
    assert run("checkout", "abcd", "a.txt") == (1, "Error: abcd matches more than one commit; use more characters\n")


def test_no_commits_yet(repo, run):
    assert run("checkout", "HEAD") == (1, "Error: no commits yet\n")


def test_file_not_in_commit(repo, run, two_commits):
    first, _ = two_commits
    assert run("checkout", first, "b.txt") == (1, f"Error: b.txt is not in commit {first[:7]}\n")


# --- protecting work ---

def test_refuses_to_overwrite_unstaged_changes(repo, run, two_commits):
    first, second = two_commits
    (repo / "a.txt").write_bytes(b"my unsaved work\n")
    status, out = run("checkout", first, "a.txt")
    assert status == 1
    assert out == (
        "Error: these files have changes that aren't staged and would be overwritten:\n"
        "  a.txt\n"
        "add them first to keep the changes, or use --force to discard them\n"
    )
    assert (repo / "a.txt").read_bytes() == b"my unsaved work\n"
    assert read_index(str(repo))["a.txt"] == hash_object(b"two\n")


def test_force_overwrites_unstaged_changes(repo, run, two_commits):
    first, _ = two_commits
    (repo / "a.txt").write_bytes(b"throw this away\n")
    assert run("checkout", "--force", first, "a.txt") == (0, "Restored a.txt\n")
    assert (repo / "a.txt").read_bytes() == b"one\n"


def test_staged_changes_are_safe_to_overwrite(repo, run, two_commits):
    # Staged content is already saved as an object, so it isn't lost
    first, _ = two_commits
    (repo / "a.txt").write_bytes(b"staged\n")
    run("add", "a.txt")
    assert run("checkout", first, "a.txt")[0] == 0
    assert (repo / ".minigit" / "objects" / hash_object(b"staged\n")).exists()


def test_refuses_to_overwrite_untracked_file(repo, run):
    first = commit_files(repo, run, "first", **{"a.txt": b"a\n", "b.txt": b"b\n"})
    (repo / "b.txt").unlink()
    run("add", "b.txt")
    run("commit", "-m", "remove b")
    (repo / "b.txt").write_bytes(b"new untracked file\n")
    assert run("checkout", first)[0] == 1
    assert (repo / "b.txt").read_bytes() == b"new untracked file\n"


def test_unchanged_files_are_not_at_risk(repo, run, two_commits):
    first, _ = two_commits
    (repo / "a.txt").write_bytes(b"one\n")  # already the content being restored
    assert run("checkout", first, "a.txt")[0] == 0


# --- nothing is written if anything is wrong ---

def test_corrupt_object_changes_nothing(repo, run, two_commits):
    first, _ = two_commits
    blob = hash_object(b"one\n")
    (repo / ".minigit" / "objects" / blob).write_bytes(b"damaged")
    status, out = run("checkout", first)
    assert status == 1
    assert "corrupt" in out
    assert (repo / "a.txt").read_bytes() == b"two\n"
    assert set(read_index(str(repo))) == {"a.txt", "b.txt"}


def test_folder_in_the_way(repo, run, two_commits):
    (repo / "b.txt").unlink()
    (repo / "b.txt").mkdir()
    assert run("checkout", "HEAD", "b.txt") == (1, "Error: cannot restore b.txt: a folder named b.txt is in the way\n")


def test_file_in_the_way_of_folder(repo, run):
    commit_files(repo, run, "nested", **{"docs__a.txt": b"a\n"})
    (repo / "docs" / "a.txt").unlink()
    (repo / "docs").rmdir()
    (repo / "docs").write_bytes(b"now a file\n")
    status, out = run("checkout", "HEAD", "docs/a.txt")
    assert status == 1
    assert out.startswith("Error: cannot restore docs/a.txt: a file is in the way")


@pytest.mark.parametrize("bad_path", ["../escaped.txt", "sub/../../escaped.txt", ".minigit/HEAD", "/abs.txt"])
def test_unsafe_paths_in_tree_are_refused(repo, run, bad_path):
    # A hand-made tree must not be able to write outside the repository
    objects = str(repo / ".minigit")
    blob = write_object(b"evil\n", objects)
    tree = write_object(f"{bad_path} {blob}\n".encode(), objects)
    commit = write_object(f"tree {tree}\nparent \n\nevil".encode(), objects)
    (repo / ".minigit" / "HEAD").write_text(commit)
    status, out = run("checkout", "HEAD")
    assert status == 1
    assert out == f"Error: refusing to restore unsafe path {bad_path!r}\n"
    assert not (repo.parent / "escaped.txt").exists()


# --- command line ---

def test_usage(repo, run):
    assert run("checkout") == (1, "Usage: minigit checkout <commit> [<file>...] [--force]\n")
    assert run("checkout", "--force") == (1, "Usage: minigit checkout <commit> [<file>...] [--force]\n")
