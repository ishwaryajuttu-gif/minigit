import hashlib
import os

def hash_object(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode()
    full_data = header + content
    digest = hashlib.sha1(full_data).hexdigest()
    return digest

def write_object(content: bytes, minigit_dir: str) -> str:
    digest = hash_object(content)
    objects_path = os.path.join(minigit_dir, "objects")
    os.makedirs(objects_path, exist_ok=True)
    file_path = os.path.join(objects_path, digest)
    with open(file_path, "wb") as f:
        f.write(content)
    return digest

def read_object(digest: str, minigit_dir: str) -> bytes:
    objects_path = os.path.join(minigit_dir, "objects")
    file_path = os.path.join(objects_path, digest)
    with open(file_path, "rb") as f:
        content = f.read()
    # An object's name is its hash, so a mismatch means the file was damaged or edited
    if hash_object(content) != digest:
        raise ValueError(f"object {digest} is corrupt: its content no longer matches its hash")
    return content