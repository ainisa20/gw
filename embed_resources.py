import os
import json
import zlib
import base64
import struct
import hashlib
import hmac

RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(RESOURCE_DIR, "_resources.py")

RESOURCE_FILES = ["chat.html", "fragments_structured.json", "fragment_matcher.py"]
PAGE_DIRS = [f"page{i:02d}" for i in range(1, 40)]

_MAGIC = b"FHRS"
_KEY_SALT = b"form-helper-resource-key-2026"


def _derive_bytes(password: bytes, salt: bytes, length: int) -> bytes:
    out = b""
    prev = b""
    counter = 1
    while len(out) < length:
        prev = hashlib.sha256(prev + password + salt + struct.pack(">I", counter)).digest()
        out += prev
        counter += 1
    return out[:length]


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    kl = len(key)
    return bytes(data[i] ^ key[i % kl] for i in range(len(data)))


def _encrypt(data: bytes, password: bytes) -> bytes:
    key = _derive_bytes(password, _KEY_SALT, 64)
    enc_key = key[:32]
    hmac_key = key[32:]
    compressed = zlib.compress(data, 9)
    encrypted = _xor_encrypt(compressed, enc_key)
    sig = hmac.new(hmac_key, encrypted, hashlib.sha256).digest()[:16]
    return _MAGIC + sig + encrypted


def _collect_files():
    files = {}
    for name in RESOURCE_FILES:
        path = os.path.join(RESOURCE_DIR, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                files[name] = f.read()

    for d in PAGE_DIRS:
        dir_path = os.path.join(RESOURCE_DIR, d)
        if not os.path.isdir(dir_path):
            continue
        for root, _, filenames in os.walk(dir_path):
            for fn in filenames:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, RESOURCE_DIR).replace("\\", "/")
                with open(full, "rb") as f:
                    files[rel] = f.read()
    return files


def main():
    password = b"fh2o25kXr7vQm9pL4wNs6yBz8jDc3eFg"

    files = _collect_files()
    print(f"Collected {len(files)} files")

    manifest = {}
    encrypted_blobs = []
    offset = 0

    for name, data in sorted(files.items()):
        encrypted = _encrypt(data, password)
        manifest[name] = {"offset": offset, "length": len(encrypted), "raw_size": len(data)}
        encrypted_blobs.append(encrypted)
        offset += len(encrypted)

    all_encrypted = b"".join(encrypted_blobs)
    b64_blob = base64.b64encode(all_encrypted).decode("ascii")

    print(f"Total encrypted: {len(all_encrypted)} bytes ({len(all_encrypted)/1024/1024:.1f} MB)")
    print(f"Base64 encoded: {len(b64_blob)} bytes ({len(b64_blob)/1024/1024:.1f} MB)")

    manifest_json = json.dumps(manifest, ensure_ascii=False)

    lines = [
        "import zlib, base64, json, hashlib, hmac, struct, os",
        "",
        f"_MANIFEST = json.loads({manifest_json!r})",
        f"_BLOB = {b64_blob!r}",
        f"_KEY_SALT = {_KEY_SALT!r}",
        "",
        "def _derive_bytes(password, salt, length):",
        "    out = b''",
        "    prev = b''",
        "    counter = 1",
        "    while len(out) < length:",
        "        prev = hashlib.sha256(prev + password + salt + struct.pack('>I', counter)).digest()",
        "        out += prev",
        "        counter += 1",
        "    return out[:length]",
        "",
        "def _decrypt(name):",
        "    info = _MANIFEST.get(name)",
        "    if not info:",
        "        return None",
        "    blob = base64.b64decode(_BLOB)",
        "    chunk = blob[info['offset']:info['offset']+info['length']]",
        "    if chunk[:4] != b'FHRS':",
        "        return None",
        "    sig = chunk[4:20]",
        "    encrypted = chunk[20:]",
        "    password = b'fh2o25kXr7vQm9pL4wNs6yBz8jDc3eFg'",
        "    key = _derive_bytes(password, _KEY_SALT, 64)",
        "    enc_key = key[:32]",
        "    hmac_key = key[32:]",
        "    expected_sig = hmac.new(hmac_key, encrypted, hashlib.sha256).digest()[:16]",
        "    if not hmac.compare_digest(sig, expected_sig):",
        "        return None",
        "    kl = len(enc_key)",
        "    compressed = bytes(encrypted[i] ^ enc_key[i % kl] for i in range(len(encrypted)))",
        "    return zlib.decompress(compressed)",
        "",
        "def get_text(name):",
        "    data = _decrypt(name)",
        "    return data.decode('utf-8') if data else None",
        "",
        "def get_bytes(name):",
        "    return _decrypt(name)",
        "",
        "def list_files(prefix=None):",
        "    if prefix is None:",
        "        return list(_MANIFEST.keys())",
        "    return [k for k in _MANIFEST.keys() if k.startswith(prefix)]",
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
