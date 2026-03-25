import time
import lancedb
from lancedb.pydantic import Vector, LanceModel
from pydantic import BaseModel, Field
import threading
from typing import List, Optional

class SnowflakeID:
    """
    Generates pure digital, time-ordered, natural anti-collision IDs.
    Very fast for retrieval.
    """
    def __init__(self, datacenter_id=1, worker_id=1, sequence=0):
        self.twepoch = 1609459200000 # 2021-01-01
        self.datacenter_id_bits = 5
        self.worker_id_bits = 5
        self.sequence_bits = 12

        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)

        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_left_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits

        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)

        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = sequence
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def _wait_next_millis(self, last_timestamp):
        timestamp = self._get_time()
        while timestamp <= last_timestamp:
            timestamp = self._get_time()
        return timestamp

    def _get_time(self):
        return int(time.time() * 1000)

    def generate(self) -> int:
        with self._lock:
            timestamp = self._get_time()
            if timestamp < self.last_timestamp:
                raise Exception("Clock moved backwards")

            if timestamp == self.last_timestamp:
                    self.sequence = (self.sequence + 1) & self.sequence_mask
                if self.sequence == 0:
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                    self.sequence = 0

            self.last_timestamp = timestamp

            return ((timestamp - self.twepoch) << self.timestamp_left_shift) | \
                   (self.datacenter_id << self.datacenter_id_shift) | \
                   (self.worker_id << self.worker_id_shift) | \
                   self.sequence

# Create global ID generator
snowflake = IdGenerator()


# ---- LanceDB Data Models (Pydantic based) ----

class BaseLanceEntity(LanceModel):
    id: int # Snowflake ID

class Question(BaseLanceEntity):
    """Core Questions stored in standard Markdown + MathJax ($$) format"""
    content_md: str
    solution_md: Optional[str] = None
    difficulty: float = 0.5
    tags: List[str] = Field(default_factory=list)
    vector: Vector(1536) # Assume OpenAI 1536-dim embeddings for now

class Draft(BaseLanceEntity):
    """Temporary storage (暂存区/草稿箱) for documents waiting for code review"""
    original_file: str
    parsed_md: str
    status: str = "pending" # pending, reviewing, approved

class ExamGroup(BaseLanceEntity):
    """Logical grouping in an ExamBag (e.g. '一、选择题')"""
    title: str
    description: Optional[str] = ""

class ExamBag(BaseLanceEntity):
    """Collection of groups forming a complete test."""
    title: str
    created_at: int # Timestamp
    group_ids: List[int] # Reference to ExamGroup

class QuestionMap(BaseLanceEntity):
    """Maps ExamGroups to Question IDs to avoid duplication"""
    group_id: int
    question_id: int
    order_idx: int


def init_lancedb(uri: str = "./lancedb_store"):
    """Initializes the database connection and creates tables if they don't exist"""
    db = lancedb.connect(uri)

    # Create tables
    if "questions" not in db.list_tables():
        db.create_table("questions", schema=Question)
    if "drafts" not in db.list_tables():
        db.create_table("drafts", schema=Draft)
    if "exambags" not in db.list_tables():
        db.create_table("exambags", schema=ExamBag)
    if "examgroups" not in db.list_tables():
        db.create_table("examgroups", schema=ExamGroup)
    if "questionmaps" not in db.list_tables():
        db.create_table("questionmaps", schema=QuestionMap)

    return db
