import os
from minigit_pkg.objects import hash_object, read_object, write_object

MINIGIT_DIR = ".minigit"


class MinigitError(Exception):
    """A problem to report to the user as a message instead of a traceback."""


def find_repo() -> str:
    # Walk up from the current folder, like git, so commands work in subfolders
    path = os.getcwd()
    while True:
        if os.path.isdir(os.path.join(path, MINIGIT_DIR)):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            raise MinigitError("not a minigit repository (run 'init' first)")
        path = parent


def read_index(root: str) -> dict:
    # Later lines win, so indexes written before add replaced entries still load correctly
    index_path = os.path.join(root, MINIGIT_DIR, "index")
    entries = {}
    if not os.path.exists(index_path):
        return entries
    with open(index_path, "rb") as f:
        for line in f.read().decode().splitlines():
            if not line.strip():
                continue
            path, separator, digest = line.rpartition(" ")
            if not separator or not path:
                raise MinigitError(f"corrupt index line: {line!r}")
            entries[path] = digest
    return entries


def format_index(entries: dict) -> bytes:
    # Sorted with "\n" endings so the same files give the same tree hash on every OS
    return "".join(f"{path} {entries[path]}\n" for path in sorted(entries)).encode()


def write_index(root: str, entries: dict):
    with open(os.path.join(root, MINIGIT_DIR, "index"), "wb") as f:
        f.write(format_index(entries))


def read_head(root: str) -> str:
    head_path = os.path.join(root, MINIGIT_DIR, "HEAD")
    if not os.path.exists(head_path):
        return ""
    with open(head_path, "rb") as f:
        return f.read().decode().strip()


def parse_commit(content: bytes) -> tuple:
    # Header fields come first, then a blank line, then the (possibly multi-line) message
    header, _, message = content.decode().partition("\n\n")
    fields = {}
    for line in header.split("\n"):
        key, _, value = line.partition(" ")
        fields[key] = value.strip()
    return fields.get("tree", ""), fields.get("parent", ""), message


def read_commit(root: str, commit_hash: str) -> tuple:
    try:
        return parse_commit(read_object(commit_hash, os.path.join(root, MINIGIT_DIR)))
    except FileNotFoundError:
        raise MinigitError(f"missing commit object {commit_hash}") from None


def init():
    if os.path.exists(MINIGIT_DIR):
        print("Already a minigit repository.")
        return
    os.makedirs(os.path.join(MINIGIT_DIR, "objects"))
    with open(os.path.join(MINIGIT_DIR, "index"), "wb"):
        pass  # creates an empty file
    print("Initialized empty minigit repository.")


def add(filepath: str):
    root = find_repo()
    full_path = os.path.abspath(filepath)
    try:
        rel_path = os.path.relpath(full_path, root)
    except ValueError:  # different drive on Windows
        rel_path = os.pardir
    if rel_path.split(os.sep)[0] == os.pardir:
        raise MinigitError(f"{filepath} is outside the repository")
    if rel_path.split(os.sep)[0] == MINIGIT_DIR:
        raise MinigitError(f"cannot add files inside {MINIGIT_DIR}")
    if "\n" in rel_path:
        raise MinigitError("file names cannot contain line breaks")
    # Store paths relative to the repo root with "/" so they match on every OS
    rel_path = rel_path.replace(os.sep, "/")

    entries = read_index(root)
    if not os.path.exists(full_path):
        # Adding a tracked file that was deleted stages its removal, like git add
        if rel_path in entries:
            del entries[rel_path]
            write_index(root, entries)
            print(f"Removed {rel_path}")
            return
        raise MinigitError(f"file not found: {filepath}")
    if not os.path.isfile(full_path):
        raise MinigitError(f"not a file: {filepath}")

    with open(full_path, "rb") as f:
        content = f.read()
    entries[rel_path] = write_object(content, os.path.join(root, MINIGIT_DIR))
    write_index(root, entries)
    print(f"Added {rel_path}")


def commit(message: str):
    if not message.strip():
        raise MinigitError("commit message cannot be empty")
    root = find_repo()
    minigit_dir = os.path.join(root, MINIGIT_DIR)

    tree_content = format_index(read_index(root))
    parent_hash = read_head(root)
    if parent_hash:
        parent_tree, _, _ = read_commit(root, parent_hash)
        unchanged = hash_object(tree_content) == parent_tree
    else:
        unchanged = tree_content == b""
    if unchanged:
        raise MinigitError("nothing to commit (use 'add' to stage changes)")

    tree_hash = write_object(tree_content, minigit_dir)
    commit_content = f"tree {tree_hash}\nparent {parent_hash}\n\n{message}"
    commit_hash = write_object(commit_content.encode(), minigit_dir)

    with open(os.path.join(minigit_dir, "HEAD"), "wb") as f:
        f.write(commit_hash.encode())

    print(f"Committed as {commit_hash}")
    return commit_hash


def log():
    root = find_repo()
    current_hash = read_head(root)
    if not current_hash:
        print("No commits yet.")
        return

    # Walk the parent pointers back to the first commit, then print oldest first
    commits = []
    while current_hash:
        _, parent_hash, message = read_commit(root, current_hash)
        commits.append((current_hash, message))
        current_hash = parent_hash

    commits.reverse()

    for commit_hash, message in commits:
        print(f"commit {commit_hash}")
        for line in message.split("\n"):
            print(f"    {line}")
        print()
