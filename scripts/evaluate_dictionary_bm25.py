# evaluate_dictionary_bm25.py
"""
Evaluasi BM25 Ranker yang menggunakan Blocked Dictionary + Front Coding
"""

import json
from pathlib import Path
import sys
import math

# Import ranker
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bm25_with_dictionary import DictionaryBM25Ranker

BASE_DIR = Path(__file__).resolve().parent.parent
BLOCKS_PATH = BASE_DIR / "data/blocks.json"
FRONTCODED_PATH = BASE_DIR / "data/frontcoded.json"
INDEX_PATH = BASE_DIR / "data/index.json"
TEST_QUERIES_PATH = Path(__file__).resolve().parent / "test_queries.json"
EVAL_OUTPUT = BASE_DIR / "data/evaluation_dictionary_bm25.json"


def load_test_queries():
    """Load test queries dengan relevance judgments"""
    if not TEST_QUERIES_PATH.exists():
        print(f"[ERROR] test_queries.json tidak ditemukan: {TEST_QUERIES_PATH}")
        print("\nSilakan buat file test_queries.json dengan format:")
        print("""
{
  "query string": ["doc_0", "doc_1", "doc_5"],
  "sistem rekomendasi": ["doc_10", "doc_25", "doc_30"],
  "machine learning": ["doc_15", "doc_20"]
}
        """)
        return None
    
    with open(TEST_QUERIES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_average_precision(retrieved, relevant):
    """
    Calculate Average Precision untuk satu query
    
    AP = (1/R) * Σ(P(k) * rel(k))
    where:
    - R = total relevant documents
    - P(k) = precision at position k
    - rel(k) = 1 if doc at k is relevant, 0 otherwise
    """
    if not retrieved or not relevant:
        return 0.0
    
    relevant_set = set(relevant)
    score = 0.0
    num_relevant_found = 0
    
    for i, doc_id in enumerate(retrieved, 1):
        if doc_id in relevant_set:
            num_relevant_found += 1
            precision_at_i = num_relevant_found / i
            score += precision_at_i
    
    return score / len(relevant) if relevant else 0.0


def calculate_r_precision(retrieved, relevant):
    """
    Calculate R-Precision
    Precision at R, where R is the number of relevant documents
    """
    if not relevant:
        return 0.0
    
    R = len(relevant)
    top_R = retrieved[:R]
    relevant_set = set(relevant)
    
    return len(set(top_R) & relevant_set) / R


def calculate_11pt_interpolated_precision(retrieved, relevant):
    """
    Calculate 11-point Interpolated Average Precision
    Standard in TREC evaluation
    """
    if not retrieved or not relevant:
        return 0.0
    
    relevant_set = set(relevant)
    precisions = []
    recalls = []
    num_relevant_found = 0
    
    for i, doc_id in enumerate(retrieved, 1):
        if doc_id in relevant_set:
            num_relevant_found += 1
            precision = num_relevant_found / i
            recall = num_relevant_found / len(relevant)
            precisions.append(precision)
            recalls.append(recall)
    
    if not recalls:
        return 0.0
    
    # 11 recall levels: 0.0, 0.1, 0.2, ..., 1.0
    recall_levels = [i / 10.0 for i in range(11)]
    interpolated_precisions = []
    
    for level in recall_levels:
        # Find max precision for recall >= level
        max_prec = 0.0
        for p, r in zip(precisions, recalls):
            if r >= level:
                max_prec = max(max_prec, p)
        interpolated_precisions.append(max_prec)
    
    return sum(interpolated_precisions) / 11.0


def calculate_dcg(retrieved, relevant, k=None):
    """
    Calculate Discounted Cumulative Gain
    DCG@k = Σ(rel_i / log2(i+1))
    """
    if k:
        retrieved = retrieved[:k]
    
    relevant_set = set(relevant)
    dcg = 0.0
    
    for i, doc_id in enumerate(retrieved, 1):
        if doc_id in relevant_set:
            dcg += 1.0 / math.log2(i + 1)
    
    return dcg


def calculate_ndcg(retrieved, relevant, k=None):
    """
    Calculate Normalized Discounted Cumulative Gain
    NDCG@k = DCG@k / IDCG@k
    """
    import math
    
    if not relevant:
        return 0.0
    
    # Calculate DCG
    dcg = calculate_dcg(retrieved, relevant, k)
    
    # Calculate IDCG (ideal DCG)
    # Ideal ranking: all relevant docs at top
    if k:
        ideal_retrieved = relevant[:k]
    else:
        ideal_retrieved = relevant
    
    idcg = sum(1.0 / math.log2(i + 2) for i in range(len(ideal_retrieved)))
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def calculate_metrics(retrieved, relevant):
    """
    Calculate semua metrik evaluasi
    
    Returns:
        dict: Dictionary berisi semua metrik
    """
    if not retrieved:
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
            'p@5': 0.0,
            'p@10': 0.0,
            'average_precision': 0.0,
            'r_precision': 0.0,
            '11pt_precision': 0.0,
            'ndcg@5': 0.0,
            'ndcg@10': 0.0
        }
    
    relevant_set = set(relevant)
    retrieved_set = set(retrieved)
    tp = len(relevant_set & retrieved_set)
    
    # Basic metrics
    precision = tp / len(retrieved) if retrieved else 0.0
    recall = tp / len(relevant) if relevant else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Precision at k
    p5 = len(set(retrieved[:5]) & relevant_set) / min(5, len(relevant)) if len(retrieved) >= 5 else 0.0
    p10 = len(set(retrieved[:10]) & relevant_set) / min(10, len(relevant)) if len(retrieved) >= 10 else 0.0
    
    # Ranking metrics
    avg_prec = calculate_average_precision(retrieved, relevant)
    r_prec = calculate_r_precision(retrieved, relevant)
    prec_11pt = calculate_11pt_interpolated_precision(retrieved, relevant)
    
    # NDCG metrics
    ndcg5 = calculate_ndcg(retrieved, relevant, k=5)
    ndcg10 = calculate_ndcg(retrieved, relevant, k=10)
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'p@5': p5,
        'p@10': p10,
        'average_precision': avg_prec,
        'r_precision': r_prec,
        '11pt_precision': prec_11pt,
        'ndcg@5': ndcg5,
        'ndcg@10': ndcg10
    }


def evaluate_query(ranker, query, relevant_docs):
    """
    Evaluate single query
    
    Args:
        ranker: DictionaryBM25Ranker instance
        query: query string
        relevant_docs: list of relevant doc_ids
    
    Returns:
        dict: Query results and metrics
    """
    results = ranker.search(query, top_k=100, verbose=False)
    retrieved_ids = [r['doc_id'] for r in results]
    
    metrics = calculate_metrics(retrieved_ids, relevant_docs)
    
    return {
        'query': query,
        'num_retrieved': len(retrieved_ids),
        'num_relevant': len(relevant_docs),
        **metrics,
        'retrieved_docs': retrieved_ids[:10]  # Top 10 untuk inspection
    }


def print_query_result(i, n, query, result):
    """Print hasil evaluasi per query"""
    print(f"[{i:2d}/{n}] {query:35s}", end=" ")
    print(f"P={result['precision']:.3f} R={result['recall']:.3f} ", end="")
    print(f"F1={result['f1']:.3f} AP={result['average_precision']:.3f}")


def main():
    print("="*80)
    print("EVALUASI BM25 dengan BLOCKED DICTIONARY + FRONT CODING")
    print("="*80)
    
    # Load test queries
    qrels = load_test_queries()
    if not qrels:
        return
    
    print(f"\n✓ Loaded {len(qrels)} test queries")
    
    # Check files
    if not BLOCKS_PATH.exists():
        print(f"[ERROR] blocks.json not found: {BLOCKS_PATH}")
        return
    
    if not FRONTCODED_PATH.exists():
        print(f"[ERROR] frontcoded.json not found: {FRONTCODED_PATH}")
        return
    
    if not INDEX_PATH.exists():
        print(f"[ERROR] index.json not found: {INDEX_PATH}")
        return
    
    # Initialize ranker
    print("\nInitializing ranker...")
    ranker = DictionaryBM25Ranker(BLOCKS_PATH, FRONTCODED_PATH, INDEX_PATH)
    
    # Get dictionary stats
    stats = ranker.get_dictionary_stats()
    print(f"\nDictionary Statistics:")
    print(f"  Blocks: {stats['num_blocks']}")
    print(f"  Terms: {stats['num_terms']}")
    print(f"  Compression ratio: {stats['compression_ratio']:.2f}x")
    
    # Evaluate all queries
    print(f"\n{'='*80}")
    print(f"Evaluating {len(qrels)} queries...")
    print("-"*80)
    
    results = []
    for i, (query, relevant_docs) in enumerate(qrels.items(), 1):
        result = evaluate_query(ranker, query, relevant_docs)
        results.append(result)
        print_query_result(i, len(qrels), query, result)
    
    # Calculate summary statistics
    n = len(results)
    summary = {
        'Mean Precision': sum(r['precision'] for r in results) / n,
        'Mean Recall': sum(r['recall'] for r in results) / n,
        'Mean F1': sum(r['f1'] for r in results) / n,
        'MAP': sum(r['average_precision'] for r in results) / n,
        'Mean P@5': sum(r['p@5'] for r in results) / n,
        'Mean P@10': sum(r['p@10'] for r in results) / n,
        'Mean R-Precision': sum(r['r_precision'] for r in results) / n,
        'Mean 11pt Precision': sum(r['11pt_precision'] for r in results) / n,
        'Mean NDCG@5': sum(r['ndcg@5'] for r in results) / n,
        'Mean NDCG@10': sum(r['ndcg@10'] for r in results) / n,
    }
    
    # Save results
    output_data = {
        'summary': summary,
        'per_query_results': results,
        'config': {
            'ranker': 'DictionaryBM25Ranker',
            'dictionary': {
                'blocks': stats['num_blocks'],
                'terms': stats['num_terms'],
                'compression': f"{stats['compression_ratio']:.2f}x"
            },
            'K1': 1.6,
            'B': 0.75,
            'min_coverage': 0.45,
            'min_threshold': 3.0,
            'max_results': '25/40/55 (specific/moderate/generic)'
        },
        'dictionary_stats': stats
    }
    
    EVAL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(EVAL_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*80)
    print("HASIL EVALUASI")
    print("="*80)
    
    print(f"\nMetrik Utama:")
    print(f"  MAP (Mean Average Precision): {summary['MAP']:.4f}")
    print(f"  Mean Precision:               {summary['Mean Precision']:.4f}")
    print(f"  Mean Recall:                  {summary['Mean Recall']:.4f}")
    print(f"  Mean F1:                      {summary['Mean F1']:.4f}")
    
    print(f"\nMetrik Ranking:")
    print(f"  Mean P@5:                     {summary['Mean P@5']:.4f}")
    print(f"  Mean P@10:                    {summary['Mean P@10']:.4f}")
    print(f"  Mean R-Precision:             {summary['Mean R-Precision']:.4f}")
    print(f"  Mean 11pt Precision:          {summary['Mean 11pt Precision']:.4f}")
    
    print(f"\nMetrik NDCG:")
    print(f"  Mean NDCG@5:                  {summary['Mean NDCG@5']:.4f}")
    print(f"  Mean NDCG@10:                 {summary['Mean NDCG@10']:.4f}")
    
    # Identify problematic queries
    problems = [r for r in results if r['f1'] < 0.60]
    if problems:
        print(f"\n{len(problems)} query perlu perhatian (F1 < 0.60):")
        for r in sorted(problems, key=lambda x: x['f1'])[:5]:
            print(f"  • {r['query']:35s} F1={r['f1']:.3f} P={r['precision']:.3f} R={r['recall']:.3f}")
    
    # Best performing queries
    best = sorted(results, key=lambda x: x['f1'], reverse=True)[:5]
    print(f"\nTop 5 queries (by F1):")
    for r in best:
        print(f"  ✓ {r['query']:35s} F1={r['f1']:.3f} P={r['precision']:.3f} R={r['recall']:.3f}")
    
    print(f"\n✓ Hasil disimpan ke: {EVAL_OUTPUT}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()