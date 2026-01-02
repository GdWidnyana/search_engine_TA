"""
Enhanced BM25 Ranker
====================
BM25 ranking dengan:
- Ultra-Smart Spell Correction (dari ultra_smart_spelling.py)
- Multi-field search (title, keyword, abstract)
- Domain-specific boosting
- Term coverage filtering
- Wildcard support
- Query expansion
- Adaptive result limiting
"""

import json
import math
import re
from pathlib import Path
from collections import defaultdict

# Import spell corrector
from scripts.spelling import UltraSmartSpellCorrector

BASE_DIR = Path(__file__).resolve().parent
BLOCKS_PATH = BASE_DIR / "streamlit_ir/data/blocks.json"
FRONTCODED_PATH = BASE_DIR / "streamlit_ir/data/frontcoded.json"
INDEX_PATH = BASE_DIR / "streamlit_ir/data/index.json"

# BM25 Parameters (TUNED)
K1 = 1.8
B = 0.70

# Field boosting
TITLE_BOOST = 8.0
KEYWORD_BOOST = 6.0
ABSTRACT_BOOST = 1.0

# Result limiting
MAX_RESULTS_SPECIFIC = 20
MAX_RESULTS_MODERATE = 35
MAX_RESULTS_GENERIC = 50

# Score thresholds
MIN_SCORE_THRESHOLD = 5.0

# Term coverage
MIN_TERM_COVERAGE = 0.50
IDEAL_TERM_COVERAGE = 0.75

# Generic terms
GENERIC_TERMS = {
    'dengan', 'untuk', 'pada', 'yang', 'dari', 'dan', 'atau', 'ke', 'oleh', 'di', 
    'adalah', 'ini', 'itu', 'akan', 'telah', 'dapat', 'harus', 'bisa', 'sudah'
}

# Domain patterns
DOMAIN_PATTERNS = {
    'security': {
        'terms': ['keamanan', 'enkripsi', 'pengamanan', 'kriptografi', 'security', 
                  'steganografi', 'watermark', 'cipher', 'citra', 'digital', 'aes', 'rsa'],
        'boost': 2.2
    },
    'ml_ai': {
        'terms': ['machine', 'learning', 'neural', 'deep', 'klasifikasi', 
                  'prediksi', 'algoritma', 'cnn', 'lstm', 'svm', 'naive', 'bayes',
                  'model', 'training', 'akurasi', 'dataset'],
        'boost': 2.1
    },
    'ui_ux': {
        'terms': ['user', 'interface', 'antarmuka', 'desain', 'ui', 'ux', 
                  'interaksi', 'usability', 'centered', 'experience', 'aplikasi'],
        'boost': 2.0
    },
    'nlp': {
        'terms': ['sentimen', 'teks', 'peringkasan', 'topik', 'chatbot', 
                  'nlp', 'text', 'mining', 'sentiment', 'analisis', 'pemodelan'],
        'boost': 2.1
    },
    'recommender': {
        'terms': ['rekomendasi', 'recommendation', 'collaborative', 'filtering',
                  'sistem', 'content', 'based'],
        'boost': 2.0
    },
    'medical': {
        'terms': ['penyakit', 'medis', 'diagnosis', 'kesehatan', 'deteksi', 
                  'jantung', 'diabetes', 'kanker', 'stroke', 'hospital', 'pasien'],
        'boost': 2.0
    },
    'iot': {
        'terms': ['iot', 'sensor', 'arduino', 'monitoring', 'embedded', 'smart'],
        'boost': 1.9
    },
    'business': {
        'terms': ['business', 'intelligence', 'bi', 'dashboard', 'analitik', 
                  'data', 'warehouse', 'olap'],
        'boost': 2.0
    },
    'mobile': {
        'terms': ['mobile', 'android', 'smartphone', 'aplikasi', 'ios', 'app'],
        'boost': 1.9
    },
    'optimization': {
        'terms': ['optimasi', 'optimization', 'algoritma', 'genetic', 'particle',
                  'swarm', 'ant', 'colony'],
        'boost': 1.9
    }
}


def decode_frontcoded(frontcoded_str):
    """
    Decode front coded string
    
    Example: "test*|ing|ed" → ["test", "testing", "tested"]
    """
    if '*' not in frontcoded_str:
        return [frontcoded_str]
    
    prefix, suffixes = frontcoded_str.split('*', 1)
    
    if not suffixes:
        return [prefix]
    
    terms = []
    for suffix in suffixes.split('|'):
        terms.append(prefix + suffix)
    
    return terms


def wildcard_to_regex(pattern):
    """
    Convert wildcard pattern to regex
    
    * = any characters (0 or more)
    ? = single character
    
    Example: "sentim*" → "^sentim.*$"
    """
    pattern = re.escape(pattern)
    pattern = pattern.replace(r'\*', '.*')
    pattern = pattern.replace(r'\?', '.')
    return f'^{pattern}$'


class EnhancedBM25Ranker:
    """
    Enhanced BM25 Ranker dengan Ultra-Smart Spell Correction
    
    Features:
    1. BM25 ranking (Okapi BM25)
    2. Multi-field search (title, keyword, abstract) dengan boosting
    3. Domain-specific boosting
    4. Term coverage filtering
    5. Ultra-smart spell correction
    6. Word segmentation
    7. Wildcard support
    8. Query expansion (synonyms)
    9. Adaptive result limiting
    """
    
    def __init__(self, blocks_path, frontcoded_path, index_path):
        """
        Initialize BM25 ranker
        
        Args:
            blocks_path: Path to blocks.json
            frontcoded_path: Path to frontcoded.json
            index_path: Path to index.json
        """
        print(f"\n{'='*80}")
        print(f"INITIALIZING ENHANCED BM25 RANKER")
        print(f"{'='*80}")
        
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
        
        print(f"✓ Dictionary: {len(self.vocabulary)} terms from {len(self.blocks)} blocks")
        
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
        
        # Build term frequency
        self.term_freq = {}
        for term, postings in self.index.items():
            freq = len(postings) if isinstance(postings, dict) else len(set(postings))
            self.term_freq[term] = freq
        
        # Add frequency from title and keyword
        for term, postings in self.title_index.items():
            freq = len(postings) if isinstance(postings, dict) else len(set(postings))
            self.term_freq[term] = self.term_freq.get(term, 0) + freq * 2
        
        for term, postings in self.keyword_index.items():
            freq = len(postings) if isinstance(postings, dict) else len(set(postings))
            self.term_freq[term] = self.term_freq.get(term, 0) + freq * 3
        
        print(f"✓ Index: {self.N} docs, {len(self.index)} terms")
        
        # Initialize Ultra-Smart Spell Corrector
        self.spell_corrector = UltraSmartSpellCorrector(
            vocabulary=self.vocabulary,
            term_freq=self.term_freq
        )
        
        # Synonyms
        self.synonyms = self._build_synonyms()
        
        print(f"✓ Configuration: K1={K1}, B={B}")
        print(f"✓ Boosting: Title={TITLE_BOOST}×, Keyword={KEYWORD_BOOST}×, Abstract={ABSTRACT_BOOST}×")
        print(f"✓ Features: Ultra-Smart Spell Correction + Word Segmentation + Wildcards")
        print(f"{'='*80}\n")
    
    def _build_synonyms(self):
        """Build synonym dictionary untuk query expansion"""
        return {
            'ml': 'machine learning',
            'ai': 'artificial intelligence',
            'dl': 'deep learning',
            'nn': 'neural network',
            'ui': 'user interface',
            'ux': 'user experience',
            'bi': 'business intelligence',
            'nlp': 'natural language processing',
            'cv': 'computer vision',
            'ir': 'information retrieval'
        }
    
    def _tokenize(self, text):
        """Simple tokenization dengan cleaning"""
        if not text:
            return []
        
        text = text.lower()
        tokens = text.split()
        return [t for t in tokens if len(t) > 1]
    
    def _is_wildcard_query(self, term):
        """Check if term contains wildcard characters (* or ?)"""
        return '*' in term or '?' in term
    
    def _expand_wildcard(self, term):
        """
        Expand wildcard pattern
        
        Example: "sentim*" → ["sentimen", "sentiment", ...]
        """
        regex = re.compile(wildcard_to_regex(term))
        expanded = [t for t in self.vocabulary if regex.match(t)]
        return expanded
    
    def _expand_query(self, query_terms):
        """Expand query dengan synonyms"""
        expanded = []
        
        for term in query_terms:
            expanded.append(term)
            
            # Add synonyms
            if term in self.synonyms:
                synonym_terms = self.synonyms[term].split()
                expanded.extend(synonym_terms)
        
        return expanded
    
    def _get_doc_ids_from_postings(self, postings):
        """Extract document IDs dari posting list"""
        if isinstance(postings, dict):
            return list(postings.keys())
        elif isinstance(postings, list):
            return list(dict.fromkeys(postings))
        else:
            return []
    
    def _compute_idf(self, term):
        """
        Compute IDF (Inverse Document Frequency)
        
        Formula: log((N - df + 0.5) / (df + 0.5) + 1)
        """
        df = self.term_freq.get(term, 0)
        if df == 0:
            return 0.0
        
        idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
        return max(0.0, idf)
    
    def _compute_bm25_score(self, term, doc_id, field='abstract'):
        """
        Compute BM25 score untuk term di document
        
        Formula: IDF × (TF × (K1+1)) / (TF + K1 × (1-B + B × (dl/avgdl)))
        
        Args:
            term: Query term
            doc_id: Document ID
            field: Field to search ('abstract', 'title', 'keyword')
            
        Returns:
            BM25 score
        """
        tf = 0
        
        if field == 'title' and term in self.title_index:
            postings = self.title_index[term]
            if isinstance(postings, dict):
                tf = postings.get(doc_id, 0)
            elif isinstance(postings, list):
                tf = postings.count(doc_id)
        elif field == 'keyword' and term in self.keyword_index:
            postings = self.keyword_index[term]
            if isinstance(postings, dict):
                tf = postings.get(doc_id, 0)
            elif isinstance(postings, list):
                tf = postings.count(doc_id)
        else:
            if term in self.index:
                postings = self.index[term]
                if isinstance(postings, dict):
                    tf = postings.get(doc_id, 0)
                elif isinstance(postings, list):
                    tf = postings.count(doc_id)
        
        if tf == 0:
            return 0.0
        
        dl = self.doc_len.get(doc_id, self.avgdl)
        idf = self._compute_idf(term)
        
        numerator = tf * (K1 + 1)
        denominator = tf + K1 * (1 - B + B * (dl / self.avgdl))
        score = idf * (numerator / denominator)
        
        return score
    
    def _get_domain_boost(self, query_terms):
        """
        Get domain-specific boost factor
        
        Returns maximum boost dari matching domains
        """
        domain_scores = defaultdict(int)
        
        for domain, config in DOMAIN_PATTERNS.items():
            matches = sum(1 for term in query_terms if term in config['terms'])
            if matches > 0:
                domain_scores[domain] = matches * config['boost']
        
        if not domain_scores:
            return 1.0
        
        return max(domain_scores.values())
    
    def _calculate_term_coverage(self, query_terms, retrieved_terms):
        """
        Calculate coverage of query terms in retrieved document
        
        Coverage = (# query terms found) / (# total significant query terms)
        """
        if not query_terms:
            return 0.0
        
        significant_terms = [t for t in query_terms if t not in GENERIC_TERMS]
        if not significant_terms:
            significant_terms = query_terms
        
        covered = sum(1 for t in significant_terms if t in retrieved_terms)
        return covered / len(significant_terms)
    
    def search(self, query, top_k=100, verbose=False):
        """
        Search dengan Enhanced BM25 + Ultra-Smart Spell Correction
        
        Args:
            query: Query string
            top_k: Maximum results to return
            verbose: Print debug information
            
        Returns:
            {
                "results": [...],
                "query_info": {
                    "original_query": str,
                    "corrected_terms": list,
                    "expanded_terms": list,
                    "is_wildcard": bool,
                    "domain_boost": float
                }
            }
        """
        
        if verbose:
            print(f"\n{'='*80}")
            print(f"ENHANCED BM25 SEARCH")
            print(f"{'='*80}")
            print(f"Query: '{query}'")
        
        # Step 1: Tokenize
        query_terms = self._tokenize(query)
        
        if verbose:
            print(f"Tokenized: {query_terms}")
        
        # Step 2: Process each term (wildcard OR spell correction)
        corrected_tokens = []
        wildcard_terms = []
        
        for term in query_terms:
            if self._is_wildcard_query(term):
                # Process wildcard immediately
                wildcard_matches = self._expand_wildcard(term)
                
                if wildcard_matches:
                    wildcard_terms.extend(wildcard_matches)
                    corrected_tokens.append(term)  # Keep original for tracking
                    if verbose:
                        print(f"  Wildcard: '{term}' → {len(wildcard_matches)} matches")
                else:
                    # Wildcard returned nothing, try to correct the base term
                    base_term = term.replace('*', '').replace('?', '')
                    if base_term:
                        corrected = self.spell_corrector.correct(base_term)
                        corrected_tokens.append(corrected)
                        if verbose:
                            print(f"  Wildcard failed, corrected base: '{base_term}' → '{corrected}'")
                    else:
                        if verbose:
                            print(f"  Wildcard: '{term}' → NO MATCHES")
            else:
                # Normal spell correction
                corrected = self.spell_corrector.correct(term)
                
                # Handle segmented words
                if ' ' in corrected:
                    segments = corrected.split()
                    corrected_tokens.extend(segments)
                    if verbose:
                        print(f"  Segmented: '{term}' → {segments}")
                else:
                    corrected_tokens.append(corrected)
                    if verbose and corrected != term:
                        print(f"  Corrected: '{term}' → '{corrected}'")
        
        # Step 3: Build final terms list
        # If we have wildcard matches, use them; otherwise use corrected tokens
        if wildcard_terms:
            # Combine: wildcard results + non-wildcard corrected terms
            final_terms = []
            for token in corrected_tokens:
                if not self._is_wildcard_query(token):
                    final_terms.append(token)
            final_terms.extend(wildcard_terms)
        else:
            final_terms = corrected_tokens
        
        # Remove wildcards from corrected_tokens for coverage calculation
        corrected_tokens_no_wildcard = [t for t in corrected_tokens if not self._is_wildcard_query(t)]
        
        # Step 4: Query expansion (synonyms)
        expanded_terms = self._expand_query(final_terms)
        
        if verbose:
            print(f"Final terms: {expanded_terms[:10]}{'...' if len(expanded_terms) > 10 else ''}")
        
        # Step 5: Domain boost
        domain_boost = self._get_domain_boost(expanded_terms)
        if verbose and domain_boost > 1.0:
            print(f"Domain boost: {domain_boost:.2f}")
        
        # Step 6: BM25 Scoring
        doc_scores = defaultdict(float)
        doc_term_matches = defaultdict(set)
        
        for term in expanded_terms:
            if term not in self.vocabulary:
                continue
            
            # Score from Abstract
            if term in self.index:
                for doc_id in self._get_doc_ids_from_postings(self.index[term]):
                    doc_scores[doc_id] += (
                        self._compute_bm25_score(term, doc_id, 'abstract')
                        * ABSTRACT_BOOST * domain_boost
                    )
                    doc_term_matches[doc_id].add(term)
            
            # Score from Title (BOOST 8×)
            if term in self.title_index:
                for doc_id in self._get_doc_ids_from_postings(self.title_index[term]):
                    doc_scores[doc_id] += (
                        self._compute_bm25_score(term, doc_id, 'title')
                        * TITLE_BOOST * domain_boost
                    )
                    doc_term_matches[doc_id].add(term)
            
            # Score from Keyword (BOOST 6×)
            if term in self.keyword_index:
                for doc_id in self._get_doc_ids_from_postings(self.keyword_index[term]):
                    doc_scores[doc_id] += (
                        self._compute_bm25_score(term, doc_id, 'keyword')
                        * KEYWORD_BOOST * domain_boost
                    )
                    doc_term_matches[doc_id].add(term)
        
        # Check if wildcard query (one or more wildcards)
        has_wildcard = any(self._is_wildcard_query(t) for t in query_terms)
        
        # Step 7: Filtering with term coverage
        filtered_docs = {}
        for doc_id, score in doc_scores.items():
            # Use corrected_tokens_no_wildcard for coverage
            if corrected_tokens_no_wildcard:
                coverage = self._calculate_term_coverage(
                    corrected_tokens_no_wildcard,
                    doc_term_matches[doc_id]
                )
            else:
                # All wildcards, no coverage check
                coverage = 1.0
            
            # For wildcard queries, be more lenient
            if has_wildcard:
                # Lower thresholds for wildcard queries
                if score >= MIN_SCORE_THRESHOLD * 0.7:  # 70% of normal threshold
                    if coverage >= 0.3 or not corrected_tokens_no_wildcard:  # 30% coverage OK
                        filtered_docs[doc_id] = score
            else:
                # Normal filtering
                if score >= MIN_SCORE_THRESHOLD and coverage >= MIN_TERM_COVERAGE:
                    # Boost for high coverage
                    if coverage >= IDEAL_TERM_COVERAGE:
                        score *= 1.3
                    elif coverage >= 0.6:
                        score *= 1.15
                    
                    filtered_docs[doc_id] = score
        
        # Step 8: Sort by score
        sorted_docs = sorted(filtered_docs.items(), key=lambda x: x[1], reverse=True)
        
        # Step 9: Adaptive result limiting
        num_terms = len([t for t in corrected_tokens_no_wildcard if t not in GENERIC_TERMS])
        if num_terms >= 3:
            limit = MAX_RESULTS_SPECIFIC
        elif num_terms >= 2:
            limit = MAX_RESULTS_MODERATE
        else:
            limit = MAX_RESULTS_GENERIC
        
        final_limit = min(limit, top_k)
        
        # Step 10: Build results
        results = []
        for doc_id, score in sorted_docs[:final_limit]:
            meta = self.doc_metadata.get(doc_id, {})
            results.append({
                "doc_id": doc_id,
                "score": score,
                "title": meta.get("title", "N/A"),
                "authors": meta.get("authors", "N/A"),
                "keywords": meta.get("keywords", "N/A"),
                "abstract": meta.get("abstract", "N/A"),
            })
        
        if verbose:
            print(f"\nFiltered: {len(doc_scores)} → {len(filtered_docs)} docs")
            print(f"Returning top {len(results)} results (limit: {final_limit})")
            if results:
                top_scores = [f"{r['score']:.2f}" for r in results[:5]]
                print(f"Top 5 scores: {top_scores}")
            print(f"{'='*80}\n")
        
        return {
            "results": results,
            "query_info": {
                "original_query": query,
                "corrected_terms": corrected_tokens_no_wildcard,
                "expanded_terms": expanded_terms,
                "is_wildcard": has_wildcard,
                "domain_boost": domain_boost
            }
        }
    
    def get_stats(self):
        """Get ranker statistics"""
        return {
            'num_blocks': len(self.blocks),
            'num_terms': len(self.vocabulary),
            'compression_ratio': len(self.vocabulary) / len(self.blocks) if self.blocks else 0,
            'num_docs': self.N,
            'avg_doc_len': self.avgdl,
            'config': {
                'K1': K1,
                'B': B,
                'title_boost': TITLE_BOOST,
                'keyword_boost': KEYWORD_BOOST,
                'abstract_boost': ABSTRACT_BOOST,
                'min_score': MIN_SCORE_THRESHOLD,
                'min_coverage': MIN_TERM_COVERAGE
            },
            'spell_corrector': self.spell_corrector.get_stats()
        }


def main():
    """Test Enhanced BM25 Ranker"""
    BASE_DIR = Path(__file__).resolve().parent
    BLOCKS_PATH = BASE_DIR / "data/blocks.json"
    FRONTCODED_PATH = BASE_DIR / "data/frontcoded.json"
    INDEX_PATH = BASE_DIR / "data/index.json"
    
    ranker = EnhancedBM25Ranker(BLOCKS_PATH, FRONTCODED_PATH, INDEX_PATH)
    
    print("\n" + "="*80)
    print("TESTING ENHANCED BM25 RANKER")
    print("="*80)
    
    test_queries = [
        "analisi sentime",                    # Typo
        "analisissentimen",                   # Segmentation needed
        "sentimennnnnnnn",                   # Heavy noise
        "pemodelantopik",                    # Compound word
        "machinelearning",                   # English compound
        "sentim*",                           # Wildcard
        "ma?hine learning",                  # Wildcard + space
        "klasifikasiiiiiii penyakittttt",   # Multiple noise
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        result = ranker.search(query, top_k=3, verbose=True)
        
        print(f"\nTop 3 Results:")
        for i, r in enumerate(result['results'][:3], 1):
            print(f"  {i}. [{r['score']:.2f}] {r['title'][:70]}...")
        
        print(f"\nQuery Info:")
        print(f"  Original: {result['query_info']['original_query']}")
        print(f"  Corrected: {result['query_info']['corrected_terms']}")
        print(f"  Wildcard: {result['query_info']['is_wildcard']}")
        print(f"  Domain Boost: {result['query_info']['domain_boost']:.2f}")


if __name__ == "__main__":
    main()
