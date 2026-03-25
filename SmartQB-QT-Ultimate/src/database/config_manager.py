import sqlite3
import base64
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class ConfigManager:
    """
    Manages lightweight configuration using SQLite.
    Includes AES-256-GCM encryption/decryption for API keys and sensitive data.
    """
    def __init__(self, db_path: str = "config.db"):
        self.db_path = db_path
        self._key = None
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database and the settings table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    is_encrypted BOOLEAN NOT NULL DEFAULT 0
                )
            ''')
            conn.commit()

    def set_master_key(self, master_password: str) -> None:
        """Derives a strong AES-256-GCM key from the user's master password with persistent random salt."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM settings WHERE key = ? AND is_encrypted = 0",
                ("kdf_salt",),
            )
            row = cursor.fetchone()
            if row:
                salt = base64.b64decode(row[0])
            else:
                salt = os.urandom(16)
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO settings (key, value, is_encrypted)
                    VALUES (?, ?, 0)
                    """,
                    ("kdf_salt", base64.b64encode(salt).decode("utf-8")),
                )
                conn.commit()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        self._key = kdf.derive(master_password.encode())

    def _encrypt(self, data: str) -> str:
        """Encrypts data using AES-GCM."""
        if not self._key:
            raise ValueError("Master key not set. Call set_master_key() first.")
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def _decrypt(self, encrypted_data_b64: str) -> str:
        """Decrypts AES-GCM encrypted data."""
        if not self._key:
            raise ValueError("Master key not set. Call set_master_key() first.")
        encrypted_data = base64.b64decode(encrypted_data_b64)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        aesgcm = AESGCM(self._key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')

    def set_value(self, key: str, value: str, encrypt: bool = False):
        """Stores a key-value pair in the database."""
        store_value = self._encrypt(value) if encrypt else value
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, is_encrypted)
                VALUES (?, ?, ?)
            ''', (key, store_value, encrypt))
            conn.commit()

    def get_value(self, key: str, default: str = None) -> str:
        """Retrieves a value from the database, decrypting if necessary."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value, is_encrypted FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()

        if result is None:
            return default

        value, is_encrypted = result
        if is_encrypted:
            if not self._key:
                # Master key not present, gracefully return default instead of confusing caller
                import logging
                logging.warning(f"Master key missing: Cannot decrypt '{key}'. Returning default.")
                return default
            try:
                return self._decrypt(value)
            except ValueError as e:
                import logging
                logging.error(f"Decryption failed for '{key}': {e}")
                return default
        return value
