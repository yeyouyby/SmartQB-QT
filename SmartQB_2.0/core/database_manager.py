import lancedb
import pyarrow as pa
from pathlib import Path
from typing import Optional

from pysqlcipher3 import dbapi2 as sqlite


class SQLiteManager:
    """
    Manages the encrypted sys_master.db using pysqlcipher3.
    Enforces AES-256 transparent encryption on the entire file.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite.Connection] = None

    def connect(self, key: str) -> None:
        """
        Connects to the database and applies the master key for transparent encryption.
        """
        self.conn = sqlite.connect(str(self.db_path))

        # Pragmas to configure SQLCipher
        # Escape single quotes by doubling them for safe PRAGMA parameterization
        safe_key = key.replace("'", "''")
        pragma_stmt = "PRAGMA key = '" + safe_key + "';"
        self.conn.execute(
            pragma_stmt
        )  # sourcery skip: sqlalchemy-execute-raw-query, sql-injection, avoid-sql-string-concatenation
        self.conn.execute("PRAGMA cipher_page_size = 4096;")
        self.conn.execute("PRAGMA kdf_iter = 600000;")
        self.conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA256;")
        self.conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA256;")

        # Test connection
        try:
            self.conn.execute("SELECT count(*) FROM sqlite_master;")
        except sqlite.DatabaseError:
            raise ValueError("Invalid database key or corrupted database.")

    def init_schema(self) -> None:
        """
        Initializes the superadmin and keys table structure.
        """
        if not self.conn:
            raise RuntimeError("Database connection not established.")

        cursor = self.conn.cursor()

        # Table for storing the super admin's encrypted private key and salt
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS superadmin_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salt BLOB NOT NULL,
                public_key_pem BLOB NOT NULL,
                private_key_ciphertext BLOB NOT NULL,
                private_key_nonce BLOB NOT NULL
            )
        """)

        self.conn.commit()


class LanceDBManager:
    """
    Manages the multi-modal vector database using LanceDB.
    """

    def __init__(self, db_dir: Path):
        # LanceDB directory is separate from sys_master.db
        self.db_path = db_dir / "knowledge_vectors.lance"
        self.db = lancedb.connect(str(self.db_path))

        # Define the strict PyArrow schema for Document Blocks
        self.schema = pa.schema(
            [
                pa.field("snowflake_id", pa.int64()),
                pa.field(
                    "vector", pa.list_(pa.float32(), 1024)
                ),  # e.g. BGE-m3 / OpenAI dimension
                pa.field("content_md", pa.string()),
                pa.field("logic_chain", pa.string()),
                pa.field("tags", pa.list_(pa.string())),
                pa.field("created_at", pa.timestamp("s")),
            ]
        )

        # Create table if it doesn't exist
        self.table_name = "questions"
        if self.table_name not in self.db.table_names():
            self.table = self.db.create_table(self.table_name, schema=self.schema)
        else:
            self.table = self.db.open_table(self.table_name)

    def insert_batch(self, data_batch: list[dict]) -> None:
        """
        Executes a single bulk insert transaction to LanceDB using the PyArrow table.
        Avoids I/O bottlenecks.
        """
        # Convert dictionary batch to PyArrow Table based on schema
        pa_table = pa.Table.from_pylist(data_batch, schema=self.schema)
        self.table.add(pa_table)
