# #build_index.py
from pathlib import Path
import json
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
CORPUS_PATH = BASE_DIR / "data/corpus.json"
OUTPUT_PATH = BASE_DIR / "data/index.json"

def build_positional_index(corpus):
    """
    Build inverted index dengan positional information
    dan field-aware indexing
    """
    # Standard inverted index
    index = defaultdict(lambda: defaultdict(int))
    
    # Positional index (optional, untuk phrase query)
    positional_index = defaultdict(lambda: defaultdict(list))
    
    # Field-specific index untuk query expansion
    title_index = defaultdict(set)
    keyword_index = defaultdict(set)
    
    # Document length untuk BM25
    doc_len = {}
    
    # Document metadata
    doc_metadata = {}
    
    for doc in corpus:
        doc_id = doc["doc_id"]
        
        # Index weighted text untuk ranking
        tokens = doc["weighted_text"].split()
        doc_len[doc_id] = len(tokens)
        
        # Build inverted index
        for position, token in enumerate(tokens):
            index[token][doc_id] += 1
            positional_index[token][doc_id].append(position)
        
        # Index title terms (untuk boosting)
        if doc.get('title'):
            for token in doc['title'].split():
                title_index[token].add(doc_id)
        
        # Index keyword terms (untuk boosting)
        if doc.get('keywords'):
            for token in doc['keywords'].split():
                keyword_index[token].add(doc_id)
        
        # Save metadata
        doc_metadata[doc_id] = {
            'title': doc.get('title', '')[:200],
            'keywords': doc.get('keywords', '')[:200],
            'abstract': doc.get('abstract', '')[:500],
            'authors': doc.get('authors', '')[:100]
        }
    
    return {
        'index': dict(index),
        'positional_index': {k: dict(v) for k, v in positional_index.items()},
        'title_index': {k: list(v) for k, v in title_index.items()},
        'keyword_index': {k: list(v) for k, v in keyword_index.items()},
        'doc_len': doc_len,
        'doc_metadata': doc_metadata,
        'num_docs': len(doc_len),
        'avg_doc_len': sum(doc_len.values()) / len(doc_len) if doc_len else 0
    }

def main():
    print(f"Loading corpus from: {CORPUS_PATH}")
    
    if not CORPUS_PATH.exists():
        print(f"[ERROR] Corpus not found: {CORPUS_PATH}")
        return
    
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    
    print(f"Building index for {len(corpus)} documents...")
    
    index_data = build_positional_index(corpus)
    
    # Save index
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2)
    
    # Statistics
    print(f"\n[OK] Index built successfully!")
    print(f"  Total documents: {index_data['num_docs']}")
    print(f"  Total terms: {len(index_data['index'])}")
    print(f"  Average document length: {index_data['avg_doc_len']:.2f}")
    print(f"  Terms in title index: {len(index_data['title_index'])}")
    print(f"  Terms in keyword index: {len(index_data['keyword_index'])}")
    print(f"  Saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()