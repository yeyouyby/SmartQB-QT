import os
import re

# 4. core/assembly.py
with open('src/core/assembly.py', 'r') as f: content = f.read()
content = content.replace('from typing import List, Dict', 'from typing import List, Dict, Any')
content = content.replace('current_score = sum(q.get("score", 0) for q in paper)', 'current_score = sum(q.get("difficulty", 0.5) for q in paper) * 10')
content = content.replace('if not pool or len(pool) < max_size:', 'if not pool or len(pool) <= max_size:')
content = content.replace('new_q = random.choice([q for q in pool if q not in new_state])', '''candidates = [q for q in pool if q not in new_state]
            if candidates:
                new_q = random.choice(candidates)
            else:
                continue''')
with open('src/core/assembly.py', 'w') as f: f.write(content)

# 5. core/concurrency.py
with open('src/core/concurrency.py', 'r') as f: content = f.read()
content = content.replace('''            while p.is_alive():
                # Emit periodic fake progress updates for the progress ring
                time.sleep(0.1)''', '''            prog = 10
            while p.is_alive():
                prog = min(99, prog + 5)
                self.progress.emit(prog)
                time.sleep(0.1)''')

content = content.replace('''            result = result_queue.get()
            if result["status"] == "success":''', '''            try:
                import queue
                result = result_queue.get(timeout=30)
                if result["status"] == "success":''')
content = content.replace('                self.finished.emit(result["data"])', '                    self.finished.emit(result["data"])')
content = content.replace('            else:', '                else:')
content = content.replace('                self.error.emit(result["message"])', '                    self.error.emit(result["message"])')
content = content.replace('''        except Exception as e:
            self.error.emit(str(e))''', '''            except queue.Empty:
                self.error.emit("OCR Process Timeout")
                p.terminate()
        except Exception as e:
            self.error.emit(str(e))''')
with open('src/core/concurrency.py', 'w') as f: f.write(content)
