# scripts/spelling.py
import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
KGRAM_PATH = BASE_DIR / "data/kgram.json"

class SpellCorrector:
    def __init__(self, k=3, max_dist=2):
        self.k = k
        self.max_dist = max_dist
        with open(KGRAM_PATH) as f:
            self.kgram_index = json.load(f)

    def _kgrams(self, word):
        word = f"${word}$"
        return [word[i:i+self.k] for i in range(len(word)-self.k+1)]

    def edit_distance(self, a, b):
        dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
        for i in range(len(a)+1):
            dp[i][0] = i
        for j in range(len(b)+1):
            dp[0][j] = j

        for i in range(1, len(a)+1):
            for j in range(1, len(b)+1):
                cost = 0 if a[i-1] == b[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,
                    dp[i][j-1] + 1,
                    dp[i-1][j-1] + cost
                )
        return dp[-1][-1]

    def correct(self, term):
        grams = self._kgrams(term)
        candidates = Counter()

        # 🔹 ambil kandidat dari k-gram index
        for g in grams:
            if g in self.kgram_index:
                for cand in self.kgram_index[g]:
                    candidates[cand] += 1

        if not candidates:
            return term

        # 🔹 filter dan ranking
        scored = []
        for cand, overlap in candidates.items():
            dist = self.edit_distance(term, cand)
            if dist <= self.max_dist:
                scored.append((cand, dist, overlap))

        if not scored:
            return term

        # ranking: edit distance → overlap k-gram
        scored.sort(key=lambda x: (x[1], -x[2]))
        return scored[0][0]
