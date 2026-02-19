import base64
import hashlib
import hmac
import secrets
import time

from ..db import get_conn

PBKDF2_ITERATIONS = 200_000
SALT_SIZE = 16
NONCE_SIZE = 16


def _b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def _normalize_mnemonic(mnemonic: str) -> str:
    return " ".join(mnemonic.strip().split())


def _validate_mnemonic(mnemonic: str) -> None:
    words = mnemonic.split()
    if len(words) not in (12, 15, 18, 21, 24):
        raise ValueError("mnemonic word count must be one of 12/15/18/21/24")


def _derive_keys(passphrase: str, salt: bytes) -> tuple[bytes, bytes]:
    material = hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=64,
    )
    return material[:32], material[32:]


def _xor_stream(data: bytes, key: bytes, nonce: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < len(data):
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    stream = bytes(out[: len(data)])
    return bytes(a ^ b for a, b in zip(data, stream))


def _encrypt_mnemonic(mnemonic: str, passphrase: str) -> dict[str, str]:
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    enc_key, mac_key = _derive_keys(passphrase, salt)
    plaintext = mnemonic.encode("utf-8")
    ciphertext = _xor_stream(plaintext, enc_key, nonce)
    mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    return {
        "salt_b64": _b64e(salt),
        "nonce_b64": _b64e(nonce),
        "ciphertext_b64": _b64e(ciphertext),
        "mac_b64": _b64e(mac),
    }


def _decrypt_blob(ciphertext_b64: str, salt_b64: str, nonce_b64: str, mac_b64: str, passphrase: str) -> str:
    salt = _b64d(salt_b64)
    nonce = _b64d(nonce_b64)
    ciphertext = _b64d(ciphertext_b64)
    expected_mac = _b64d(mac_b64)
    enc_key, mac_key = _derive_keys(passphrase, salt)
    actual_mac = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_mac, actual_mac):
        raise ValueError("vault mac mismatch")
    plaintext = _xor_stream(ciphertext, enc_key, nonce)
    return plaintext.decode("utf-8")


def _ensure_table() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vault_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_ref TEXT NOT NULL UNIQUE,
                encrypted_mnemonic_b64 TEXT NOT NULL,
                salt_b64 TEXT NOT NULL,
                nonce_b64 TEXT NOT NULL,
                mac_b64 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                last_used_at INTEGER
            )
            """
        )


def upsert_key_ref(key_ref: str, mnemonic: str, passphrase: str) -> None:
    _ensure_table()
    if not key_ref.startswith("vault://"):
        raise ValueError("key_ref must start with vault://")
    normalized = _normalize_mnemonic(mnemonic)
    _validate_mnemonic(normalized)
    now = int(time.time())
    blob = _encrypt_mnemonic(normalized, passphrase)
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM vault_keys WHERE key_ref=?", (key_ref,)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE vault_keys
                SET encrypted_mnemonic_b64=?, salt_b64=?, nonce_b64=?, mac_b64=?, status='active', updated_at=?
                WHERE key_ref=?
                """,
                (blob["ciphertext_b64"], blob["salt_b64"], blob["nonce_b64"], blob["mac_b64"], now, key_ref),
            )
            return
        conn.execute(
            """
            INSERT INTO vault_keys(
                key_ref, encrypted_mnemonic_b64, salt_b64, nonce_b64, mac_b64, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (key_ref, blob["ciphertext_b64"], blob["salt_b64"], blob["nonce_b64"], blob["mac_b64"], now, now),
        )


def key_ref_exists(key_ref: str) -> bool:
    _ensure_table()
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM vault_keys WHERE key_ref=? AND status='active'", (key_ref,)).fetchone()
    return bool(row)


def list_key_refs() -> list[dict[str, str]]:
    _ensure_table()
    query = """
    SELECT key_ref, status, created_at, updated_at
    FROM vault_keys
    ORDER BY id ASC
    """
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def get_secret_by_key_ref(key_ref: str, passphrase: str) -> str:
    _ensure_table()
    if not passphrase:
        raise ValueError("vault passphrase is not set")
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT encrypted_mnemonic_b64, salt_b64, nonce_b64, mac_b64
            FROM vault_keys
            WHERE key_ref=? AND status='active'
            """,
            (key_ref,),
        ).fetchone()
    if not row:
        raise ValueError(f"vault key_ref not found: {key_ref}")
    return _decrypt_blob(
        ciphertext_b64=str(row["encrypted_mnemonic_b64"]),
        salt_b64=str(row["salt_b64"]),
        nonce_b64=str(row["nonce_b64"]),
        mac_b64=str(row["mac_b64"]),
        passphrase=passphrase,
    )
