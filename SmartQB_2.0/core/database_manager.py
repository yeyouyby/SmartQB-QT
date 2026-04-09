import lancedb
import pyarrow as pa
from pathlib import Path
from typing import Optional, Any

from pysqlcipher3 import dbapi2 as sqlite


class SQLiteManager:
    """
    Manages the encrypted sys_master.db using pysqlcipher3.
    Enforces AES-256 transparent encryption on the entire file.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn: Optional[sqlite.Connection] = None

    def connect(self, key: bytearray) -> None:
        """
        Connects to the database and applies the master key for transparent encryption.
        """
        if self.conn:
            self.conn.close()
        self.conn = sqlite.connect(str(self.db_path))

        # Pragmas to configure SQLCipher
        # Construct the PRAGMA query string safely. String construction is necessary as
        # sqlite3 DB-API does not allow parameter binding for PRAGMA statements.
        pragma_key_query = f"PRAGMA key = \"x'{key.hex()}'\";"
        self.conn.execute(pragma_key_query)
        self.conn.execute("PRAGMA cipher_page_size = 4096;")
        self.conn.execute("PRAGMA kdf_iter = 600000;")
        self.conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA256;")
        self.conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA256;")

        # Test connection
        try:
            self.conn.execute("SELECT count(*) FROM sqlite_master;")
        except sqlite.DatabaseError:
            if self.conn:
                self.conn.close()
            self.conn = None
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

    def __init__(self, db_dir: Path, vector_dim: int = 1024):
        # LanceDB directory is separate from sys_master.db
        self.db_path = db_dir / "knowledge_vectors.lance"
        self.vector_dim = vector_dim

        self.db: Any = None
        self.table: Any = None

        # Define the strict PyArrow schema for Document Blocks
        self.schema = pa.schema(
            [
                pa.field("snowflake_id", pa.int64()),
                pa.field(
                    "vector", pa.list_(pa.float32(), self.vector_dim)
                ),  # e.g. BGE-m3 / OpenAI dimension
                pa.field("content_md", pa.string()),
                pa.field("logic_chain", pa.string()),
                pa.field("tags", pa.list_(pa.string())),
                pa.field("created_at", pa.timestamp("s")),
            ]
        )

    def connect(self) -> None:
        """
        Establishes the LanceDB connection.
        This is separated from __init__ to avoid blocking the GUI thread.
        """
        self.db = lancedb.connect(str(self.db_path))

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
        if not data_batch:
            return
        pa_table = pa.Table.from_pylist(data_batch, schema=self.schema)
        self.table.add(pa_table)
