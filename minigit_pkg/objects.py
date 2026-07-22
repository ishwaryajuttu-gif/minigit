import hashlib 
def hash_object(content: bytes)->str:
    header=f"blob {len(content)}\0".encode()
    full_data=header+content
    digest=hashlib.sha1(full_data).hexdigest()
    return digest
