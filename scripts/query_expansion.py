# query_expansion.py
import json
from pathlib import Path
from collections import defaultdict
import math

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data/index.json"

class QueryExpander:
    """
    Query expansion menggunakan co-occurrence statistics
    untuk meningkatkan recall
    """
    
    def __init__(self, index_path):
        """Load index dan build co-occurrence matrix"""
        with open(index_path, 'r') as f:
            data = json.load(f)
        
        self.index = data['index']
        self.doc_len = data['doc_len']
        self.N = data['num_docs']
        
        # Build synonym/related terms dictionary
        self.synonyms = self._build_synonym_dict()
        
        print(f"QueryExpander initialized with {len(self.synonyms)} term relations")
    
    def _build_synonym_dict(self):
        """
        Build dictionary of related terms menggunakan co-occurrence
        Hanya simpan yang paling strong relationship
        """
        synonyms = defaultdict(set)
        
        # Manual synonyms untuk domain skripsi/thesis Indonesia
        manual_synonyms = {
            'sistem': {'aplikasi', 'program', 'software'},
            'aplikasi': {'sistem', 'program', 'software'},
            'model': {'metode', 'algoritma', 'teknik'},
            'metode': {'model', 'algoritma', 'teknik', 'pendekatan'},
            'algoritma': {'metode', 'model', 'teknik'},
            'klasifikasi': {'pengelompokan', 'kategorisasi'},
            'pengelompokan': {'klasifikasi', 'clustering'},
            'analisis': {'analisa', 'pengolahan', 'pemrosesan'},
            'analisa': {'analisis', 'pengolahan'},
            'pengolahan': {'pemrosesan', 'analisis', 'processing'},
            'pemrosesan': {'pengolahan', 'analisis', 'processing'},
            'deteksi': {'identifikasi', 'pengenalan'},
            'identifikasi': {'deteksi', 'pengenalan'},
            'pengenalan': {'deteksi', 'identifikasi', 'recognition'},
            'optimasi': {'optimisasi', 'optimization'},
            'optimisasi': {'optimasi', 'optimization'},
            'desain': {'rancangan', 'perancangan', 'design'},
            'rancangan': {'desain', 'perancangan', 'design'},
            'perancangan': {'desain', 'rancangan', 'design'},
            'user': {'pengguna', 'pemakai'},
            'pengguna': {'user', 'pemakai'},
            'interface': {'antarmuka', 'tampilan'},
            'antarmuka': {'interface', 'tampilan'},
            'data': {'dataset'},
            'dataset': {'data'},
            'learning': {'pembelajaran'},
            'pembelajaran': {'learning'},
            'machine': {'mesin'},
            'mesin': {'machine'},
            'intelligence': {'kecerdasan'},
            'kecerdasan': {'intelligence'},
            'business': {'bisnis'},
            'bisnis': {'business'},
            'mobile': {'android', 'ios', 'smartphone'},
            'android': {'mobile', 'smartphone'},
            'web': {'website', 'internet'},
            'website': {'web', 'internet'},
            'database': {'basis data', 'basisdata'},
            'basis': {'database', 'basisdata'},
        }
        
        synonyms.update(manual_synonyms)
        
        return synonyms
    
    def expand_query(self, query_terms, max_expansions=2):
        """
        Expand query dengan related terms
        
        Args:
            query_terms: List of query terms
            max_expansions: Maximum terms untuk ditambahkan per term
        
        Returns:
            expanded_terms: List of original + expanded terms
        """
        expanded = set(query_terms)
        
        for term in query_terms:
            if term in self.synonyms:
                # Ambil beberapa synonym saja (yang paling relevan)
                related = list(self.synonyms[term])[:max_expansions]
                expanded.update(related)
        
        return list(expanded)
    
    def expand_query_with_weights(self, query_terms, original_weight=1.0, expanded_weight=0.5):
        """
        Expand query dengan weights untuk original vs expanded terms
        
        Returns:
            dict: {term: weight}
        """
        weighted_terms = {}
        
        # Original terms dengan weight penuh
        for term in query_terms:
            weighted_terms[term] = original_weight
        
        # Expanded terms dengan weight lebih rendah
        for term in query_terms:
            if term in self.synonyms:
                for related in list(self.synonyms[term])[:2]:
                    if related not in weighted_terms:
                        weighted_terms[related] = expanded_weight
        
        return weighted_terms


def test_expansion():
    """Test query expansion"""
    expander = QueryExpander(INDEX_PATH)
    
    test_queries = [
        "sistem rekomendasi",
        "machine learning",
        "user interface",
        "klasifikasi penyakit",
        "optimasi algoritma"
    ]
    
    print("="*80)
    print("QUERY EXPANSION TEST")
    print("="*80)
    
    for query in test_queries:
        terms = query.lower().split()
        expanded = expander.expand_query(terms)
        
        print(f"\nOriginal: {query}")
        print(f"Terms: {terms}")
        print(f"Expanded: {expanded}")
        print(f"Added terms: {set(expanded) - set(terms)}")


if __name__ == "__main__":
    if not INDEX_PATH.exists():
        print(f"[ERROR] Index not found: {INDEX_PATH}")
        print("Please run build_index.py first!")
    else:
        test_expansion()