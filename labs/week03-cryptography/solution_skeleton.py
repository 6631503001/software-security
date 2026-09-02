"""
Week 3 — FIX the misuse here. Fill in the TODOs.
pip install argon2-cffi pycryptodome
"""
import hashlib
import os
from argon2 import PasswordHasher
from Crypto.Cipher import AES

ph = PasswordHasher()

def store_password(pw: str) -> str:
    # FIX: argon2id, salted automatically
    return ph.hash(pw)

def verify_password(hash_: str, pw: str) -> bool:
    try:
        return ph.verify(hash_, pw)
    except Exception:
        return False

def login_with_upgrade(username: str, password: str, user_db: dict) -> bool:
    # Task 6: upgrade a legacy MD5 record to argon2id on successful login
    stored_hash = user_db[username]
    if stored_hash.startswith("$argon2id$"):
        valid = verify_password(stored_hash, password)
        if valid and ph.check_needs_rehash(stored_hash):
            user_db[username] = ph.hash(password)
        return valid
    if hashlib.md5(password.encode()).hexdigest() == stored_hash:
        user_db[username] = ph.hash(password)   # upgrade only after the password checks out
        return True
    return False

def encrypt_gcm(data: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    # FIX: authenticated encryption (AES-GCM), random nonce, key from env/KMS
    nonce = os.urandom(12)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(data)
    return nonce, ct, tag

def decrypt_gcm(nonce: bytes, ciphertext: bytes, tag: bytes, key: bytes) -> bytes:
    # Task 7: verify the tag before returning plaintext (raises on tampering)
    return AES.new(key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(ciphertext, tag)

def reset_token() -> str:
    # FIX: CSPRNG
    import secrets
    return secrets.token_urlsafe(16)

if __name__ == "__main__":
    key = bytes.fromhex(os.environ.get("ENC_KEY_HEX", os.urandom(32).hex()))

    # --- Task 6: rehash-on-login upgrades a legacy MD5 record ---
    print("=" * 62)
    print("TASK 6 - Password storage: argon2id + rehash-on-login")
    print("=" * 62)
    user_db = {"alice": hashlib.md5(b"alicepw").hexdigest()}
    print(f"{'Legacy MD5 record':<28}: {user_db['alice']}")
    print(f"{'Login (correct pw)':<28}: {login_with_upgrade('alice', 'alicepw', user_db)}")
    print(f"{'Stored hash now':<28}: {user_db['alice'][:26]}...")
    print(f"{'-> migrated to argon2id':<28}: {user_db['alice'].startswith('$argon2id$')}")

    # --- Task 7: AES-GCM round-trip + tamper proof ---
    print("=" * 62)
    print("TASK 7 - Authenticated encryption: AES-GCM")
    print("=" * 62)
    nonce, ciphertext, tag = encrypt_gcm(b"secret message", key)
    print(f"{'Nonce (random 12 B)':<28}: {nonce.hex()}")
    print(f"{'Ciphertext':<28}: {ciphertext.hex()}")
    print(f"{'Auth tag':<28}: {tag.hex()}")
    print(f"{'Round-trip decrypt':<28}: {decrypt_gcm(nonce, ciphertext, tag, key)}")
    tampered_ciphertext = bytes([ciphertext[0] ^ 1]) + ciphertext[1:]
    print(f"{'Tampered (bit flipped)':<28}: {tampered_ciphertext.hex()}")
    try:
        decrypt_gcm(nonce, tampered_ciphertext, tag, key)
        print(f"{'Tampered decrypt':<28}: decrypted?! (bad)")
    except ValueError as error:
        print(f"{'Tampered decrypt':<28}: FAILED -> {error}")

    # --- Base fixes: argon2 verify + CSPRNG token ---
    print("=" * 62)
    print("BASE FIXES - argon2 verify + CSPRNG token")
    print("=" * 62)
    password_hash = store_password("password123")
    print(f"{'argon2 verify (correct)':<28}: {verify_password(password_hash, 'password123')}")
    print(f"{'argon2 verify (wrong)':<28}: {verify_password(password_hash, 'wrong')}")
    print(f"{'reset_token (secrets)':<28}: {reset_token()}")
