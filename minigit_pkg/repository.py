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