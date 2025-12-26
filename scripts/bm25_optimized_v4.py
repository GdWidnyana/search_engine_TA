#bm25_optimized_v4.py
import json
import math
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data/processed/index.json"

# ===== OPTIMIZED BALANCED PARAMETERS =====
K1 = 1.6
B = 0.75

# Field boosting - STRONG for precision
TITLE_BOOST = 5.5
KEYWORD_BOOST = 4.5
ABSTRACT_BOOST = 1.0

# Result limiting - BALANCED
MAX_RESULTS_SPECIFIC = 25
MAX_RESULTS_MODERATE = 40
MAX_RESULTS_GENERIC = 55

# Score thresholds - BALANCED (not too high, not too low)
MIN_SCORE_THRESHOLD = 3.0  # Raised from 2.0 for better precision

# Term coverage - BALANCED
MIN_TERM_COVERAGE = 0.45  # Between 0.4 and 0.6
IDEAL_TERM_COVERAGE = 0.70

# Generic terms - MINIMAL
GENERIC_TERMS = {'dengan', 'untuk', 'pada', 'yang', 'dari'}

# Domain patterns
DOMAIN_PATTERNS = {
    'security': {
        'terms': ['keamanan', 'enkripsi', 'pengamanan', 'kriptografi', 'security', 
                  'steganografi', 'watermark', 'cipher', 'citra', 'digital'],
        'boost': 1.9
    },
    'ml_ai': {
        'terms': ['machine', 'learning', 'neural', 'deep', 'klasifikasi', 
                  'prediksi', 'algoritma', 'cnn', 'lstm', 'svm', 'naive', 'bayes'],
        'boost': 1.8
    },
    'ui_ux': {
        'terms': ['user', 'interface', 'antarmuka', 'desain', 'ui', 'ux', 
                  'interaksi', 'usability', 'centered', 'experience'],
        'boost': 1.7
    },
    'nlp': {
        'terms': ['sentimen', 'teks', 'peringkasan', 'topik', 'chatbot', 
                  'nlp', 'text', 'mining', 'sentiment', 'analisis'],
        'boost': 1.8
    },
    'recommender': {
        'terms': ['rekomendasi', 'recommendation', 'collaborative', 'filtering'],
        'boost': 1.8
    },
    'medical': {
        'terms': ['penyakit', 'medis', 'diagnosis', 'kesehatan', 'deteksi'],
        'boost': 1.7
    },
    'iot': {
        'terms': ['iot', 'sensor', 'arduino', 'monitoring', 'embedded'],
        'boost': 1.6
    },
    'business': {
        'terms': ['business', 'intelligence', 'bi', 'dashboard', 'analitik'],
        'boost': 1.7
    },
    'mobile': {
        'terms': ['mobile', 'android', 'smartphone', 'aplikasi'],
        'boost': 1.6
    }
}


def edit_distance(s1, s2):
    """Levenshtein distance"""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


class OptimizedBM25Ranker:
    """
    Optimized BM25 with precision-recall balance
    """
    
    def __init__(self, index_path):
        with open(index_path, 'r') as f:
            data = json.load(f)
        
        self.index = data['index']
        self.doc_len = data['doc_len']
        self.title_index = data.get('title_index', {})
        self.keyword_index = data.get('keyword_index', {})
        self.doc_metadata = data.get('doc_metadata', {})
        self.N = data['num_docs']
        self.avgdl = data['avg_doc_len']
        
        self.vocabulary = set(self.index.keys())
        self.term_freq = {term: len(postings) for term, postings in self.index.items()}
        self.synonyms = self._build_synonyms()
        
        print(f"OptimizedBM25 v4 loaded: {self.N} docs, {len(self.vocabulary)} terms")
    
    def _build_synonyms(self):
        """Build synonyms"""
        return {
            'sistem': {'aplikasi'},
            'aplikasi': {'sistem'},
            'analisis': {'analisa'},
            'sentimen': {'sentiment'},
            'pencarian': {'search'},
            'rekomendasi': {'recommendation'},
            'klasifikasi': {'classification'},
            'deteksi': {'detection'},
            'pengguna': {'user'},
            'antarmuka': {'interface'},
            'mobile': {'android'},
            'desain': {'design'},
            'keamanan': {'security'},
            'enkripsi': {'encryption'},
            'penyakit': {'disease'},
        }
    
    def correct_spelling(self, word):
        """Spelling correction"""
        if word in self.vocabulary:
            return word, True
        
        # Prefix matching
        prefix_matches = [t for t in self.vocabulary 
                         if t.startswith(word) and len(t) <= len(word) + 5]
        if prefix_matches:
            return max(prefix_matches, key=lambda t: self.term_freq.get(t, 0)), False
        
        # Edit distance
        candidates = []
        for vocab_term in self.vocabulary:
            if abs(len(vocab_term) - len(word)) > 2:
                continue
            dist = edit_distance(word, vocab_term)
            if dist <= 2:
                candidates.append((vocab_term, dist, self.term_freq.get(vocab_term, 0)))
        
        if candidates:
            candidates.sort(key=lambda x: (x[1], -x[2]))
            return candidates[0][0], False
        
        return word, False
    
    def expand_query(self, terms):
        """Query expansion"""
        expanded = set(terms)
        for term in terms:
            if term in self.synonyms:
                expanded.update(list(self.synonyms[term])[:1])
        return list(expanded)
    
    def preprocess_query(self, query):
        """Preprocess query"""
        query = query.lower().strip()
        terms = [t for t in query.split() if len(t) > 1]
        
        if not terms:
            return [], []
        
        # Spelling correction
        corrected_terms = []
        corrections = []
        
        for term in terms:
            corrected, was_correct = self.correct_spelling(term)
            corrected_terms.append(corrected)
            if not was_correct:
                corrections.append(f"{term}→{corrected}")
        
        # Expansion
        expanded_terms = self.expand_query(corrected_terms)
        
        return expanded_terms, corrections
    
    def get_core_terms(self, query_terms):
        """Get core terms"""
        core = [t for t in query_terms if t not in GENERIC_TERMS]
        return core if core else query_terms
    
    def analyze_query_specificity(self, query_terms):
        """Analyze specificity"""
        core_terms = self.get_core_terms(query_terms)
        
        domain_match = any(
            any(term in info['terms'] for term in core_terms)
            for info in DOMAIN_PATTERNS.values()
        )
        
        if len(core_terms) >= 3 or (len(core_terms) >= 2 and domain_match):
            return 'specific'
        elif len(core_terms) >= 2:
            return 'moderate'
        else:
            return 'generic'
    
    def detect_query_domain(self, query_terms):
        """Detect domain"""
        for domain, info in DOMAIN_PATTERNS.items():
            if any(term in info['terms'] for term in query_terms):
                return domain, info['boost']
        return 'general', 1.0
    
    def compute_idf(self, term):
        """IDF with penalty"""
        if term not in self.index:
            return 0.0
        
        df = len(self.index[term])
        idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
        
        # Penalty for common terms
        if df > self.N * 0.5:
            idf *= 0.4
        elif df > self.N * 0.3:
            idf *= 0.6
        
        return idf
    
    def compute_term_coverage(self, query_terms, doc_id):
        """Calculate coverage"""
        core_terms = self.get_core_terms(query_terms)
        if not core_terms:
            return 0.0
        
        matches = sum(1 for t in core_terms
                     if (t in self.index and doc_id in self.index[t]) or
                        (t in self.title_index and doc_id in self.title_index[t]) or
                        (t in self.keyword_index and doc_id in self.keyword_index[t]))
        
        return matches / len(core_terms)
    
    def compute_bm25_score(self, query_terms, doc_id):
        """BM25 scoring"""
        score = 0.0
        dl = self.doc_len.get(doc_id, 0)
        
        if dl == 0:
            return 0.0
        
        for term in query_terms:
            if term not in self.index or doc_id not in self.index[term]:
                continue
            
            tf = self.index[term][doc_id]
            idf = self.compute_idf(term)
            
            numerator = tf * (K1 + 1)
            denominator = tf + K1 * (1 - B + B * (dl / self.avgdl))
            
            score += idf * (numerator / denominator)
        
        return score
    
    def apply_boosting(self, query_terms, doc_scores, domain_boost):
        """Apply semantic boosting"""
        boosted = {}
        core_terms = self.get_core_terms(query_terms)
        
        for doc_id, base_score in doc_scores.items():
            mult = 1.0
            
            # Title matching - STRONG boost for precision
            title_matches = sum(1 for t in core_terms
                              if t in self.title_index and doc_id in self.title_index[t])
            
            if title_matches > 0:
                title_cov = title_matches / len(core_terms)
                
                # Progressive boost
                if title_cov >= 0.8:
                    mult += TITLE_BOOST * 1.5
                elif title_cov >= 0.6:
                    mult += TITLE_BOOST * 1.2
                else:
                    mult += TITLE_BOOST * title_cov
            
            # Keyword matching
            kw_matches = sum(1 for t in core_terms
                           if t in self.keyword_index and doc_id in self.keyword_index[t])
            
            if kw_matches > 0:
                kw_cov = kw_matches / len(core_terms)
                mult += KEYWORD_BOOST * kw_cov
            
            # Perfect match bonus
            if title_matches == len(core_terms) and len(core_terms) >= 2:
                mult *= 2.0
            
            # High coverage bonus
            coverage = self.compute_term_coverage(query_terms, doc_id)
            if coverage >= IDEAL_TERM_COVERAGE:
                mult *= 1.4
            elif coverage >= 0.6:
                mult *= 1.2
            
            # Domain boost
            mult *= domain_boost
            
            boosted[doc_id] = base_score * mult
        
        return boosted
    
    def filter_results(self, scores, specificity):
        """Smart filtering for precision"""
        if not scores:
            return {}
        
        score_values = sorted(scores.values(), reverse=True)
        
        # Limits
        if specificity == 'specific':
            max_results = MAX_RESULTS_SPECIFIC
            percentile = 0.25
        elif specificity == 'moderate':
            max_results = MAX_RESULTS_MODERATE
            percentile = 0.35
        else:
            max_results = MAX_RESULTS_GENERIC
            percentile = 0.45
        
        # Adaptive threshold
        if len(score_values) > 20:
            cutoff_idx = max(8, int(len(score_values) * percentile))
            adaptive_threshold = score_values[cutoff_idx]
        else:
            adaptive_threshold = MIN_SCORE_THRESHOLD
        
        threshold = max(adaptive_threshold, MIN_SCORE_THRESHOLD)
        
        # Apply threshold
        filtered = {doc_id: score for doc_id, score in scores.items()
                   if score >= threshold}
        
        # Limit results
        if len(filtered) > max_results:
            sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
            filtered = dict(sorted_items[:max_results])
        
        return filtered
    
    def search(self, query, top_k=10, verbose=False):
        """Main search"""
        # Preprocess
        query_terms, corrections = self.preprocess_query(query)
        
        if not query_terms:
            return []
        
        if corrections and verbose:
            print(f"✓ Corrected: {', '.join(corrections)}")
        
        # Analyze
        specificity = self.analyze_query_specificity(query_terms)
        domain, domain_boost = self.detect_query_domain(query_terms)
        
        # Collect candidates
        candidate_docs = defaultdict(int)
        
        for term in query_terms:
            if term in self.index:
                for doc_id in self.index[term].keys():
                    candidate_docs[doc_id] += 1
        
        # Coverage filter
        core_terms = self.get_core_terms(query_terms)
        min_matches = max(1, int(len(core_terms) * MIN_TERM_COVERAGE))
        
        candidate_docs = {doc_id: count for doc_id, count in candidate_docs.items()
                         if count >= min_matches}
        
        # Fallback
        if len(candidate_docs) < 8:
            min_matches = max(1, int(len(core_terms) * 0.35))
            candidate_docs = defaultdict(int)
            for term in query_terms:
                if term in self.index:
                    for doc_id in self.index[term].keys():
                        candidate_docs[doc_id] += 1
            candidate_docs = {doc_id: count for doc_id, count in candidate_docs.items()
                             if count >= min_matches}
        
        if not candidate_docs:
            return []
        
        # Score
        scores = {}
        for doc_id in candidate_docs.keys():
            score = self.compute_bm25_score(query_terms, doc_id)
            if score > 0:
                scores[doc_id] = score
        
        # Boost
        scores = self.apply_boosting(query_terms, scores, domain_boost)
        
        # Filter
        scores = self.filter_results(scores, specificity)
        
        # Return
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in sorted_results[:top_k]:
            metadata = self.doc_metadata.get(doc_id, {})
            results.append({
                'doc_id': doc_id,
                'score': score,
                'title': metadata.get('title', ''),
                'keywords': metadata.get('keywords', ''),
                'abstract': metadata.get('abstract', '')[:200] + '...',
                'authors': metadata.get('authors', ''),
                'domain': domain,
                'specificity': specificity
            })
        
        return results


def main():
    """Interactive search"""
    if not INDEX_PATH.exists():
        print(f"[ERROR] Index not found: {INDEX_PATH}")
        return
    
    print("="*80)
    print("OPTIMIZED BM25 v4 - PRECISION-RECALL BALANCED")
    print("="*80)
    
    ranker = OptimizedBM25Ranker(INDEX_PATH)
    
    while True:
        print("\n" + "-"*80)
        query = input("Enter query (or 'quit'): ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        results = ranker.search(query, top_k=10, verbose=True)
        
        print(f"\nFound {len(results)} results")
        
        if not results:
            print("No results found.")
            continue
        
        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['doc_id']} (Score: {r['score']:.2f})")
            print(f"   {r['title'][:80]}")


if __name__ == "__main__":
    main()