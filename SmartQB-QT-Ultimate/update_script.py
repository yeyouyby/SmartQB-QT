import os
import re

# 1. README.md
with open('README.md', 'r') as f: content = f.read()
content = content.replace('## Features\n-', '## Features\n\n-')
with open('README.md', 'w') as f: f.write(content)

# 2. .gitignore
with open('.gitignore', 'w') as f:
    f.write('lancedb_store/\n')
    f.write('test_config.db\n')
    f.write('venv/\n')
    f.write('__pycache__/\n')
    f.write('*.pyc\n')

# 3. database/models.py
with open('src/database/models.py', 'r') as f: content = f.read()
content = content.replace('from pydantic import BaseModel', 'from pydantic import BaseModel, Field\nimport threading')
content = content.replace('tags: List[str] = []', 'tags: List[str] = Field(default_factory=list)')

# Snowflake updates
snowflake_old = """        self.sequence = sequence
        self.last_timestamp = -1

    def _get_time(self):"""
snowflake_new = """        self.sequence = sequence
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def _wait_next_millis(self, last_timestamp):
        timestamp = self._get_time()
        while timestamp <= last_timestamp:
            timestamp = self._get_time()
        return timestamp

    def _get_time(self):"""
content = content.replace(snowflake_old, snowflake_new)

generate_old = """    def generate(self) -> int:
        timestamp = self._get_time()"""
generate_new = """    def generate(self) -> int:
        with self._lock:
            timestamp = self._get_time()"""
content = content.replace(generate_old, generate_new)
content = content.replace('        if timestamp < self.last_timestamp:', '            if timestamp < self.last_timestamp:')
content = content.replace('            raise Exception("Clock moved backwards")', '                raise Exception("Clock moved backwards")')
content = content.replace('        if timestamp == self.last_timestamp:', '            if timestamp == self.last_timestamp:')
content = content.replace('            self.sequence = (self.sequence + 1) & self.sequence_mask', '                self.sequence = (self.sequence + 1) & self.sequence_mask')
content = content.replace('            if self.sequence == 0:', '                if self.sequence == 0:')
content = content.replace('                timestamp = self._wait_next_millis(self.last_timestamp)', '                    timestamp = self._wait_next_millis(self.last_timestamp)')
content = content.replace('        else:', '            else:')
content = content.replace('            self.sequence = 0', '                self.sequence = 0')
content = content.replace('        self.last_timestamp = timestamp', '            self.last_timestamp = timestamp')
content = content.replace('        return ((timestamp - self.twepoch) << self.timestamp_left_shift) | \\', '            return ((timestamp - self.twepoch) << self.timestamp_left_shift) | \\')
content = content.replace('               (self.datacenter_id << self.datacenter_id_shift) | \\', '                   (self.datacenter_id << self.datacenter_id_shift) | \\')
content = content.replace('               (self.worker_id << self.worker_id_shift) | \\', '                   (self.worker_id << self.worker_id_shift) | \\')
content = content.replace('               self.sequence', '                   self.sequence')
with open('src/database/models.py', 'w') as f: f.write(content)
