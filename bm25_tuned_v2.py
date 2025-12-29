#bm25_tuned_v2.py

import json
import math
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
BLOCKS_PATH = BASE_DIR / "streamlit_ir/blocks.json"
FRONTCODED_PATH = BASE_DIR / "streamlit_ir/frontcoded.json"
INDEX_PATH = BASE_DIR / "streamlit_ir/index.json"

# BM25 Parameters
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
GENERIC_TERMS = {'dengan', 'untuk', 'pada', 'yang', 'dari', 'dan', 'atau', 'ke', 'oleh', 'di', 'adalah'}

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


def normalize_repeated_chars(text):
    """
    Normalize repeated characters
    Example: sentimennnnnnnn -> sentimen, analisiiiiis -> analisis
    Allow max 2 repeated characters
    """
    # Pattern: replace 3+ consecutive same chars with max 2
    normalized = re.sub(r'(.)\1{2,}', r'\1\1', text)
    return normalized


def wildcard_to_regex(pattern):
    """
    Convert wildcard pattern to regex
    * = any characters (0 or more)
    ? = single character
    """
    # Escape special regex characters except * and ?
    pattern = re.escape(pattern)
    # Replace escaped wildcards with regex equivalents
    pattern = pattern.replace(r'\*', '.*')  # * -> .*
    pattern = pattern.replace(r'\?', '.')    # ? -> .
    return f'^{pattern}$'


class TunedDictionaryBM25Ranker:
    """
    TUNED BM25 Ranker with Wildcard & Repeated Character Handling
    """
    
    def __init__(self, blocks_path, frontcoded_path, index_path):
        """Load dictionary and index"""
        print(f"Loading TUNED BM25 dictionary and index...")
        
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
        
        # Build common typos dictionary
        self.common_typos = self._build_common_typos()
        
        # Synonyms
        self.synonyms = self._build_synonyms()
        
        print(f"  ✓ Index loaded: {self.N} docs, {len(self.index)} terms")
        print(f"  ✓ Common typos: {len(self.common_typos)} patterns")
        print(f"  ✓ Features: Wildcard (*,?) + Repeated char normalization")
        print(f"  ✓ Configuration: TUNED (K1={K1}, B={B})")
    
    def _build_common_typos(self):
        """Build common typo patterns"""
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
            'klasifksi': 'klasifikasi',
            'predksi': 'prediksi',
            'algortima': 'algoritma',
            'algortma': 'algoritma',
            
            # NLP terms
            'sentmen': 'sentimen',
            'sentimn': 'sentimen',
            'peringksn': 'peringkasan',
            'peringkasn': 'peringkasan',
            
            # System terms
            'sistem': 'sistem',
            'sistm': 'sistem',
            'rekomndasi': 'rekomendasi',
            'rekomndsi': 'rekomendasi',
            'apliksi': 'aplikasi',
            'aplikas': 'aplikasi',
            
            # Security terms
            'enkripsi': 'enkripsi',
            'enkrpsi': 'enkripsi',
            'keamnan': 'keamanan',
            'keamaan': 'keamanan',
            
            # Common words
            'desain': 'desain',
            'desan': 'desain',
            'optimsi': 'optimasi',
            'optimasi': 'optimasi',
            'analsis': 'analisis',
            'analisys': 'analisis'
        }
    
    def _build_synonyms(self):
        """Build synonym dictionary"""
        return {
            'ml': 'machine learning',
            'ai': 'artificial intelligence',
            'dl': 'deep learning',
            'nn': 'neural network',
            'ui': 'user interface',
            'ux': 'user experience',
            'bi': 'business intelligence'
        }
    
    def _tokenize(self, text):
        """Tokenization with cleaning and repeated char normalization"""
        if not text:
            return []
        
        # Normalize repeated characters FIRST
        text = normalize_repeated_chars(text.lower())
        
        tokens = text.split()
        # Remove very short tokens
        return [t for t in tokens if len(t) > 1]
    
    def _is_wildcard_query(self, term):
        """Check if term contains wildcard characters"""
        return '*' in term or '?' in term
    
    def _expand_wildcard(self, pattern):
        """
        Expand wildcard pattern to matching terms from vocabulary
        Example: "sentim*" -> ["sentimen", "sentiment", "sentimental"]
        """
        if not self._is_wildcard_query(pattern):
            return [pattern]
        
        # Convert wildcard to regex
        regex_pattern = wildcard_to_regex(pattern)
        regex = re.compile(regex_pattern, re.IGNORECASE)
        
        # Find matching terms in vocabulary
        matches = [term for term in self.vocabulary if regex.match(term)]
        
        # Limit to top 20 matches to avoid performance issues
        if len(matches) > 20:
            # Prioritize by term frequency
            matches = sorted(matches, key=lambda t: self.term_freq.get(t, 0), reverse=True)[:20]
        
        return matches if matches else [pattern]
    
    def _correct_spelling(self, term):
        """Correct spelling with typo patterns"""
        # Check exact match in typos
        if term in self.common_typos:
            return self.common_typos[term]
        
        # Check if term in vocabulary
        if term in self.vocabulary:
            return term
        
        # Find close matches with edit distance
        min_dist = float('inf')
        best_match = term
        
        for vocab_term in self.vocabulary:
            # Only check similar length terms
            if abs(len(vocab_term) - len(term)) > 2:
                continue
            
            dist = edit_distance(term, vocab_term)
            if dist < min_dist and dist <= 2:  # Allow up to 2 edits
                min_dist = dist
                best_match = vocab_term
        
        return best_match if min_dist <= 2 else term
    
    def _expand_query(self, query_terms):
        """Expand query with synonyms and wildcards"""
        expanded = []
        
        for term in query_terms:
            # Handle wildcard first
            if self._is_wildcard_query(term):
                wildcard_matches = self._expand_wildcard(term)
                expanded.extend(wildcard_matches)
            else:
                expanded.append(term)
                
                # Add synonyms
                if term in self.synonyms:
                    synonym_terms = self.synonyms[term].split()
                    expanded.extend(synonym_terms)
        
        return expanded
    
    def _get_doc_ids_from_postings(self, postings):
        """Get document IDs from posting list"""
        if isinstance(postings, dict):
            return list(postings.keys())
        elif isinstance(postings, list):
            return list(dict.fromkeys(postings))
        else:
            return []
    
    def _compute_idf(self, term):
        """Compute IDF"""
        df = self.term_freq.get(term, 0)
        if df == 0:
            return 0.0
        
        idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
        return max(0.0, idf)
    
    def _compute_bm25_score(self, term, doc_id, field='abstract'):
        """Compute BM25 score with tuned parameters"""
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
        """Get domain-specific boost"""
        domain_scores = defaultdict(int)
        
        for domain, config in DOMAIN_PATTERNS.items():
            matches = sum(1 for term in query_terms if term in config['terms'])
            if matches > 0:
                domain_scores[domain] = matches * config['boost']
        
        if not domain_scores:
            return 1.0
        
        return max(domain_scores.values())
    
    def _calculate_term_coverage(self, query_terms, retrieved_terms):
        """Calculate coverage of query terms in retrieved doc"""
        if not query_terms:
            return 0.0
        
        significant_terms = [t for t in query_terms if t not in GENERIC_TERMS]
        if not significant_terms:
            significant_terms = query_terms
        
        covered = sum(1 for t in significant_terms if t in retrieved_terms)
        return covered / len(significant_terms)
    
    def search(self, query, top_k=100, verbose=False):
        """Search with tuned parameters + wildcard support"""
        # Tokenize and clean (includes repeated char normalization)
        query_terms = self._tokenize(query)
        
        if verbose:
            print(f"\n[TUNED BM25 SEARCH + WILDCARD]")
            print(f"Query: {query}")
            print(f"Tokenized: {query_terms}")
        
        # Spelling correction (skip wildcards)
        corrected_terms = []
        for term in query_terms:
            if self._is_wildcard_query(term):
                corrected_terms.append(term)
                if verbose:
                    print(f"  Wildcard detected: '{term}'")
            else:
                corrected = self._correct_spelling(term)
                corrected_terms.append(corrected)
                if verbose and corrected != term:
                    print(f"  Corrected: '{term}' → '{corrected}'")
        
        # Query expansion (includes wildcard expansion)
        expanded_terms = self._expand_query(corrected_terms)
        
        if verbose:
            print(f"Expanded terms: {expanded_terms[:10]}{'...' if len(expanded_terms) > 10 else ''}")
        
        # Get domain boost
        domain_boost = self._get_domain_boost(expanded_terms)
        if verbose:
            print(f"Domain boost: {domain_boost:.2f}")
        
        # Score documents
        doc_scores = defaultdict(float)
        doc_term_matches = defaultdict(set)
        
        for term in expanded_terms:
            if term not in self.vocabulary:
                if verbose:
                    print(f"  Term '{term}' not in vocabulary")
                continue
            
            # Score from abstract
            if term in self.index:
                doc_ids = self._get_doc_ids_from_postings(self.index[term])
                for doc_id in doc_ids:
                    score = self._compute_bm25_score(term, doc_id, 'abstract')
                    doc_scores[doc_id] += score * ABSTRACT_BOOST * domain_boost
                    doc_term_matches[doc_id].add(term)
            
            # Score from title
            if term in self.title_index:
                doc_ids = self._get_doc_ids_from_postings(self.title_index[term])
                for doc_id in doc_ids:
                    score = self._compute_bm25_score(term, doc_id, 'title')
                    doc_scores[doc_id] += score * TITLE_BOOST * domain_boost
                    doc_term_matches[doc_id].add(term)
            
            # Score from keywords
            if term in self.keyword_index:
                doc_ids = self._get_doc_ids_from_postings(self.keyword_index[term])
                for doc_id in doc_ids:
                    score = self._compute_bm25_score(term, doc_id, 'keyword')
                    doc_scores[doc_id] += score * KEYWORD_BOOST * domain_boost
                    doc_term_matches[doc_id].add(term)
        
        # Filter by term coverage and score threshold
        filtered_docs = {}
        for doc_id, score in doc_scores.items():
            coverage = self._calculate_term_coverage(
                corrected_terms, 
                doc_term_matches[doc_id]
            )
            
            if score >= MIN_SCORE_THRESHOLD and coverage >= MIN_TERM_COVERAGE:
                if coverage >= IDEAL_TERM_COVERAGE:
                    score *= 1.3
                elif coverage >= 0.6:
                    score *= 1.15
                
                filtered_docs[doc_id] = score
        
        # Sort by score
        sorted_docs = sorted(filtered_docs.items(), key=lambda x: x[1], reverse=True)
        
        # Determine result limit
        num_query_terms = len([t for t in corrected_terms if t not in GENERIC_TERMS])
        if num_query_terms >= 3:
            limit = MAX_RESULTS_SPECIFIC
        elif num_query_terms == 2:
            limit = MAX_RESULTS_MODERATE
        else:
            limit = MAX_RESULTS_GENERIC
        
        # Format results
        results = []
        for doc_id, score in sorted_docs[:limit]:
            metadata = self.doc_metadata.get(doc_id, {})
            coverage = self._calculate_term_coverage(
                corrected_terms,
                doc_term_matches[doc_id]
            )
            
            results.append({
                'doc_id': doc_id,
                'score': score,
                'coverage': coverage,
                'title': metadata.get('title', 'N/A'),
                'authors': metadata.get('authors', 'N/A'),
                'keywords': metadata.get('keywords', 'N/A'),
                'abstract': metadata.get('abstract', 'N/A')
            })
        
        if verbose:
            print(f"\nFiltered: {len(doc_scores)} → {len(filtered_docs)} docs")
            print(f"Returning top {len(results)} results (limit: {limit})")
            if results:
                top_scores = [f"{r['score']:.2f}" for r in results[:5]]
                print(f"Top 5 scores: {top_scores}")
        
        return results
    
    def get_dictionary_stats(self):
        """Get dictionary statistics"""
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
                'min_score': MIN_SCORE_THRESHOLD,
                'min_coverage': MIN_TERM_COVERAGE
            }
        }


def main():
    """Test ranker with wildcard and repeated chars"""
    BASE_DIR = Path(__file__).resolve().parent.parent
    BLOCKS_PATH = BASE_DIR / "streamlit_ir/data/blocks.json"
    FRONTCODED_PATH = BASE_DIR / "streamlit_ir/data/frontcoded.json"
    INDEX_PATH = BASE_DIR / "streamlit_ir/data/index.json"
    
    ranker = TunedDictionaryBM25Ranker(BLOCKS_PATH, FRONTCODED_PATH, INDEX_PATH)
    
    print("\n" + "="*80)
    print("TESTING WILDCARD + REPEATED CHARACTER HANDLING")
    print("="*80)
    
    test_queries = [
        "analisis sentimennnnnnnnnn",  # Repeated chars
        "sentim*",                      # Wildcard *
        "ma?hine learning",             # Wildcard ?
        "sistem rekomen*",              # Wildcard at end
        "klasifikasiiiiiii penyakittttt",  # Multiple repeated chars
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = ranker.search(query, top_k=3, verbose=True)
        print(f"\nTop 3 Results:")
        for i, r in enumerate(results[:3], 1):
            print(f"  {i}. {r['title'][:60]}... (score: {r['score']:.2f})")


if __name__ == "__main__":
    main()