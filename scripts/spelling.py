"""
Ultra-Smart Spell Corrector - FIXED VERSION
============================================
Perbaikan untuk:
1. Repeated chars cleaning dengan exception handling untuk double chars Indonesia
2. Prefix matching yang lebih akurat dengan substring validation
"""

import json
import re
import difflib
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "data/index.json"
DICTIONARY_PATH = "indonesian_wordlist_clean.txt"


class UltraSmartSpellCorrector:
    """
    ULTRA-SMART Spell Corrector dengan:
    - Smart repeated char cleaning (dengan exception untuk double chars Indonesia)
    - Enhanced prefix matching dengan substring validation
    - Multi-stage correction
    """
    
    def __init__(self, vocabulary=None, term_freq=None):
        """Initialize spell corrector"""
        self.vocabulary = vocabulary if vocabulary else set()
        self.term_freq = term_freq if term_freq else {}
        self._cache = {}
        
        # Build valid double chars dari vocabulary
        self.valid_double_chars = self._build_valid_double_chars()
        
        # Indices
        self.prefix_index = defaultdict(set)
        self.substring_index = defaultdict(set)  # NEW: untuk substring matching
        
        # Load dictionary if available
        self._load_dictionary()
        
        # Build indices
        if self.vocabulary:
            self._build_prefix_index()
            self._build_substring_index()
        
        print(f"[UltraSmartSpellCorrector] Vocabulary: {len(self.vocabulary)} kata")
        print(f"[UltraSmartSpellCorrector] Valid double chars: {len(self.valid_double_chars)} patterns")
        print(f"[UltraSmartSpellCorrector] Strategy: Smart cleaning + Substring validation")

    def _load_dictionary(self):
        """Load kamus Indonesia"""
        try:
            dict_path = Path(DICTIONARY_PATH)
            if dict_path.exists():
                with open(dict_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip().lower()
                        if len(word) >= 2:
                            self.vocabulary.add(word)
                            self.term_freq[word] = self.term_freq.get(word, 0) + 10
                print(f"[UltraSmartSpellCorrector] Loaded {len(self.vocabulary)} words from dictionary")
        except Exception as e:
            print(f"[Warning] Gagal load kamus: {e}")

    def _build_valid_double_chars(self):
        """
        Build set of valid double characters dari vocabulary
        
        Contoh: 'gg' dari 'sanggup', 'menggunakan'
                'nn' dari 'perennial', 'pannekuk'
                'll' dari 'ullah', 'balled'
        """
        valid_doubles = set()
        
        for word in self.vocabulary:
            # Find all double chars dalam kata
            for i in range(len(word) - 1):
                if word[i] == word[i+1]:
                    double = word[i] * 2
                    valid_doubles.add(double)
        
        # Selalu include double chars umum dalam bahasa Indonesia
        common_doubles = {'nn', 'mm', 'll', 'ss', 'tt', 'kk', 'pp', 'gg', 'bb', 'dd', 'ff'}
        valid_doubles.update(common_doubles)
        
        return valid_doubles

    def _build_prefix_index(self):
        """Build prefix index untuk autocomplete"""
        for word in self.vocabulary:
            for i in range(2, min(len(word) + 1, 8)):
                prefix = word[:i]
                self.prefix_index[prefix].add(word)

    def _build_substring_index(self):
        """
        Build substring index untuk matching kata yang kurang huruf
        
        Contoh: 'analisi' akan match dengan 'analisis' karena semua huruf ada
        """
        for word in self.vocabulary:
            if len(word) >= 4:
                # Store word by its sorted character signature
                char_sig = ''.join(sorted(word))
                self.substring_index[char_sig].add(word)

    def _smart_clean_repeated_chars(self, text):
        """
        Smart cleaning untuk repeated chars dengan exception handling
        
        Rules:
        1. Valid double chars (gg, nn, ll, etc.) → keep as double
        2. 3+ repeated chars → reduce to 1
        
        Examples:
        - 'deteksiiiiiipenyakiiiiit' → 'deteksipenyakit'
        - 'menggunakan' → 'menggunakan' (gg tetap)
        - 'sanggup' → 'sanggup' (gg tetap)
        - 'sennnntimen' → 'sentimen' (nnn → n)
        """
        text = text.lower()
        result = []
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # Count consecutive same chars
            count = 1
            while i + count < len(text) and text[i + count] == char:
                count += 1
            
            # Decision logic
            if count >= 3:
                # 3+ repeated → reduce to 1
                result.append(char)
            elif count == 2:
                # Check if this double is valid in Indonesian
                double = char * 2
                if double in self.valid_double_chars:
                    result.append(double)
                else:
                    # Not valid double, reduce to 1
                    result.append(char)
            else:
                # Single char
                result.append(char)
            
            i += count
        
        return ''.join(result)

    def _find_substring_match(self, term):
        """
        Find words yang mengandung semua huruf dari term (prefix match lebih akurat)
        
        Contoh: 'analisi' → 'analisis' (semua huruf ada, hanya kurang 's')
        
        Returns:
            (matched_word, confidence)
        """
        if len(term) < 4:
            return term, 0
        
        # Exact match
        if term in self.vocabulary:
            return term, 100
        
        # Strategy 1: Find words that START with term (prefix)
        prefix_candidates = [w for w in self.vocabulary if w.startswith(term)]
        
        if prefix_candidates:
            # Score by length difference and frequency
            scored = []
            for word in prefix_candidates:
                len_diff = len(word) - len(term)
                freq = self.term_freq.get(word, 0)
                
                # Prefer words that are only slightly longer (missing 1-3 chars)
                if len_diff <= 3:
                    score = freq + (100 - len_diff * 10)
                    scored.append((word, score))
            
            if scored:
                best_word = max(scored, key=lambda x: x[1])[0]
                # Validate: check if term is truly a prefix
                if best_word.startswith(term):
                    # Calculate confidence based on how much is missing
                    len_diff = len(best_word) - len(term)
                    confidence = int(95 - (len_diff * 5))  # 95, 90, 85, 80 for 1,2,3,4 missing
                    return best_word, confidence
        
        # Strategy 2: Fuzzy substring (semua huruf term ada di word, urutan sama)
        # Check if all characters of term appear in word in same order
        def is_subsequence(term, word):
            """Check if term is subsequence of word"""
            it = iter(word)
            return all(c in it for c in term)
        
        subseq_candidates = []
        for word in self.vocabulary:
            if len(word) >= len(term) and len(word) <= len(term) + 4:
                if is_subsequence(term, word):
                    len_diff = len(word) - len(term)
                    freq = self.term_freq.get(word, 0)
                    
                    # Check similarity
                    similarity = difflib.SequenceMatcher(None, term, word).ratio()
                    
                    if similarity >= 0.7:
                        score = freq + (similarity * 100) - (len_diff * 5)
                        subseq_candidates.append((word, score, similarity))
        
        if subseq_candidates:
            best_word, best_score, best_sim = max(subseq_candidates, key=lambda x: x[1])
            confidence = int(best_sim * 85)  # Lower confidence than prefix
            return best_word, confidence
        
        return term, 0

    def _extract_from_noise(self, text):
        """Extract valid words dari noise string"""
        if len(text) < 4:
            return []
        
        found_words = []
        
        for word in self.vocabulary:
            if len(word) >= 4 and word in text:
                pos = text.find(word)
                freq = self.term_freq.get(word, 0)
                score = len(word) * 3 + freq / 10
                found_words.append((word, score, pos))
        
        if not found_words:
            return []
        
        found_words.sort(key=lambda x: -x[1])
        
        selected = []
        used_ranges = []
        
        for word, score, start_pos in found_words:
            end_pos = start_pos + len(word)
            
            overlap = False
            for used_start, used_end in used_ranges:
                if not (end_pos <= used_start or start_pos >= used_end):
                    overlap = True
                    break
            
            if not overlap:
                selected.append((word, start_pos))
                used_ranges.append((start_pos, end_pos))
        
        selected.sort(key=lambda x: x[1])
        return [word for word, _ in selected]

    def _greedy_split(self, term):
        """Greedy word segmentation"""
        result = []
        i = 0
        
        while i < len(term):
            longest_match = None
            longest_len = 0
            
            max_scan = min(len(term) - i, 20)
            for length in range(max_scan, 1, -1):
                candidate = term[i:i+length]
                if candidate in self.vocabulary and length > longest_len:
                    longest_match = candidate
                    longest_len = length
                    break
            
            if longest_match:
                result.append(longest_match)
                i += longest_len
            else:
                i += 1
        
        return result

    def _find_fuzzy_match(self, term):
        """Fuzzy matching untuk typo"""
        if len(term) < 3:
            return term, 0
        
        close_matches = difflib.get_close_matches(
            term, 
            list(self.vocabulary), 
            n=15,
            cutoff=0.55
        )
        
        if close_matches:
            scored = []
            for match in close_matches:
                similarity = difflib.SequenceMatcher(None, term, match).ratio()
                freq = self.term_freq.get(match, 0)
                len_diff = abs(len(match) - len(term))
                
                freq_score = min(freq / 500, 1.0)
                score = (similarity * 0.5) + (freq_score * 0.4) - (len_diff * 0.01)
                scored.append((match, score, similarity))
            
            best_match, best_score, best_similarity = max(scored, key=lambda x: x[1])
            confidence = int(best_similarity * 100)
            return best_match, confidence
        
        return term, 0

    def _correct_single_term(self, term):
        """
        Complete correction pipeline - Multi-stage
        
        Stages:
        1. Smart repeated char cleaning (dengan exception double chars)
        2. Exact match
        3. Substring match (PREFIX validation untuk kata kurang huruf)
        4. Extract dari noise
        5. Greedy split
        6. Fuzzy match
        """
        # Stage 1: Smart cleaning
        cleaned = self._smart_clean_repeated_chars(term)
        
        if not cleaned or len(cleaned) < 2:
            return term, 0
        
        # Stage 2: Exact match
        if cleaned in self.vocabulary:
            return cleaned, 100
        
        # Stage 3: PRIORITY - Substring match untuk kata yang kurang huruf
        # Ini akan handle 'analisi' → 'analisis'
        if 4 <= len(cleaned) <= 15:
            substring_match, substring_score = self._find_substring_match(cleaned)
            if substring_score >= 80 and substring_match != cleaned:
                return substring_match, substring_score
        
        # Stage 4: Extract dari noise
        if len(cleaned) >= 8:
            extracted = self._extract_from_noise(cleaned)
            if len(extracted) >= 1:
                total_len = sum(len(w) for w in extracted)
                coverage = total_len / len(cleaned)
                
                if coverage >= 0.25:
                    return " ".join(extracted), 94
        
        # Stage 5: Greedy split
        if len(cleaned) >= 6:
            split_result = self._greedy_split(cleaned)
            
            if len(split_result) >= 2 and all(w in self.vocabulary for w in split_result):
                total_len = sum(len(w) for w in split_result)
                coverage = total_len / len(cleaned)
                
                if coverage >= 0.55:
                    return " ".join(split_result), 92
            
            if len(split_result) == 1 and split_result[0] in self.vocabulary:
                return split_result[0], 95
        
        # Stage 6: Fuzzy match (last resort)
        corrected, score = self._find_fuzzy_match(cleaned)
        if score >= 55:
            return corrected, score
        
        return cleaned, 50

    def correct(self, query_string):
        """Main correction function"""
        query_string = query_string.strip()
        if not query_string:
            return ""
        
        query_string = query_string.lower()
        tokens = query_string.split()
        corrected_tokens = []
        
        for token in tokens:
            # Check cache
            if token in self._cache:
                corrected_tokens.append(self._cache[token])
                continue
            
            # Correct
            corrected, score = self._correct_single_term(token)
            
            if score >= 55:
                self._cache[token] = corrected
                corrected_tokens.append(corrected)
            else:
                # Last resort
                if len(token) >= 4:
                    fuzzy, fuzzy_score = self._find_fuzzy_match(token)
                    if fuzzy_score >= 50 and fuzzy != token:
                        self._cache[token] = fuzzy
                        corrected_tokens.append(fuzzy)
                        continue
                    
                    substring, substring_score = self._find_substring_match(token)
                    if substring_score >= 70 and substring != token:
                        self._cache[token] = substring
                        corrected_tokens.append(substring)
                        continue
                
                self._cache[token] = token
                corrected_tokens.append(token)
        
        return " ".join(corrected_tokens)

    def get_suggestion(self, query_string):
        """Get suggestion dengan confidence"""
        corrected = self.correct(query_string)
        
        if corrected.lower() == query_string.lower():
            return None, 0
        
        return corrected, 85

    def clear_cache(self):
        """Clear correction cache"""
        self._cache.clear()

    def get_stats(self):
        """Get corrector statistics"""
        return {
            'vocabulary_size': len(self.vocabulary),
            'cache_size': len(self._cache),
            'valid_double_chars': len(self.valid_double_chars),
            'substring_index_size': len(self.substring_index)
        }


def test_spell_corrector():
    """Test spell corrector"""
    print("\n" + "="*80)
    print("TESTING ENHANCED SPELL CORRECTOR")
    print("="*80)
    
    try:
        with open(INDEX_PATH, 'r') as f:
            data = json.load(f)
        
        vocabulary = set(data.get('index', {}).keys())
        term_freq = {term: 100 for term in vocabulary}
        
        print(f"Loaded {len(vocabulary)} terms from index\n")
    except:
        print("Warning: Could not load index, using empty vocabulary\n")
        vocabulary = set()
        term_freq = {}
    
    corrector = UltraSmartSpellCorrector(vocabulary=vocabulary, term_freq=term_freq)
    
    test_cases = [
        # FIXED: Heavy repeated chars
        ("deteksiiiiiiiiiiiiiiiipenyakiiiiiiiiiiiiiiiittttttttttt", "Heavy repeated chars"),
        ("sentimennnnnnnn", "Repeated chars"),
        ("analisiiiiis", "Repeated chars"),
        
        # FIXED: Missing chars (prefix matching)
        ("analisi sentime", "Incomplete words"),
        ("analisi", "Missing 's'"),
        ("sentime", "Missing 'n'"),
        ("klasifikas", "Missing 'i'"),
        
        # Word segmentation
        ("analisissentimen", "Compound word"),
        ("pemodelantopik", "Compound word"),
        
        # Valid double chars (should be preserved)
        ("menggunakan", "Valid double 'gg'"),
        ("sanggup", "Valid double 'gg'"),
        ("tanggung", "Valid double 'gg'"),
        
        # Mixed
        ("klasifikasiiiiiii penyakittttt", "Multiple issues"),
    ]
    
    print("\nTest Results:")
    print("-" * 80)
    
    for query, description in test_cases:
        corrected = corrector.correct(query)
        changed = "✓" if corrected != query else "○"
        print(f"{changed} [{description:25s}] '{query:40s}' → '{corrected}'")
    
    print("\n" + "="*80)
    print("Stats:", corrector.get_stats())
    print("="*80)


if __name__ == "__main__":
    test_spell_corrector()
