import hmac
import hashlib
import base64
import os
import json
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from argon2 import PasswordHasher


class KMSManager:
    """
    Key Management System for SmartQB.
    Implements Hybrid KMS with Argon2, AES-256-GCM, and RSA-2048.
    """

    ARGON2_TIME_COST = 3
    ARGON2_MEMORY_COST = 65536
    ARGON2_PARALLELISM = 4
    ARGON2_HASH_LEN = 32
    ARGON2_SALT_LEN = 16

    def __init__(self):
        # Argon2 configuration matching current security standards
        self.ph = PasswordHasher(
            time_cost=self.ARGON2_TIME_COST,
            memory_cost=self.ARGON2_MEMORY_COST,
            parallelism=self.ARGON2_PARALLELISM,
            hash_len=self.ARGON2_HASH_LEN,
            salt_len=self.ARGON2_SALT_LEN,
        )

    def derive_master_key(self, password: str, salt: bytes) -> bytes:
        """
        Derives an AES-256 (32 bytes) master key from a password using Argon2.
        Note: The returned key is 32 bytes of raw material extracted from Argon2 hash.
        We use the raw hash value since Argon2 handles salting internally.
        """
        # argon2-cffi's hash() returns a formatted string. For raw key derivation
        # we can use the low-level API or hash string extraction.
        from argon2.low_level import hash_secret_raw, Type

        # password to bytes
        password_bytes = password.encode("utf-8")

        raw_hash = hash_secret_raw(
            secret=password_bytes,
            salt=salt,
            time_cost=self.ARGON2_TIME_COST,
            memory_cost=self.ARGON2_MEMORY_COST,
            parallelism=self.ARGON2_PARALLELISM,
            hash_len=self.ARGON2_HASH_LEN,
            type=Type.ID,
        )
        return raw_hash

    def generate_rsa_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generates an RSA-2048 key pair.
        Returns:
            Tuple[bytes, bytes]: (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return private_pem, public_pem

    def encrypt_aes_gcm(self, data: bytes, key: bytes) -> Tuple[bytes, bytes]:
        """
        Encrypts data using AES-256-GCM.
        Returns:
            Tuple[bytes, bytes]: (ciphertext with auth tag, nonce)
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return ciphertext, nonce

    def decrypt_aes_gcm(self, ciphertext: bytes, nonce: bytes, key: bytes) -> bytes:
        """
        Decrypts data using AES-256-GCM.
        """
        aesgcm = AESGCM(key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext
        except InvalidTag as e:
            raise ValueError(f"Decryption failed or data tampered: {e}")

    def encrypt_rsa(self, data: bytes, public_key_pem: bytes) -> bytes:
        """
        Encrypts data using RSA Public Key (for the supervisory copy).
        """
        public_key = serialization.load_pem_public_key(public_key_pem)
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return ciphertext

    def decrypt_rsa(self, ciphertext: bytes, private_key_pem: bytes) -> bytes:
        """
        Decrypts data using RSA Private Key.
        """
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
        )
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext

    def sign_config(self, config_dict: dict, master_key: bytes) -> str:
        """
        Calculates HMAC-SHA256 signature for a dictionary to prevent tampering.
        """
        # Ensure consistent serialization order
        config_str = json.dumps(config_dict, sort_keys=True)
        h = hmac.new(master_key, config_str.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(h.digest()).decode("utf-8")

    def verify_config_signature(
        self, config_dict: dict, signature: str, master_key: bytes
    ) -> bool:
        """
        Verifies HMAC-SHA256 signature of a config dictionary.
        """
        expected_sig = self.sign_config(config_dict, master_key)
        return hmac.compare_digest(expected_sig, signature)

    def zero_memory(self, byte_array: bytearray):
        """
        Zeroes out memory of a bytearray to protect sensitive keys from remaining in memory.
        Note: Python memory management makes true memory zeroing difficult, but bytearrays
        can be overwritten before garbage collection.
        """
        for i in range(len(byte_array)):
            byte_array[i] = 0
