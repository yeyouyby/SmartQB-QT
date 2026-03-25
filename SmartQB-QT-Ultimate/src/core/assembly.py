import random
import math
from typing import List, Dict, Any

class ExamAssemblerSA:
    """
    Simulated Annealing algorithm for intelligent exam generation.
    """
    def __init__(self, target_score: int, target_difficulty: float, constraints: Dict[str, Any]):
        self.target_score = target_score
        self.target_difficulty = target_difficulty
        self.constraints = constraints

        self.initial_temp = 100.0
        self.cooling_rate = 0.95
        self.min_temp = 0.1

    def energy(self, paper: List[Dict]) -> float:
        """ Calculate how far the current paper is from the target. Lower is better. """
        if not paper:
            return float('inf')

        current_score = sum(q.get("score", 10) for q in paper)
        current_diff = sum(q.get("difficulty", 0.5) for q in paper) / len(paper)

        # Penalties
        score_penalty = abs(current_score - self.target_score) * 10
        diff_penalty = abs(current_diff - self.target_difficulty) * 100

        tag_penalty = 0
        target_tags = self.constraints.get("tags", [])
        paper_tags = set(tag for q in paper for tag in q.get("tags", []))
        for tag in target_tags:
            if tag not in paper_tags:
                tag_penalty += 50

        return score_penalty + diff_penalty + tag_penalty

    def assemble(self, pool: List[Dict], max_size: int = 20) -> List[Dict]:
        """ Runs SA algorithm over the question pool """
        if not pool or len(pool) <= max_size:
            return pool

        # Initial random state
        current_state = random.sample(pool, max_size)
        current_energy = self.energy(current_state)
        best_state = list(current_state)
        best_energy = current_energy

        temp = self.initial_temp

        while temp > self.min_temp:
            # Generate neighbor state by swapping one random question
            new_state = list(current_state)
            idx_to_remove = random.randint(0, len(new_state) - 1)
            new_state_ids = {q['id'] for q in new_state}
            candidates = [q for q in pool if q['id'] not in new_state_ids]
            if candidates:
                new_q = random.choice(candidates)
            else:
                temp *= self.cooling_rate
                continue
            new_state[idx_to_remove] = new_q

            new_energy = self.energy(new_state)

            # Acceptance probability
            if new_energy < current_energy:
                current_state = new_state
                current_energy = new_energy
                if new_energy < best_energy:
                    best_state = list(new_state)
                    best_energy = new_energy
            else:
                p = math.exp((current_energy - new_energy) / temp)
                if random.random() < p:
                    current_state = new_state
                    current_energy = new_energy

            temp *= self.cooling_rate

        return best_state
