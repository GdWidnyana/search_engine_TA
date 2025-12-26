#evaluate_optimized_v4.py
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bm25_optimized_v4 import OptimizedBM25Ranker

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data/index.json"
TEST_QUERIES_PATH = Path(__file__).resolve().parent / "test_queries.json"
EVAL_OUTPUT = BASE_DIR / "data/evaluation_optimized_v4.json"


def load_test_queries():
    """Load test queries"""
    if not TEST_QUERIES_PATH.exists():
        print(f"[ERROR] test_queries.json tidak ditemukan: {TEST_QUERIES_PATH}")
        return None
    
    with open(TEST_QUERIES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_average_precision(retrieved, relevant):
    """Calculate Average Precision untuk satu query"""
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
    """Calculate R-Precision"""
    if not relevant:
        return 0.0
    
    R = len(relevant)
    top_R = retrieved[:R]
    relevant_set = set(relevant)
    
    return len(set(top_R) & relevant_set) / R


def calculate_11pt_interpolated_precision(retrieved, relevant):
    """Calculate 11-point Interpolated Average Precision"""
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
    
    # 11 recall points
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


def calculate_metrics(retrieved, relevant):
    """Calculate semua metrik"""
    if not retrieved:
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1': 0.0,
            'p@5': 0.0,
            'p@10': 0.0,
            'average_precision': 0.0,
            'r_precision': 0.0,
            '11pt_precision': 0.0
        }
    
    relevant_set = set(relevant)
    retrieved_set = set(retrieved)
    tp = len(relevant_set & retrieved_set)
    
    # Metrik dasar
    precision = tp / len(retrieved) if retrieved else 0.0
    recall = tp / len(relevant) if relevant else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # P@k
    p5 = len(set(retrieved[:5]) & relevant_set) / min(5, len(relevant)) if len(retrieved) >= 5 else 0.0
    p10 = len(set(retrieved[:10]) & relevant_set) / min(10, len(relevant)) if len(retrieved) >= 10 else 0.0
    
    # Metrik ranking
    avg_prec = calculate_average_precision(retrieved, relevant)
    r_prec = calculate_r_precision(retrieved, relevant)
    prec_11pt = calculate_11pt_interpolated_precision(retrieved, relevant)
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'p@5': p5,
        'p@10': p10,
        'average_precision': avg_prec,
        'r_precision': r_prec,
        '11pt_precision': prec_11pt
    }


def evaluate_query(ranker, query, relevant_docs):
    """Evaluate single query"""
    results = ranker.search(query, top_k=100, verbose=False)
    retrieved_ids = [r['doc_id'] for r in results]
    
    metrics = calculate_metrics(retrieved_ids, relevant_docs)
    
    return {
        'query': query,
        'num_retrieved': len(retrieved_ids),
        'num_relevant': len(relevant_docs),
        **metrics,
        'retrieved_docs': retrieved_ids[:10]
    }


def main():
    print("="*80)
    print("EVALUASI BM25 OPTIMIZED v4")
    print("="*80)
    
    # Load
    qrels = load_test_queries()
    if not qrels:
        return
    
    print(f"\n✓ Memuat {len(qrels)} test queries")
    
    # Initialize
    ranker = OptimizedBM25Ranker(INDEX_PATH)
    
    # Evaluate
    print(f"\nMengevaluasi {len(qrels)} queries...")
    print("-"*80)
    
    results = []
    for i, (query, relevant_docs) in enumerate(qrels.items(), 1):
        print(f"[{i:2d}/{len(qrels)}] {query:30s} ", end="")
        
        result = evaluate_query(ranker, query, relevant_docs)
        results.append(result)
        
        print(f"P={result['precision']:.2f} R={result['recall']:.2f} F1={result['f1']:.2f}")
    
    # Summary
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
    }
    
    # Save
    with open(EVAL_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary,
            'per_query_results': results,
            'config': {
                'K1': 1.6,
                'B': 0.75,
                'min_coverage': 0.45,
                'min_threshold': 3.0,
                'max_results': '25/40/55'
            }
        }, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("HASIL EVALUASI")
    print("="*80)
    
    # Metrik Utama
    print(f"\nMetrik Utama:")
    print(f"  MAP (Mean Average Precision): {summary['MAP']:.4f}")
    print(f"  Mean Precision:               {summary['Mean Precision']:.4f}")
    print(f"  Mean Recall:                  {summary['Mean Recall']:.4f}")
    print(f"  Mean F1:                      {summary['Mean F1']:.4f}")
    
    # Metrik Ranking
    print(f"\nMetrik Ranking:")
    print(f"  Mean P@5:                     {summary['Mean P@5']:.4f}")
    print(f"  Mean P@10:                    {summary['Mean P@10']:.4f}")
    print(f"  Mean R-Precision:             {summary['Mean R-Precision']:.4f}")
    print(f"  Mean 11pt Precision:          {summary['Mean 11pt Precision']:.4f}")
    
    # Query bermasalah
    problems = [r for r in results if r['f1'] < 0.60]
    if problems:
        print(f"\n{len(problems)} query perlu perhatian (F1 < 0.60):")
        for r in sorted(problems, key=lambda x: x['f1'])[:5]:
            print(f"  • {r['query']:30s} F1={r['f1']:.2f}")
    
    print(f"\n✓ Hasil disimpan ke: {EVAL_OUTPUT}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()