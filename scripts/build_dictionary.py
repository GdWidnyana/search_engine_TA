#build_dictionary.py
import json
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data/index.json"
BLOCK_PATH = BASE_DIR / "data/blocks.json"
FRONT_PATH = BASE_DIR / "data/frontcoded.json"

def front_code(terms):
    if not terms:
        return ""
    prefix = terms[0]
    for term in terms[1:]:
        i = 0
        while i < min(len(prefix), len(term)) and prefix[i] == term[i]:
            i += 1
        prefix = prefix[:i]
    return prefix + "*" + "|".join(t[len(prefix):] for t in terms)

if __name__ == "__main__":
    with open(INDEX_PATH, "r") as f:
        index_data = json.load(f)["index"]

    terms = sorted(index_data.keys())
    blocks = defaultdict(list)

    for t in terms:
        blocks[t[:3]].append(t)

    frontcoded = {
        k: front_code(v)
        for k, v in blocks.items()
    }

    with open(BLOCK_PATH, "w") as f:
        json.dump(blocks, f, indent=2)

    with open(FRONT_PATH, "w") as f:
        json.dump(frontcoded, f, indent=2)

    print("[OK] Dictionary built (blocking + front coding)")
