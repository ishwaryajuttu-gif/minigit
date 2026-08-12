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