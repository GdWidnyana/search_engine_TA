# scripts/spelling.py
"""
Enhanced Spell Corrector dengan Intelligent Word Segmentation
- Menggunakan corpus vocabulary + frequency analysis
- Smart DP segmentation dengan multiple scoring factors
- Fallback ke Indonesian common words
"""
import json
from pathlib import Path
from collections import Counter, defaultdict
import re

BASE_DIR = Path(__file__).resolve().parent.parent
KGRAM_PATH = BASE_DIR / "data/kgram.json"
INDEX_PATH = BASE_DIR / "data/index.json"

# Indonesian common words untuk fallback
INDONESIAN_COMMON_WORDS = {
    'dan', 'atau', 'yang', 'dengan', 'untuk', 'pada', 'dari', 'ke', 'oleh', 'di',
    'adalah', 'ini', 'itu', 'akan', 'telah', 'dapat', 'harus', 'bisa', 'sudah',
    'belum', 'tidak', 'ada', 'juga', 'lebih', 'sangat', 'saat', 'setelah', 'sebelum',
    'sistem', 'data', 'hasil', 'metode', 'penelitian', 'analisis', 'model', 'proses',
    'teknik', 'cara', 'informasi', 'pengguna', 'penggunaan', 'aplikasi', 'berbasis'
}

class SpellCorrector:
    def __init__(self, k=3, max_dist=2):
        self.k = k
        self.max_dist = max_dist
        
        # Load k-gram index
        with open(KGRAM_PATH) as f:
            self.kgram_index = json.load(f)
        
        # Build vocabulary dari k-gram index
        self.vocabulary = set()
        for kgram, words in self.kgram_index.items():
            self.vocabulary.update(words)
        
        # Add common Indonesian words
        self.vocabulary.update(INDONESIAN_COMMON_WORDS)
        
        # Load corpus untuk frequency analysis
        self._load_corpus_stats()
        
        # Build word frequency dan bigrams
        self._build_frequency_stats()
        
        # Cache
        self._segment_cache = {}
        self._correction_cache = {}
        
        print(f"[SpellCorrector] Loaded {len(self.vocabulary)} terms")
        print(f"[SpellCorrector] Bigram pairs: {len(self.common_bigrams)}")

    def _load_corpus_stats(self):
        """Load corpus statistics dari index"""
        try:
            with open(INDEX_PATH) as f:
                data = json.load(f)
            
            # Extract term frequencies dari index
            self.term_freq = {}
            for term, postings in data.get('index', {}).items():
                if isinstance(postings, dict):
                    self.term_freq[term] = len(postings)
                elif isinstance(postings, list):
                    self.term_freq[term] = len(set(postings))
            
            # Extract dari title dan keyword index juga
            for term, postings in data.get('title_index', {}).items():
                freq = len(postings) if isinstance(postings, dict) else len(set(postings))
                self.term_freq[term] = self.term_freq.get(term, 0) + freq * 2  # Boost title
            
            for term, postings in data.get('keyword_index', {}).items():
                freq = len(postings) if isinstance(postings, dict) else len(set(postings))
                self.term_freq[term] = self.term_freq.get(term, 0) + freq * 3  # Boost keyword
            
            print(f"[SpellCorrector] Term frequencies: {len(self.term_freq)} unique terms")
            
        except Exception as e:
            print(f"[SpellCorrector] Warning: Could not load corpus stats: {e}")
            self.term_freq = {}

    def _build_frequency_stats(self):
        """Build bigram frequency dari corpus"""
        self.common_bigrams = defaultdict(int)
        
        # Known domain-specific bigrams dengan frequency tinggi
        known_bigrams = {
            ('machine', 'learning'): 1000,
            ('deep', 'learning'): 800,
            ('neural', 'network'): 700,
            ('user', 'interface'): 600,
            ('natural', 'language'): 600,
            ('data', 'mining'): 500,
            ('text', 'mining'): 500,
            ('sentiment', 'analysis'): 450,
            ('topic', 'modeling'): 400,
            ('recommender', 'system'): 350,
            ('business', 'intelligence'): 300,
            ('information', 'retrieval'): 300,
            ('sistem', 'rekomendasi'): 500,
            ('analisis', 'sentimen'): 600,
            ('pemodelan', 'topik'): 400,
            ('penggalian', 'data'): 350,
            ('pembelajaran', 'mesin'): 450,
            ('jaringan', 'saraf'): 300,
            ('jaringan', 'syaraf'): 300,
            ('kecerdasan', 'buatan'): 350,
            ('pengolahan', 'bahasa'): 300,
            ('bahasa', 'alami'): 300,
            ('klasifikasi', 'teks'): 250,
            ('peringkasan', 'teks'): 200,
        }
        
        self.common_bigrams.update(known_bigrams)
        
        # Add reverse pairs dengan frequency lebih rendah
        for (w1, w2), freq in list(known_bigrams.items()):
            self.common_bigrams[(w2, w1)] = freq // 2

    def _get_word_frequency(self, word):
        """Get frequency of word dalam corpus"""
        return self.term_freq.get(word, 0)

    def _kgrams(self, word):
        word = f"${word}$"
        return [word[i:i+self.k] for i in range(len(word)-self.k+1)]

    def edit_distance(self, a, b):
        """Optimized edit distance with early termination"""
        if abs(len(a) - len(b)) > self.max_dist:
            return self.max_dist + 1
            
        dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
        for i in range(len(a)+1):
            dp[i][0] = i
        for j in range(len(b)+1):
            dp[0][j] = j

        for i in range(1, len(a)+1):
            min_val = float('inf')
            for j in range(1, len(b)+1):
                cost = 0 if a[i-1] == b[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,
                    dp[i][j-1] + 1,
                    dp[i-1][j-1] + cost
                )
                min_val = min(min_val, dp[i][j])
            
            if min_val > self.max_dist:
                return self.max_dist + 1
        
        return dp[-1][-1]

    def _score_segmentation(self, segments, original_term):
        """
        Score segmentation quality dengan multiple factors:
        1. Word frequency dalam corpus
        2. Bigram likelihood
        3. Length compatibility
        4. Edit distance dari original
        """
        score = 0.0
        
        # Factor 1: Semua words harus ada di vocabulary
        for word in segments:
            if word not in self.vocabulary:
                return -1000  # Invalid
        
        # Factor 2: Word frequency (lebih tinggi = lebih baik)
        freq_score = sum(self._get_word_frequency(w) for w in segments)
        score += freq_score * 10  # Weight frequency
        
        # Factor 3: Bigram score (jika ada)
        bigram_score = 0
        for i in range(len(segments) - 1):
            bigram = (segments[i], segments[i+1])
            if bigram in self.common_bigrams:
                bigram_score += self.common_bigrams[bigram]
        score += bigram_score * 50  # Heavy weight untuk known bigrams
        
        # Factor 4: Length compatibility
        total_len = sum(len(w) for w in segments)
        len_diff = abs(total_len - len(original_term))
        score -= len_diff * 100  # Penalize length mismatch
        
        # Factor 5: Prefer fewer segments (simplicity)
        score -= len(segments) * 50
        
        # Factor 6: Avoid very short words (kecuali common)
        for word in segments:
            if len(word) < 3 and word not in INDONESIAN_COMMON_WORDS:
                score -= 200
        
        # Factor 7: Check substring overlap dengan original
        overlap_score = 0
        temp_original = original_term.lower()
        for word in segments:
            if word in temp_original:
                overlap_score += len(word) * 20
        score += overlap_score
        
        return score

    def _segment_word_smart(self, term):
        """
        Smart DP segmentation dengan scoring yang comprehensive
        """
        n = len(term)
        
        # dp[i] = (best_score, best_segmentation)
        dp = [(-float('inf'), [])] * (n + 1)
        dp[0] = (0, [])
        
        for i in range(1, n + 1):
            # Try all possible last word lengths
            for j in range(max(0, i - 25), i):  # Max word length 25
                candidate = term[j:i]
                
                # Skip terlalu pendek
                if len(candidate) < 3:
                    continue
                
                # Must be in vocabulary (dengan fuzzy matching untuk typo)
                if candidate not in self.vocabulary:
                    # Try fuzzy match untuk typo
                    corrected = self._find_best_match(candidate)
                    if corrected == candidate:  # No good match
                        continue
                    candidate = corrected
                
                # Calculate score untuk segmentation ini
                new_segments = dp[j][1] + [candidate]
                new_score = self._score_segmentation(new_segments, term)
                
                if new_score > dp[i][0]:
                    dp[i] = (new_score, new_segments)
        
        best_score, best_segments = dp[n]
        
        # Only accept if score is positive (valid)
        if best_score > 0 and best_segments:
            return best_segments
        
        return None

    def _segment_word_greedy_smart(self, term):
        """
        Greedy segmentation dengan priority ke high-frequency words
        """
        result = []
        i = 0
        n = len(term)
        
        while i < n:
            best_match = None
            best_score = -float('inf')
            
            # Try dari panjang maksimal ke minimal
            for length in range(min(25, n - i), 2, -1):
                candidate = term[i:i+length]
                
                if candidate not in self.vocabulary:
                    continue
                
                # Score kandidat ini
                freq = self._get_word_frequency(candidate)
                
                # Bonus jika membentuk bigram dengan kata sebelumnya
                bigram_bonus = 0
                if result:
                    bigram = (result[-1], candidate)
                    if bigram in self.common_bigrams:
                        bigram_bonus = self.common_bigrams[bigram] * 10
                
                candidate_score = freq + bigram_bonus
                
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_match = (candidate, length)
            
            if best_match:
                result.append(best_match[0])
                i += best_match[1]
            else:
                # Tidak bisa segment, gagal
                return None
        
        # Validate hasil
        if result and len(result) >= 2:
            score = self._score_segmentation(result, term)
            if score > 0:
                return result
        
        return None

    def _find_best_match(self, term):
        """Mencari kata terbaik dari vocabulary"""
        if term in self._correction_cache:
            return self._correction_cache[term]
        
        if len(term) < 3:
            return term
            
        grams = self._kgrams(term)
        candidates = Counter()

        for g in grams:
            if g in self.kgram_index:
                for cand in self.kgram_index[g]:
                    candidates[cand] += 1

        if not candidates:
            return term

        scored = []
        for cand, overlap in candidates.most_common(100):
            if abs(len(cand) - len(term)) > 3:
                continue
                
            dist = self.edit_distance(term, cand)
            if dist <= self.max_dist:
                freq = self._get_word_frequency(cand)
                scored.append((cand, dist, overlap, freq))

        if not scored:
            return term

        # Ranking: edit distance â†' frequency â†' overlap
        scored.sort(key=lambda x: (x[1], -x[3], -x[2]))
        result = scored[0][0]
        
        self._correction_cache[term] = result
        return result

    def correct(self, term):
        """
        Enhanced correction dengan intelligent segmentation
        
        Strategy:
        1. Exact match â†' return immediately
        2. Coba spelling correction untuk kata normal
        3. Smart segmentation untuk kata panjang atau compound
        """
        # 1. Exact match
        if term in self.vocabulary:
            return term
        
        # 2. Check cache
        if term in self._segment_cache:
            cached = self._segment_cache[term]
            return cached if cached else term
        
        # 3. Untuk kata pendek-medium, coba spelling correction
        if len(term) <= 10:
            corrected = self._find_best_match(term)
            if corrected != term and corrected in self.vocabulary:
                dist = self.edit_distance(term, corrected)
                if dist <= 2:
                    self._segment_cache[term] = corrected
                    return corrected
        
        # 4. Word segmentation untuk kata panjang (>10 chars)
        if len(term) > 10:
            # Try greedy first (faster)
            segments = self._segment_word_greedy_smart(term)
            
            if not segments:
                # Try DP (more accurate but slower)
                segments = self._segment_word_smart(term)
            
            if segments and len(segments) >= 2:
                result = ' '.join(segments)
                self._segment_cache[term] = result
                return result
        
        # 5. Fallback untuk kata medium length (7-10 chars)
        # Mungkin compound word yang pendek
        if 7 <= len(term) <= 10:
            segments = self._segment_word_smart(term)
            if segments and len(segments) == 2:
                result = ' '.join(segments)
                self._segment_cache[term] = result
                return result
        
        # 6. Last resort: spelling correction
        corrected = self._find_best_match(term)
        self._segment_cache[term] = corrected if corrected != term else None
        return corrected


# Test function
def test_segmentation():
    """Test segmentation dengan various cases"""
    corrector = SpellCorrector()
    
    test_cases = [
        "pemodelantopik",
        "pemodelantopikberita",
        "analisissentimen",
        "machinelearning",
        "deeplearning",
        "sistemrekomendasi",
        "pengolahanbahasa",
        "jaringansyaraf",
        "klasifikasiteks",
        "penggaliandata",
    ]
    
    print("\n" + "="*80)
    print("TESTING WORD SEGMENTATION")
    print("="*80)
    
    for test in test_cases:
        result = corrector.correct(test)
        print(f"\n'{test}' â†' '{result}'")
        
        if ' ' in result:
            segments = result.split()
            print(f"  Segments: {segments}")
            print(f"  Valid: {all(s in corrector.vocabulary for s in segments)}")


if __name__ == "__main__":
    test_segmentation()
