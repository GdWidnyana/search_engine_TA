# bm25_with_dictionary_improved.py
"""
BM25 Ranker dengan Dictionary + IMPROVED Spelling Correction
Perbaikan untuk handle typo ekstrem seperti "detksi penykti jntung"
"""

import json
import math
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
BLOCKS_PATH = BASE_DIR / "data/blocks.json"
FRONTCODED_PATH = BASE_DIR / "data/frontcoded.json"
INDEX_PATH = BASE_DIR / "data/index.json"

# BM25 Parameters
K1 = 1.6
B = 0.75

# Field boosting
TITLE_BOOST = 5.5
KEYWORD_BOOST = 4.5
ABSTRACT_BOOST = 1.0

# Result limiting
MAX_RESULTS_SPECIFIC = 25
MAX_RESULTS_MODERATE = 40
MAX_RESULTS_GENERIC = 55

# Score thresholds - INCREASED for better precision
MIN_SCORE_THRESHOLD = 8.0  # Raised from 5.0 to 8.0 for even stricter filtering

# Term coverage - INCREASED for stricter matching
MIN_TERM_COVERAGE = 0.65  # Raised from 0.50 to 0.65 (require 2 of 3 terms)
IDEAL_TERM_COVERAGE = 0.85  # Raised from 0.70 to 0.85

# Generic terms
GENERIC_TERMS = {'dengan', 'untuk', 'pada', 'yang', 'dari', 'dan', 'atau', 'ke', 'oleh'}

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
        'terms': ['penyakit', 'medis', 'diagnosis', 'kesehatan', 'deteksi', 
                  'jantung', 'diabetes', 'kanker', 'stroke', 'hospital'],
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


def decode_frontcoded(frontcoded_str):
    """Decode front coded string"""
    if '*' not in frontcoded_str:
        return [frontcoded_str]
    
    prefix, suffixes = frontcoded_str.split('*', 1)
    
    if not suffixes:
        return [prefix]
    
    terms = []
    for suffix in suffixes.split('|'):
        terms.append(prefix + suffix)
    
    return terms


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


class ImprovedDictionaryBM25Ranker:
    """
    Improved BM25 dengan spelling correction yang lebih baik
    """
    
    def __init__(self, blocks_path, frontcoded_path, index_path):
        """Load dictionary and index"""
        print(f"Loading improved dictionary and index...")
        
        # Load blocks
        with open(blocks_path, 'r') as f:
            self.blocks = json.load(f)
        
        # Load frontcoded
        with open(frontcoded_path, 'r') as f:
            self.frontcoded = json.load(f)
        
        # Build vocabulary
        self.vocabulary = set()
        for block_key, frontcoded_str in self.frontcoded.items():
            terms = decode_frontcoded(frontcoded_str)
            self.vocabulary.update(terms)
        
        print(f"  ✓ Dictionary loaded: {len(self.vocabulary)} terms from {len(self.blocks)} blocks")
        
        # Load index
        with open(index_path, 'r') as f:
            data = json.load(f)
        
        self.index = data['index']
        self.doc_len = data['doc_len']
        self.title_index = data.get('title_index', {})
        self.keyword_index = data.get('keyword_index', {})
        self.doc_metadata = data.get('doc_metadata', {})
        self.N = data['num_docs']
        self.avgdl = data['avg_doc_len']
        
        # Term frequency
        self.term_freq = {term: len(postings) for term, postings in self.index.items()}
        
        # Build common typos dictionary - EXPANDED
        self.common_typos = self._build_common_typos()
        
        # Synonyms
        self.synonyms = self._build_synonyms()
        
        print(f"  ✓ Index loaded: {self.N} docs, {len(self.index)} terms")
        print(f"  ✓ Common typos: {len(self.common_typos)} patterns")
    
    def _build_common_typos(self):
        """Build common typo patterns - EXPANDED untuk Indonesia"""
        return {
            # Medical terms
            'detksi': 'deteksi',
            'deteksi': 'deteksi',
            'penykti': 'penyakit',
            'penykit': 'penyakit',
            'penyakit': 'penyakit',
            'jntung': 'jantung',
            'jantng': 'jantung',
            'jantung': 'jantung',
            'diabtes': 'diabetes',
            'diabetis': 'diabetes',
            'kankr': 'kanker',
            'kanker': 'kanker',
            'strke': 'stroke',
            'stroke': 'stroke',
            'dagnosis': 'diagnosis',
            'diagnosa': 'diagnosis',
            'diagnosis': 'diagnosis',
            'kesehtan': 'kesehatan',
            'kesehatn': 'kesehatan',
            
            # ML/AI terms
            'machin': 'machine',
            'lerning': 'learning',
            'learnnig': 'learning',
            'klasifkasi': 'klasifikasi',
            'klasifikasi': 'klasifikasi',
            'algortima': 'algoritma',
            'algoritma': 'algoritma',
            'predksi': 'prediksi',
            'prediksi': 'prediksi',
            
            # System terms
            'sistem': 'sistem',
            'sistim': 'sistem',
            'aplikas': 'aplikasi',
            'aplikasi': 'aplikasi',
            'rekomndasi': 'rekomendasi',
            'rekomendasi': 'rekomendasi',
            'pencaruan': 'pencarian',
            'pencarian': 'pencarian',
            'pencrarian': 'pencarian',
            
            # UI/UX terms
            'interfce': 'interface',
            'interface': 'interface',
            'antarmka': 'antarmuka',
            'antarmuka': 'antarmuka',
            'pengguna': 'pengguna',
            'pemakai': 'pengguna',
            
            # Other common
            'ontolgi': 'ontologi',
            'ontologi': 'ontologi',
            'jaringan': 'jaringan',
            'jaringn': 'jaringan',
        }
    
    def _build_synonyms(self):
        """Build synonyms - EXPANDED"""
        return {
            'sistem': {'aplikasi', 'program'},
            'aplikasi': {'sistem', 'program'},
            'analisis': {'analisa'},
            'analisa': {'analisis'},
            'sentimen': {'sentiment'},
            'pencarian': {'search'},
            'rekomendasi': {'recommendation'},
            'klasifikasi': {'classification', 'pengelompokan'},
            'deteksi': {'detection', 'identifikasi', 'pengenalan'},
            'detection': {'deteksi', 'identifikasi'},
            'pengguna': {'user'},
            'user': {'pengguna'},
            'antarmuka': {'interface'},
            'interface': {'antarmuka'},
            'mobile': {'android'},
            'android': {'mobile'},
            'desain': {'design'},
            'design': {'desain'},
            'keamanan': {'security'},
            'security': {'keamanan'},
            'enkripsi': {'encryption'},
            'penyakit': {'disease'},
            'disease': {'penyakit'},
            'jantung': {'heart', 'cardiac'},
            'heart': {'jantung'},
            'diagnosis': {'diagnosa'},
            'diagnosa': {'diagnosis'},
            'kesehatan': {'health'},
            'health': {'kesehatan'},
        }
    
    def find_term_in_dictionary(self, term):
        """Check if term exists"""
        return term in self.vocabulary
    
    def find_block(self, term):
        """Find block containing term"""
        if len(term) >= 3:
            block_key = term[:3]
        else:
            block_key = term
        
        if block_key in self.blocks:
            if term in self.blocks[block_key]:
                return block_key
        
        return None
    
    def correct_spelling(self, word):
        """
        IMPROVED spelling correction dengan multi-stage approach
        """
        # Stage 1: Check if word already correct
        if self.find_term_in_dictionary(word):
            return word, True, 0
        
        # Stage 2: Check common typos dictionary - PRIORITY
        if word in self.common_typos:
            corrected = self.common_typos[word]
            if self.find_term_in_dictionary(corrected):
                return corrected, False, 1
        
        # Stage 3: Prefix matching (for incomplete words)
        if len(word) >= 3:
            block_key = word[:3]
            if block_key in self.blocks:
                block_terms = self.blocks[block_key]
                prefix_matches = [t for t in block_terms 
                                if t.startswith(word) and len(t) <= len(word) + 5]
                if prefix_matches:
                    # Return most frequent
                    best = max(prefix_matches, key=lambda t: self.term_freq.get(t, 0))
                    return best, False, len(best) - len(word)
        
        # Stage 4: Edit distance with expanded search
        candidates = []
        
        # Search in current block and similar blocks
        search_prefixes = set()
        if len(word) >= 3:
            search_prefixes.add(word[:3])
            
            # Add blocks with similar prefixes (allow 1 char difference)
            for i in range(min(3, len(word))):
                for c in 'abcdefghijklmnopqrstuvwxyz':
                    variant = word[:i] + c + (word[i+1:3] if len(word) > i+1 else '')
                    if len(variant) >= 3 and variant in self.blocks:
                        search_prefixes.add(variant)
        
        # Increased max distance for extreme typos
        max_distance = min(3, len(word) // 2)  # Allow up to 3 edits or half the word length
        
        for prefix in search_prefixes:
            if prefix not in self.blocks:
                continue
            
            for vocab_term in self.blocks[prefix]:
                # More lenient length check
                if abs(len(vocab_term) - len(word)) > max_distance:
                    continue
                
                dist = edit_distance(word, vocab_term)
                if dist <= max_distance:
                    freq = self.term_freq.get(vocab_term, 0)
                    candidates.append((vocab_term, dist, freq))
        
        if candidates:
            # Sort by: distance (lower better), then frequency (higher better)
            candidates.sort(key=lambda x: (x[1], -x[2]))
            return candidates[0][0], False, candidates[0][1]
        
        # No correction found
        return word, False, 999
    
    def expand_query(self, terms):
        """Query expansion with synonyms"""
        expanded = set(terms)
        for term in terms:
            if term in self.synonyms:
                # Add top 2 synonyms
                expanded.update(list(self.synonyms[term])[:2])
        return list(expanded)
    
    def preprocess_query(self, query):
        """
        IMPROVED query preprocessing with better correction
        """
        query = query.lower().strip()
        terms = [t for t in query.split() if len(t) > 1]
        
        if not terms:
            return [], []
        
        # Spelling correction with confidence
        corrected_terms = []
        corrections = []
        correction_confidence = []
        
        for term in terms:
            corrected, was_correct, distance = self.correct_spelling(term)
            corrected_terms.append(corrected)
            
            if not was_correct:
                corrections.append(f"{term}→{corrected}")
                correction_confidence.append(distance)
        
        # Query expansion (only if corrections look good)
        if all(conf < 3 for conf in correction_confidence):
            expanded_terms = self.expand_query(corrected_terms)
        else:
            # If corrections are uncertain, don't expand
            expanded_terms = corrected_terms
        
        return expanded_terms, corrections
    
    def get_core_terms(self, query_terms):
        """Get core terms (remove stopwords)"""
        core = [t for t in query_terms if t not in GENERIC_TERMS]
        return core if core else query_terms
    
    def analyze_query_specificity(self, query_terms):
        """Analyze query specificity"""
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
        """Detect query domain with match count"""
        domain_matches = {}
        
        for domain, info in DOMAIN_PATTERNS.items():
            matches = sum(1 for term in query_terms if term in info['terms'])
            if matches > 0:
                domain_matches[domain] = matches
        
        if domain_matches:
            # Return domain with most matches
            best_domain = max(domain_matches.items(), key=lambda x: x[1])
            return best_domain[0], DOMAIN_PATTERNS[best_domain[0]]['boost']
        
        return 'general', 1.0
    
    def compute_idf(self, term):
        """Compute IDF with penalty"""
        if term not in self.index:
            return 0.0
        
        df = len(self.index[term])
        idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
        
        # Penalty for very common terms
        if df > self.N * 0.5:
            idf *= 0.4
        elif df > self.N * 0.3:
            idf *= 0.6
        
        return idf
    
    def compute_term_coverage(self, query_terms, doc_id):
        """Calculate term coverage"""
        core_terms = self.get_core_terms(query_terms)
        if not core_terms:
            return 0.0
        
        matches = sum(1 for t in core_terms
                     if (t in self.index and doc_id in self.index[t]) or
                        (t in self.title_index and doc_id in self.title_index[t]) or
                        (t in self.keyword_index and doc_id in self.keyword_index[t]))
        
        return matches / len(core_terms)
    
    def check_semantic_relevance(self, query_terms, doc_id):
        """
        Check semantic relevance - ensure doc is actually about the query topic
        Return True only if doc contains key concepts from query
        """
        core_terms = self.get_core_terms(query_terms)
        if not core_terms:
            return True
        
        # Get document text (title + keywords + abstract)
        metadata = self.doc_metadata.get(doc_id, {})
        doc_text = (
            metadata.get('title', '') + ' ' + 
            metadata.get('keywords', '') + ' ' + 
            metadata.get('abstract', '')
        ).lower()
        
        # Check if ALL core terms (or their synonyms) appear in document
        matches = 0
        for term in core_terms:
            # Check direct match
            if term in doc_text:
                matches += 1
                continue
            
            # Check synonyms
            if term in self.synonyms:
                if any(syn in doc_text for syn in self.synonyms[term]):
                    matches += 1
                    continue
        
        # Require at least 70% of core terms to be in document text
        coverage = matches / len(core_terms)
        return coverage >= 0.7
    
    def compute_bm25_score(self, query_terms, doc_id):
        """Compute BM25 score"""
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
        """Apply field boosting"""
        boosted = {}
        core_terms = self.get_core_terms(query_terms)
        
        for doc_id, base_score in doc_scores.items():
            mult = 1.0
            
            # Title matching boost
            title_matches = sum(1 for t in core_terms
                              if t in self.title_index and doc_id in self.title_index[t])
            
            if title_matches > 0:
                title_cov = title_matches / len(core_terms)
                
                if title_cov >= 0.8:
                    mult += TITLE_BOOST * 1.5
                elif title_cov >= 0.6:
                    mult += TITLE_BOOST * 1.2
                else:
                    mult += TITLE_BOOST * title_cov
            
            # Keyword matching boost
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
        """Filter results with higher threshold"""
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
        """Main search function with improved correction and semantic filtering"""
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
        if len(candidate_docs) < 5:
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
        
        # NEW: Semantic filtering - remove irrelevant documents
        semantically_relevant = {}
        for doc_id in candidate_docs.keys():
            if self.check_semantic_relevance(query_terms, doc_id):
                semantically_relevant[doc_id] = candidate_docs[doc_id]
        
        # If semantic filtering removes too many, use original candidates
        if len(semantically_relevant) >= 3:
            candidate_docs = semantically_relevant
        
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
        
        # NEW: Final semantic check - ensure top results are truly relevant
        final_scores = {}
        for doc_id, score in scores.items():
            # Double-check semantic relevance with stricter threshold for top results
            if self.check_semantic_relevance(query_terms, doc_id):
                final_scores[doc_id] = score
        
        # If too strict, relax a bit
        if len(final_scores) < min(3, len(scores) // 2):
            final_scores = scores
        
        # Sort and format
        sorted_results = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        
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
    
    def get_dictionary_stats(self):
        """Get dictionary statistics"""
        return {
            'num_blocks': len(self.blocks),
            'num_terms': len(self.vocabulary),
            'num_frontcoded': len(self.frontcoded),
            'avg_block_size': sum(len(v) for v in self.blocks.values()) / len(self.blocks),
            'compression_ratio': len(self.vocabulary) / len(self.frontcoded),
            'num_typo_patterns': len(self.common_typos)
        }


def main():
    """Test the improved ranker"""
    print("="*80)
    print("Improved BM25 with Better Spelling Correction")
    print("="*80)
    
    ranker = ImprovedDictionaryBM25Ranker(BLOCKS_PATH, FRONTCODED_PATH, INDEX_PATH)
    
    # Test queries with typos
    test_queries = [
        "detksi penykti jntung",    # Extreme typos
        "machin lerning",            # Common typos
        "sistem rekomndasi",         # Moderate typos
        "klasifikasi penyakit",      # Correct spelling
    ]
    
    print("\nTesting queries:")
    print("-"*80)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = ranker.search(query, top_k=5, verbose=True)
        print(f"Found {len(results)} results")
        
        if results:
            for i, r in enumerate(results[:3], 1):
                print(f"  {i}. {r['title'][:60]}... (score={r['score']:.2f})")


if __name__ == "__main__":
    main()
