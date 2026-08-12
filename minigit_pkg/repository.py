import os
from minigit_pkg.objects import write_object

MINIGIT_DIR = ".minigit"

def init():
    if os.path.exists(MINIGIT_DIR):
        print("Already a minigit repository.")
        return
    os.makedirs(os.path.join(MINIGIT_DIR, "objects"))
    with open(os.path.join(MINIGIT_DIR, "index"), "w") as f:
        pass  # creates an empty file
    print("Initialized empty minigit repository.")

def add(filepath: str):
    with open(filepath, "rb") as f:
        content = f.read()
    digest = write_object(content, MINIGIT_DIR)
    with open(os.path.join(MINIGIT_DIR, "index"), "a") as f:
        f.write(f"{filepath} {digest}\n")
    print(f"Added {filepath}")
def write_tree():
    index_path = os.path.join(MINIGIT_DIR, "index")
    with open(index_path, "rb") as f:
        index_content = f.read()
    tree_hash = write_object(index_content, MINIGIT_DIR)
    return tree_hash

def commit(message: str):
    tree_hash = write_tree()

    head_path = os.path.join(MINIGIT_DIR, "HEAD")
    if os.path.exists(head_path):
        with open(head_path, "r") as f:
            parent_hash = f.read().strip()
    else:
        parent_hash = ""

    commit_content = f"tree {tree_hash}\nparent {parent_hash}\n\n{message}"
    commit_hash = write_object(commit_content.encode(), MINIGIT_DIR)

    with open(head_path, "w") as f:
        f.write(commit_hash)

    print(f"Committed as {commit_hash}")
    return commit_hash
def log():
    head_path = os.path.join(MINIGIT_DIR, "HEAD")
    if not os.path.exists(head_path):
        print("No commits yet.")
        return

    with open(head_path, "r") as f:
        current_hash = f.read().strip()

    commits = []
    while current_hash:
        commit_content = read_object(current_hash, MINIGIT_DIR).decode()
        commits.append((current_hash, commit_content))

        lines = commit_content.split("\n")
        parent_line = lines[1]  # "parent <hash>" or "parent "
        parent_hash = parent_line[len("parent "):].strip()
        current_hash = parent_hash

        # your code: extract the parent hash from commit_content
        # (it's on the line that starts with "parent ")
        # then set current_hash to that value, or "" if empty

    commits.reverse()

    for commit_hash, content in commits:
        print(f"commit {commit_hash}")
        message = content.split("\n\n", 1)[1]
        print(f"    {message}")
        print()
    
from minigit_pkg.objects import write_object, read_object
import os
from minigit_pkg.objects import write_object, read_object