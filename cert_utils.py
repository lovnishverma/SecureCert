import hashlib
from web3 import Web3


def compute_sha256_hex(file_path):
    """Return the hex (without 0x) of SHA-256 of the file"""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()  # 64 hex chars
    except Exception as e:
        raise Exception(f"Error computing hash: {e}")


def sha256_hex_to_bytes32(hexstr):
    """Convert hex string (64 chars or with 0x) to bytes32 for contract"""
    h = hexstr.lower()
    if h.startswith("0x"):
        h = h[2:]
    if len(h) != 64:
        raise ValueError("SHA256 hex string must be 64 hex chars")
    return Web3.to_bytes(hexstr="0x" + h)


def format_timestamp(timestamp):
    """Convert Unix timestamp to readable format"""
    if timestamp == 0:
        return "Not issued"

    import datetime
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def validate_certificate_id(cert_id):
    """Validate certificate ID format"""
    if not cert_id or len(cert_id.strip()) == 0:
        return False, "Certificate ID cannot be empty"

    if len(cert_id) > 100:
        return False, "Certificate ID too long (max 100 characters)"

    # Check for valid characters (alphanumeric, hyphens, underscores)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', cert_id):
        return False, "Certificate ID can only contain letters, numbers, hyphens, and underscores"

    return True, "Valid"


def get_file_info(file):
    """Get file information and validate"""
    if not file or not file.filename:
        return False, "No file selected"

    # Check file extension
    allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        return False, f"File type {file_ext} not allowed. Use: {', '.join(allowed_extensions)}"

    # Check file size (in memory, approximate)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Seek back to beginning

    max_size = 10 * 1024 * 1024  # 10MB
    if size > max_size:
        return False, f"File too large ({size/1024/1024:.1f}MB). Max size: 10MB"

    return True, {"filename": file.filename, "size": size, "extension": file_ext}
