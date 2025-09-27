# cert_utils.py
import hashlib
from web3 import Web3


def compute_sha256_hex(file_path):
    """Return the hex (without 0x) of SHA-256 of the file"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()  # 64 hex chars


def sha256_hex_to_bytes32(hexstr):
    """Convert hex string (64 chars or with 0x) to 0x-prefixed 32-byte hex for contract"""
    h = hexstr.lower()
    if h.startswith("0x"):
        h = h[2:]
    if len(h) != 64:
        raise ValueError("sha256 hex string must be 64 hex chars")
    return Web3.to_bytes(hexstr="0x" + h)
