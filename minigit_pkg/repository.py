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


def parse_index(data: bytes) -> dict:
    # Used for both the index file and tree objects, which share one format.
    # Later lines win, so indexes written before add replaced entries still load correctly.
    entries = {}
    # Split only on "\n": splitlines() would also split file names containing
    # characters such as U+2028. The "\r" strip reads indexes from older versions.
    for line in data.decode().split("\n"):
        line = line.removesuffix("\r")
        if not line.strip():
            continue
        path, separator, digest = line.rpartition(" ")
        if not separator or not path:
            raise MinigitError(f"corrupt index line: {line!r}")
        entries[path] = digest
    return entries


def read_index(root: str) -> dict:
    index_path = os.path.join(root, MINIGIT_DIR, "index")
    if not os.path.exists(index_path):
        return {}
    with open(index_path, "rb") as f:
        return parse_index(f.read())


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


def load_object(root: str, digest: str, kind: str) -> bytes:
    try:
        return read_object(digest, os.path.join(root, MINIGIT_DIR))
    except FileNotFoundError:
        raise MinigitError(f"missing {kind} object {digest}") from None
    except ValueError as error:
        raise MinigitError(str(error)) from None


def read_commit(root: str, commit_hash: str) -> tuple:
    return parse_commit(load_object(root, commit_hash, "commit"))


def history(root: str) -> list:
    # Commit hashes from HEAD back to the first commit, newest first
    hashes = []
    current_hash = read_head(root)
    while current_hash:
        hashes.append(current_hash)
        _, current_hash, _ = read_commit(root, current_hash)
    return hashes


def resolve_commit(root: str, ref: str) -> str:
    # Accept "HEAD", a full hash, or a unique prefix of at least 4 characters,
    # matched only against commits in the history so blobs and trees can't be picked
    head = read_head(root)
    if not head:
        raise MinigitError("no commits yet")
    if ref == "HEAD":
        return head
    ref = ref.lower()
    if len(ref) < 4 or any(c not in "0123456789abcdef" for c in ref):
        raise MinigitError(f"not a commit: {ref} (use a hash from 'log', at least 4 characters)")
    matches = [h for h in history(root) if h.startswith(ref)]
    if not matches:
        raise MinigitError(f"no commit matches {ref}")
    if len(matches) > 1:
        raise MinigitError(f"{ref} matches more than one commit; use more characters")
    return matches[0]


def to_repo_path(root: str, filepath: str) -> tuple:
    # Returns (path relative to the repo root with "/" separators, absolute path)
    full_path = os.path.abspath(filepath)
    try:
        rel_path = os.path.relpath(full_path, root)
    except ValueError:  # different drive on Windows
        rel_path = os.pardir
    if rel_path.split(os.sep)[0] == os.pardir:
        raise MinigitError(f"{filepath} is outside the repository")
    if rel_path.split(os.sep)[0] == MINIGIT_DIR:
        raise MinigitError(f"cannot use files inside {MINIGIT_DIR}")
    if "\n" in rel_path or "\r" in rel_path:
        raise MinigitError("file names cannot contain line breaks")
    # Store paths relative to the repo root with "/" so they match on every OS
    return rel_path.replace(os.sep, "/"), full_path


def working_path(root: str, path: str) -> str:
    # Turn a path from a tree into a location on disk, refusing anything that
    # could write outside the repository or into .minigit
    # Windows also treats "\" as a separator, so check those pieces there too
    parts = (path.replace("\\", "/") if os.name == "nt" else path).split("/")
    unsafe = (
        os.path.isabs(path)
        or (os.name == "nt" and ":" in path)
        or any(part in ("", ".", "..") for part in parts)
        or parts[0] == MINIGIT_DIR
    )
    if unsafe:
        raise MinigitError(f"refusing to restore unsafe path {path!r}")
    return os.path.join(root, *parts)


def init():
    if os.path.exists(MINIGIT_DIR):
        print("Already a minigit repository.")
        return
    os.makedirs(os.path.join(MINIGIT_DIR, "objects"))
    with open(os.path.join(MINIGIT_DIR, "index"), "wb"):
        pass  # creates an empty file
    print("Initialized empty minigit repository.")


def tracked_name(root: str, entries: dict, rel_path: str, full_path: str) -> str:
    # On case-insensitive file systems (Windows, macOS) "a.txt" and "A.txt" are the
    # same file, so reuse the name already in the index instead of adding a duplicate
    if rel_path in entries:
        return rel_path
    for existing in entries:
        if existing.lower() == rel_path.lower():
            existing_path = os.path.join(root, existing)
            if os.path.exists(existing_path) and os.path.samefile(existing_path, full_path):
                return existing
    return rel_path


def stage(root: str, entries: dict, filepath: str) -> str:
    # Update entries for one path and return the message to print; raises before
    # touching the index file, so add() can stage all paths or none
    rel_path, full_path = to_repo_path(root, filepath)

    if not os.path.exists(full_path):
        # Adding a tracked file that was deleted stages its removal, like git add
        if rel_path in entries:
            del entries[rel_path]
            return f"Removed {rel_path}"
        raise MinigitError(f"file not found: {filepath}")
    if not os.path.isfile(full_path):
        raise MinigitError(f"not a file: {filepath}")

    rel_path = tracked_name(root, entries, rel_path, full_path)
    with open(full_path, "rb") as f:
        content = f.read()
    entries[rel_path] = write_object(content, os.path.join(root, MINIGIT_DIR))
    return f"Added {rel_path}"


def add(*filepaths: str):
    root = find_repo()
    entries = read_index(root)
    messages = [stage(root, entries, filepath) for filepath in filepaths]
    write_index(root, entries)
    for message in messages:
        print(message)


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


def has_unstaged_changes(root: str, entries: dict, path: str, target_hash: str) -> bool:
    # True if restoring would overwrite content that isn't saved anywhere: the file
    # differs from the version being restored and from its staged version
    full_path = working_path(root, path)
    if not os.path.isfile(full_path):
        return False
    with open(full_path, "rb") as f:
        current = hash_object(f.read())
    return current != target_hash and current != entries.get(path)


def blocked_by(root: str, path: str) -> str:
    # A folder where the file goes, or a file where one of its folders goes, stops the write
    full_path = working_path(root, path)
    if os.path.isdir(full_path):
        return f"a folder named {path} is in the way"
    folder = os.path.dirname(full_path)
    while folder != root:
        if os.path.exists(folder) and not os.path.isdir(folder):
            return f"a file is in the way of the folder {os.path.relpath(folder, root)}"
        folder = os.path.dirname(folder)
    return ""


def checkout(ref: str, *filepaths: str, force: bool = False):
    # Restore files from a commit into the working folder and stage them. HEAD doesn't
    # move: without branches, that would hide every later commit from log. Commit
    # afterwards to record the restored files as a new commit.
    root = find_repo()
    commit_hash = resolve_commit(root, ref)
    short_hash = commit_hash[:7]
    tree_hash, _, _ = read_commit(root, commit_hash)
    snapshot = parse_index(load_object(root, tree_hash, "tree"))

    if filepaths:
        paths = []
        for filepath in filepaths:
            rel_path, _ = to_repo_path(root, filepath)
            if rel_path not in snapshot:
                raise MinigitError(f"{filepath} is not in commit {short_hash}")
            paths.append(rel_path)
        paths = list(dict.fromkeys(paths))
    else:
        paths = sorted(snapshot)

    # Check everything before writing anything, so a problem leaves every file untouched
    contents = {path: load_object(root, snapshot[path], "file") for path in paths}
    for path in paths:
        problem = blocked_by(root, path)
        if problem:
            raise MinigitError(f"cannot restore {path}: {problem}")
    entries = read_index(root)
    if not force:
        at_risk = [path for path in paths if has_unstaged_changes(root, entries, path, snapshot[path])]
        if at_risk:
            listed = "\n".join(f"  {path}" for path in at_risk)
            raise MinigitError(
                "these files have changes that aren't staged and would be overwritten:\n"
                f"{listed}\nadd them first to keep the changes, or use --force to discard them"
            )

    messages = []
    for path in paths:
        full_path = working_path(root, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(contents[path])
        entries[path] = snapshot[path]
        messages.append(f"Restored {path}")
    if not filepaths:
        # A whole-snapshot checkout stages exactly that snapshot; other tracked files
        # stay on disk but won't be in the next commit
        for path in sorted(set(entries) - set(snapshot)):
            del entries[path]
            messages.append(f"Unstaged {path} (not in {short_hash}; the file is left in place)")
    write_index(root, entries)
    for message in messages:
        print(message)
