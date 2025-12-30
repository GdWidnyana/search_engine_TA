# scripts/wildcard.py
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PERMUTERM_PATH = BASE_DIR / "data/permuterm.json"

class WildcardExpander:
    def __init__(self):
        with open(PERMUTERM_PATH) as f:
            self.permuterm = json.load(f)

    def expand(self, pattern: str):
        """
        Contoh:
        mach*     -> mach$
        *ment     -> ment$*
        ana*is    -> is$ana*
        """

        if "*" not in pattern:
            return [pattern]

        before, after = pattern.split("*")

        rotated_query = after + "$" + before
        results = set()

        for key, terms in self.permuterm.items():
            if key.startswith(rotated_query):
                for t in terms:
                    results.add(t)

        return list(results)