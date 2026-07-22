import hashlib


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
