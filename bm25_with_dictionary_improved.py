# bm25_with_dictionary_improved_v2.py
"""
BM25 Ranker dengan Dictionary + ENHANCED Spelling Correction
Perbaikan untuk handle:
1. Kata terpotong: "analisi sentime" → "analisis sentimen"
2. Kata digabung: "analisisentime" → "analisis sentimen"
3. Typo ekstrem: "analisos sentmn" → "analisis sentimen"
"""

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

# Score thresholds - LOWERED untuk hindari false negative
MIN_SCORE_THRESHOLD = 3.0  # Lowered from 8.0 to 3.0

# Term coverage - RELAXED untuk hindari false negative
MIN_TERM_COVERAGE = 0.40  # Lowered from 0.65 to 0.40
IDEAL_TERM_COVERAGE = 0.70  # Lowered from 0.85 to 0.70

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


class EnhancedDictionaryBM25Ranker:
    """
    Enhanced BM25 dengan spelling correction yang lebih baik
    Handle: kata terpotong, kata digabung, typo ekstrem
    """
    
    def __init__(self, blocks_path, frontcoded_path, index_path):
        """Load dictionary and index"""
        print(f"Loading enhanced dictionary and index...")
        
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
        
        # Build enhanced typo dictionary
        self.common_typos = self._build_common_typos()
        
        # Build word pairs for compound detection
        self.common_pairs = self._build_common_pairs()
        
        # Synonyms
        self.synonyms = self._build_synonyms()
        
        print(f"  ✓ Index loaded: {self.N} docs, {len(self.index)} terms")
        print(f"  ✓ Common typos: {len(self.common_typos)} patterns")
        print(f"  ✓ Common pairs: {len(self.common_pairs)} word combinations")
    
    def _build_common_typos(self):
        """Build comprehensive typo patterns"""
        return {
            # Medical terms
            'detksi': 'deteksi', 'deteksi': 'deteksi', 'detek': 'deteksi',
            'penykti': 'penyakit', 'penykit': 'penyakit', 'penyakit': 'penyakit', 'penykt': 'penyakit',
            'jntung': 'jantung', 'jantng': 'jantung', 'jantung': 'jantung', 'jntng': 'jantung',
            'diabtes': 'diabetes', 'diabetis': 'diabetes', 'diabet': 'diabetes',
            'kankr': 'kanker', 'kanker': 'kanker', 'kankr': 'kanker',
            'strke': 'stroke', 'stroke': 'stroke', 'strok': 'stroke',
            'dagnosis': 'diagnosis', 'diagnosa': 'diagnosis', 'diagnosis': 'diagnosis', 'diagnos': 'diagnosis',
            'kesehtan': 'kesehatan', 'kesehatn': 'kesehatan', 'kesehatan': 'kesehatan', 'kesehat': 'kesehatan',
            
            # Analysis & Sentiment
            'analisi': 'analisis', 'analisis': 'analisis', 'analis': 'analisis', 'analisa': 'analisis',
            'analisos': 'analisis', 'analisys': 'analisis', 'analize': 'analisis',
            'sentime': 'sentimen', 'sentimen': 'sentimen', 'sentiment': 'sentimen', 'sentimn': 'sentimen',
            'sentmn': 'sentimen', 'sentimnt': 'sentimen', 'sentimnt': 'sentimen',
            
            # ML/AI terms
            'machin': 'machine', 'machine': 'machine', 'machn': 'machine',
            'lerning': 'learning', 'learnnig': 'learning', 'learning': 'learning', 'learnng': 'learning',
            'klasifkasi': 'klasifikasi', 'klasifikasi': 'klasifikasi', 'klasifksi': 'klasifikasi',
            'algortima': 'algoritma', 'algoritma': 'algoritma', 'algorit': 'algoritma', 'algoritme': 'algoritma',
            'predksi': 'prediksi', 'prediksi': 'prediksi', 'prediks': 'prediksi',
            
            # System terms
            'sistem': 'sistem', 'sistim': 'sistem', 'system': 'sistem', 'sistm': 'sistem',
            'aplikas': 'aplikasi', 'aplikasi': 'aplikasi', 'aplkasi': 'aplikasi', 'apliksi': 'aplikasi',
            'rekomndasi': 'rekomendasi', 'rekomendasi': 'rekomendasi', 'rekomend': 'rekomendasi',
            'pencaruan': 'pencarian', 'pencarian': 'pencarian', 'pencrarian': 'pencarian', 'pencaran': 'pencarian',
            
            # UI/UX terms
            'interfce': 'interface', 'interface': 'interface', 'intrface': 'interface', 'interfac': 'interface',
            'antarmka': 'antarmuka', 'antarmuka': 'antarmuka', 'antarmka': 'antarmuka',
            'pengguna': 'pengguna', 'pemakai': 'pengguna', 'penguna': 'pengguna',
            
            # Other
            'ontolgi': 'ontologi', 'ontologi': 'ontologi', 'ontolog': 'ontologi',
            'jaringan': 'jaringan', 'jaringn': 'jaringan', 'jaring': 'jaringan',
        }
    
    def _build_common_pairs(self):
        """Build common word pairs untuk deteksi kata digabung"""
        return {
            'analisissentimen': ['analisis', 'sentimen'],
            'analisisentimen': ['analisis', 'sentimen'],
            'analisissistem': ['analisis', 'sistem'],
            'sistemrekomendasi': ['sistem', 'rekomendasi'],
            'machinelearning': ['machine', 'learning'],
            'deeplearning': ['deep', 'learning'],
            'userinterface': ['user', 'interface'],
            'deteksipenyakit': ['deteksi', 'penyakit'],
            'klasifikasipenyakit': ['klasifikasi', 'penyakit'],
            'textmining': ['text', 'mining'],
            'datamining': ['data', 'mining'],
            'neuralnetwork': ['neural', 'network'],
        }
    
    def _build_synonyms(self):
        """Build synonyms"""
        return {
            'sistem': {'aplikasi', 'program'},
            'aplikasi': {'sistem', 'program'},
            'analisis': {'analisa'},
            'analisa': {'analisis'},
            'sentimen': {'sentiment'},
            'sentiment': {'sentimen'},
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
    
    def split_compound_word(self, word):
        """
        NEW: Split kata yang digabung menjadi dua kata
        Contoh: "analisisentime" → ["analisis", "sentimen"]
        """
        # Check if exact match in common pairs
        word_lower = word.lower()
        if word_lower in self.common_pairs:
            return self.common_pairs[word_lower]
        
        # Try to find valid splits
        best_split = None
        best_score = 0
        
        # Try different split points (minimum 4 chars each part)
        for i in range(4, len(word) - 3):
            part1 = word[:i]
            part2 = word[i:]
            
            # Correct each part
            corrected1, _, dist1 = self.correct_spelling(part1)
            corrected2, _, dist2 = self.correct_spelling(part2)
            
            # Calculate split score (lower distance = better)
            if dist1 < 999 and dist2 < 999:
                # Prioritize splits where both parts are in vocabulary
                freq1 = self.term_freq.get(corrected1, 0)
                freq2 = self.term_freq.get(corrected2, 0)
                
                # Score based on: found in dict, frequency, and edit distance
                score = (freq1 + freq2) - (dist1 + dist2) * 10
                
                if score > best_score:
                    best_score = score
                    best_split = [corrected1, corrected2]
        
        return best_split if best_split else None
    
    def complete_truncated_word(self, word):
        """
        NEW: Complete kata yang terpotong
        Contoh: "analisi" → "analisis", "sentime" → "sentimen"
        """
        if len(word) < 4:
            return None
        
        # Find words that start with this prefix
        candidates = []
        
        # Search in blocks
        block_key = word[:3]
        if block_key in self.blocks:
            for term in self.blocks[block_key]:
                if term.startswith(word):
                    freq = self.term_freq.get(term, 0)
                    length_diff = len(term) - len(word)
                    # Prefer shorter completions with higher frequency
                    score = freq - length_diff * 10
                    candidates.append((term, score, length_diff))
        
        if candidates:
            # Sort by score (higher is better)
            candidates.sort(key=lambda x: x[1], reverse=True)
            # Return best match if completion is reasonable (max 4 chars added)
            if candidates[0][2] <= 4:
                return candidates[0][0]
        
        return None
    
    def correct_spelling(self, word):
        """
        ENHANCED spelling correction dengan multi-stage approach
        """
        # Stage 0: Check if word already correct
        if self.find_term_in_dictionary(word):
            return word, True, 0
        
        # Stage 1: Check common typos dictionary - PRIORITY
        if word in self.common_typos:
            corrected = self.common_typos[word]
            if self.find_term_in_dictionary(corrected):
                return corrected, False, 1
        
        # Stage 2: Try to complete truncated word
        completed = self.complete_truncated_word(word)
        if completed:
            return completed, False, len(completed) - len(word)
        
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
            
            # Add blocks with similar prefixes
            for i in range(min(3, len(word))):
                for c in 'abcdefghijklmnopqrstuvwxyz':
                    variant = word[:i] + c + (word[i+1:3] if len(word) > i+1 else '')
                    if len(variant) >= 3 and variant in self.blocks:
                        search_prefixes.add(variant)
        
        max_distance = min(4, len(word) // 2 + 1)
        
        for prefix in search_prefixes:
            if prefix not in self.blocks:
                continue
            
            for vocab_term in self.blocks[prefix]:
                if abs(len(vocab_term) - len(word)) > max_distance:
                    continue
                
                dist = edit_distance(word, vocab_term)
                if dist <= max_distance:
                    freq = self.term_freq.get(vocab_term, 0)
                    candidates.append((vocab_term, dist, freq))
        
        if candidates:
            candidates.sort(key=lambda x: (x[1], -x[2]))
            return candidates[0][0], False, candidates[0][1]
        
        # No correction found
        return word, False, 999
    
    def preprocess_query(self, query):
        """
        ENHANCED query preprocessing dengan handling untuk:
        1. Kata digabung
        2. Kata terpotong
        3. Typo ekstrem
        """
        query = query.lower().strip()
        
        # Remove extra spaces
        query = re.sub(r'\s+', ' ', query)
        
        # Initial tokenization
        raw_terms = [t for t in query.split() if len(t) > 1]
        
        if not raw_terms:
            return [], []
        
        # Process each term
        corrected_terms = []
        corrections = []
        
        for term in raw_terms:
            # Try to detect compound word first
            split_result = self.split_compound_word(term)
            
            if split_result:
                # Word was split successfully
                corrected_terms.extend(split_result)
                corrections.append(f"{term}→{' '.join(split_result)}")
            else:
                # Normal spelling correction
                corrected, was_correct, distance = self.correct_spelling(term)
                corrected_terms.append(corrected)
                
                if not was_correct and distance < 999:
                    corrections.append(f"{term}→{corrected}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in corrected_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        # Query expansion (only if corrections look good)
        all_distances = [999]  # default
        for term in raw_terms:
            _, _, dist = self.correct_spelling(term)
            all_distances.append(dist)
        
        if all(d < 3 for d in all_distances):
            expanded_terms = self.expand_query(unique_terms)
        else:
            expanded_terms = unique_terms
        
        return expanded_terms, corrections
    
    def expand_query(self, terms):
        """Query expansion with synonyms"""
        expanded = set(terms)
        for term in terms:
            if term in self.synonyms:
                # Add top 2 synonyms
                expanded.update(list(self.synonyms[term])[:2])
        return list(expanded)
    
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
            best_domain = max(domain_matches.items(), key=lambda x: x[1])
            return best_domain[0], DOMAIN_PATTERNS[best_domain[0]]['boost']
        
        return 'general', 1.0
    
    def compute_idf(self, term):
        """Compute IDF with penalty"""
        if term not in self.index:
            return 0.0
        
        df = len(self.index[term])
        idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1.0)
        
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
        """Check semantic relevance - RELAXED untuk hindari false negative"""
        core_terms = self.get_core_terms(query_terms)
        if not core_terms:
            return True
        
        metadata = self.doc_metadata.get(doc_id, {})
        doc_text = (
            metadata.get('title', '') + ' ' + 
            metadata.get('keywords', '') + ' ' + 
            metadata.get('abstract', '')
        ).lower()
        
        matches = 0
        for term in core_terms:
            if term in doc_text:
                matches += 1
                continue
            
            if term in self.synonyms:
                if any(syn in doc_text for syn in self.synonyms[term]):
                    matches += 1
                    continue
        
        coverage = matches / len(core_terms)
        # RELAXED: 50% coverage (was 70%)
        return coverage >= 0.5
    
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
            
            kw_matches = sum(1 for t in core_terms
                           if t in self.keyword_index and doc_id in self.keyword_index[t])
            
            if kw_matches > 0:
                kw_cov = kw_matches / len(core_terms)
                mult += KEYWORD_BOOST * kw_cov
            
            if title_matches == len(core_terms) and len(core_terms) >= 2:
                mult *= 2.0
            
            coverage = self.compute_term_coverage(query_terms, doc_id)
            if coverage >= IDEAL_TERM_COVERAGE:
                mult *= 1.4
            elif coverage >= 0.6:
                mult *= 1.2
            
            mult *= domain_boost
            
            boosted[doc_id] = base_score * mult
        
        return boosted
    
    def filter_results(self, scores, specificity):
        """Filter results with RELAXED threshold"""
        if not scores:
            return {}
        
        score_values = sorted(scores.values(), reverse=True)
        
        # More results for each category
        if specificity == 'specific':
            max_results = MAX_RESULTS_SPECIFIC
            percentile = 0.30  # More lenient
        elif specificity == 'moderate':
            max_results = MAX_RESULTS_MODERATE
            percentile = 0.40  # More lenient
        else:
            max_results = MAX_RESULTS_GENERIC
            percentile = 0.50  # More lenient
        
        # Adaptive threshold - MORE RELAXED
        if len(score_values) > 15:
            cutoff_idx = max(5, int(len(score_values) * percentile))
            adaptive_threshold = score_values[min(cutoff_idx, len(score_values)-1)]
        else:
            # For small result sets, use lower threshold
            adaptive_threshold = MIN_SCORE_THRESHOLD * 0.5
        
        # Use the LOWER of the two thresholds
        threshold = min(adaptive_threshold, MIN_SCORE_THRESHOLD)
        
        # Apply threshold
        filtered = {doc_id: score for doc_id, score in scores.items()
                   if score >= threshold}
        
        # If we filtered too much, relax further
        if len(filtered) < 3 and len(scores) >= 3:
            # Just take top scores without threshold
            sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            filtered = dict(sorted_items[:max(max_results, 10)])
        
        # Limit results
        if len(filtered) > max_results:
            sorted_items = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
            filtered = dict(sorted_items[:max_results])
        
        return filtered
    
    def search(self, query, top_k=10, verbose=False):
        """Main search function with enhanced correction"""
        # Preprocess with enhanced correction
        query_terms, corrections = self.preprocess_query(query)
        
        if not query_terms:
            return []
        
        if corrections and verbose:
            print(f"✓ Corrected: {', '.join(corrections)}")
        
        if verbose:
            print(f"✓ Query terms: {query_terms}")
        
        # Analyze
        specificity = self.analyze_query_specificity(query_terms)
        domain, domain_boost = self.detect_query_domain(query_terms)
        
        if verbose:
            print(f"✓ Specificity: {specificity}, Domain: {domain}")
        
        # Collect candidates
        candidate_docs = defaultdict(int)
        
        for term in query_terms:
            if term in self.index:
                for doc_id in self.index[term].keys():
                    candidate_docs[doc_id] += 1
        
        if verbose:
            print(f"✓ Initial candidates: {len(candidate_docs)}")
        
        # Coverage filter
        core_terms = self.get_core_terms(query_terms)
        min_matches = max(1, int(len(core_terms) * MIN_TERM_COVERAGE))
        
        candidate_docs = {doc_id: count for doc_id, count in candidate_docs.items()
                         if count >= min_matches}
        
        if verbose:
            print(f"✓ After coverage filter: {len(candidate_docs)} (min_matches={min_matches})")
        
        # Fallback with more relaxed threshold
        if len(candidate_docs) < 5:
            min_matches = max(1, int(len(core_terms) * 0.25))  # More relaxed: 25%
            candidate_docs = defaultdict(int)
            for term in query_terms:
                if term in self.index:
                    for doc_id in self.index[term].keys():
                        candidate_docs[doc_id] += 1
            candidate_docs = {doc_id: count for doc_id, count in candidate_docs.items()
                             if count >= min_matches}
            
            if verbose:
                print(f"✓ After relaxed fallback: {len(candidate_docs)} (min_matches={min_matches})")
        
        if not candidate_docs:
            if verbose:
                print("✗ No candidates found!")
            return []
        
        # Semantic filtering - OPTIONAL, not strict
        semantically_relevant = {}
        for doc_id in candidate_docs.keys():
            if self.check_semantic_relevance(query_terms, doc_id):
                semantically_relevant[doc_id] = candidate_docs[doc_id]
        
        # Only use semantic filtering if we have enough results
        if len(semantically_relevant) >= max(3, len(candidate_docs) // 3):
            candidate_docs = semantically_relevant
            if verbose:
                print(f"✓ After semantic filter: {len(candidate_docs)}")
        else:
            if verbose:
                print(f"✓ Skipping semantic filter (too few: {len(semantically_relevant)})")
        
        # Score
        scores = {}
        for doc_id in candidate_docs.keys():
            score = self.compute_bm25_score(query_terms, doc_id)
            if score > 0:
                scores[doc_id] = score
        
        if verbose:
            print(f"✓ Scored documents: {len(scores)}")
            if scores:
                print(f"  Top score: {max(scores.values()):.2f}")
        
        # Boost
        scores = self.apply_boosting(query_terms, scores, domain_boost)
        
        if verbose:
            print(f"✓ After boosting:")
            if scores:
                print(f"  Top score: {max(scores.values()):.2f}")
        
        # Filter with adaptive threshold
        scores = self.filter_results(scores, specificity)
        
        if verbose:
            print(f"✓ After filtering: {len(scores)} results")
        
        # Final semantic check - MORE RELAXED
        final_scores = {}
        for doc_id, score in scores.items():
            if self.check_semantic_relevance(query_terms, doc_id):
                final_scores[doc_id] = score
        
        # If too strict, keep more results
        if len(final_scores) < max(3, len(scores) // 2):
            final_scores = scores
            if verbose:
                print(f"✓ Keeping all scores (semantic check too strict)")
        
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
            'num_typo_patterns': len(self.common_typos),
            'num_word_pairs': len(self.common_pairs)
        }


def main():
    """Test the enhanced ranker"""
    print("="*80)
    print("Enhanced BM25 with Advanced Spelling Correction")
    print("="*80)
    
    ranker = EnhancedDictionaryBM25Ranker(BLOCKS_PATH, FRONTCODED_PATH, INDEX_PATH)
    
    # Test queries - INCLUDE NORMAL QUERIES
    test_queries = [
        # Normal queries (should work!)
        ("analisis sentimen", "Normal query"),
        ("sistem rekomendasi", "Normal query"),
        ("deteksi penyakit jantung", "Normal query"),
        ("machine learning", "Normal query"),
        
        # Typo queries
        ("analisi sentime", "Kata terpotong"),
        ("analisisentime", "Kata digabung"),
        ("analisos sentmn", "Typo ekstrem"),
        ("sistemrekomendasi", "Kata digabung"),
        ("machin lerning", "Common typos"),
    ]
    
    print("\nTesting queries:")
    print("-"*80)
    
    for query, description in test_queries:
        print(f"\n[{description}]")
        print(f"Query: '{query}'")
        print("-" * 60)
        
        results = ranker.search(query, top_k=5, verbose=True)
        print(f"\n>>> Found {len(results)} results")
        
        if results:
            for i, r in enumerate(results[:3], 1):
                print(f"  {i}. [{r['score']:.2f}] {r['title'][:70]}...")
        else:
            print("  ⚠️  WARNING: No results found!")
        
        print()


if __name__ == "__main__":
    main()
