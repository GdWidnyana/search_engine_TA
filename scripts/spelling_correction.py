"""
Spelling Correction using Edit Distance (Levenshtein Distance)

Untuk handle typos seperti:
- "pencaruan" → "pencarian"
- "aplikas" → "aplikasi"
- "machin" → "machine"
"""
#spelling_correction.py
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data/index.json"


def edit_distance(s1, s2):
    """
    Calculate Levenshtein distance between two strings
    
    Returns: integer distance (lower = more similar)
    """
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


class SpellingCorrector:
    """
    Spelling correction using edit distance + prefix matching
    """
    
    def __init__(self, index_path):
        """Load vocabulary from index"""
        with open(index_path, 'r') as f:
            data = json.load(f)
        
        self.vocabulary = set(data['index'].keys())
        
        # Build frequency map (for better suggestions)
        self.term_freq = {}
        for term, postings in data['index'].items():
            self.term_freq[term] = len(postings)
        
        # Build prefix index for fast prefix matching
        self.prefix_index = {}
        for term in self.vocabulary:
            for i in range(1, min(len(term) + 1, 8)):  # Prefix up to 7 chars
                prefix = term[:i]
                if prefix not in self.prefix_index:
                    self.prefix_index[prefix] = set()
                self.prefix_index[prefix].add(term)
        
        print(f"SpellingCorrector initialized with {len(self.vocabulary)} terms")
    
    def suggest_with_prefix(self, word, max_suggestions=3):
        """
        Suggest completions for partial word using prefix matching
        Better for incomplete queries like "pencar" → "pencarian"
        """
        if word in self.vocabulary:
            return [(word, 0, self.term_freq.get(word, 0))]
        
        # Find all terms with this prefix
        candidates = []
        
        if word in self.prefix_index:
            for vocab_term in self.prefix_index[word]:
                freq = self.term_freq.get(vocab_term, 0)
                # Distance = remaining characters
                distance = len(vocab_term) - len(word)
                candidates.append((vocab_term, distance, freq))
        
        if not candidates:
            return []
        
        # Sort by frequency (higher is better), then by distance (shorter is better)
        candidates.sort(key=lambda x: (-x[2], x[1]))
        
        return candidates[:max_suggestions]
    
    def suggest(self, word, max_suggestions=3, max_distance=2):
        """
        Suggest corrections for a potentially misspelled word
        
        Args:
            word: potentially misspelled word
            max_suggestions: maximum number of suggestions
            max_distance: maximum edit distance to consider
        
        Returns:
            List of (corrected_word, distance, frequency) tuples
        """
        # If word already in vocabulary, no correction needed
        if word in self.vocabulary:
            return [(word, 0, self.term_freq.get(word, 0))]
        
        # First, try prefix matching (better for incomplete words)
        prefix_candidates = self.suggest_with_prefix(word, max_suggestions=5)
        
        # Calculate edit distance to all vocabulary terms
        edit_candidates = []
        
        for vocab_term in self.vocabulary:
            # Skip if length difference is too large (optimization)
            if abs(len(vocab_term) - len(word)) > max_distance:
                continue
            
            distance = edit_distance(word, vocab_term)
            
            if distance <= max_distance:
                freq = self.term_freq.get(vocab_term, 0)
                edit_candidates.append((vocab_term, distance, freq))
        
        # Combine and deduplicate
        all_candidates = []
        seen = set()
        
        # Prioritize prefix matches (they're usually better for incomplete words)
        for term, dist, freq in prefix_candidates:
            if term not in seen:
                # Give bonus score to prefix matches
                all_candidates.append((term, dist * 0.5, freq))  # Halve distance for prefix matches
                seen.add(term)
        
        # Add edit distance matches
        for term, dist, freq in edit_candidates:
            if term not in seen:
                all_candidates.append((term, dist, freq))
                seen.add(term)
        
        if not all_candidates:
            return []
        
        # Sort by:
        # 1. Edit distance (lower is better)
        # 2. Frequency (higher is better)
        all_candidates.sort(key=lambda x: (x[1], -x[2]))
        
        return all_candidates[:max_suggestions]
    
    def correct_query(self, query_terms, context_terms=None, max_distance=2, auto_correct=True):
        """
        Correct multiple query terms with context awareness
        
        Args:
            query_terms: list of query terms
            context_terms: terms that appear together (for context)
            max_distance: maximum edit distance
            auto_correct: if True, auto-apply best correction
        
        Returns:
            If auto_correct=True: list of corrected terms
            If auto_correct=False: dict of {term: suggestions}
        """
        if auto_correct:
            corrected = []
            for i, term in enumerate(query_terms):
                # Get context (other terms in query)
                other_terms = [t for j, t in enumerate(query_terms) if j != i]
                
                suggestions = self.suggest(term, max_suggestions=5, max_distance=max_distance)
                
                if suggestions:
                    # Context-aware selection
                    best = suggestions[0]
                    
                    # If multiple suggestions with similar scores, prefer longer/more specific
                    if len(suggestions) > 1:
                        # Check for common co-occurrences
                        for sugg_term, dist, freq in suggestions[:3]:
                            # Prefer terms that make sense in context
                            # e.g., for "sistem pencar", prefer "pencarian" over "pencari"
                            if dist <= 1 and len(sugg_term) > len(best[0]):
                                # Longer term is often more complete
                                best = (sugg_term, dist, freq)
                                break
                    
                    corrected.append(best[0])
                else:
                    # No suggestion, keep original
                    corrected.append(term)
            
            return corrected
        else:
            suggestions_map = {}
            for term in query_terms:
                if term not in self.vocabulary:
                    suggestions = self.suggest(term, max_suggestions=3, max_distance=max_distance)
                    if suggestions:
                        suggestions_map[term] = suggestions
            return suggestions_map


def test_spelling_correction():
    """Test spelling correction"""
    if not INDEX_PATH.exists():
        print(f"[ERROR] Index not found: {INDEX_PATH}")
        return
    
    corrector = SpellingCorrector(INDEX_PATH)
    
    print("="*80)
    print("SPELLING CORRECTION TEST")
    print("="*80)
    
    # Test cases
    test_words = [
        "pencaruan",   # Should suggest "pencarian"
        "aplikas",     # Should suggest "aplikasi"
        "machin",      # Should suggest "machine"
        "learnnig",    # Should suggest "learning"
        "klasifkasi",  # Should suggest "klasifikasi"
        "sistem",      # Already correct, no suggestion
        "ontolgi",     # Should suggest "ontologi"
        "rekomdasi",   # Should suggest "rekomendasi"
    ]
    
    print("\nIndividual word corrections:")
    print("-"*80)
    
    for word in test_words:
        suggestions = corrector.suggest(word, max_suggestions=3, max_distance=2)
        
        print(f"\nWord: '{word}'")
        if suggestions and suggestions[0][1] == 0:
            print(f"  ✓ Already correct")
        elif suggestions:
            print(f"  Suggestions:")
            for term, dist, freq in suggestions:
                print(f"    - '{term}' (distance={dist}, freq={freq})")
        else:
            print(f"  ✗ No suggestions found")
    
    # Test query correction
    print("\n" + "="*80)
    print("QUERY CORRECTION TEST")
    print("="*80)
    
    test_queries = [
        "sistem pencaruan",
        "machin learnnig",
        "aplikas mobile",
        "klasifkasi penyakit",
        "user interfce"
    ]
    
    for query in test_queries:
        terms = query.split()
        
        print(f"\nOriginal query: '{query}'")
        print(f"  Terms: {terms}")
        
        # Auto-correct
        corrected_terms = corrector.correct_query(terms, auto_correct=True)
        corrected_query = ' '.join(corrected_terms)
        
        print(f"  Corrected: '{corrected_query}'")
        
        # Show suggestions
        suggestions_map = corrector.correct_query(terms, auto_correct=False)
        if suggestions_map:
            print(f"  Suggestions:")
            for term, suggestions in suggestions_map.items():
                print(f"    '{term}' → {[s[0] for s in suggestions]}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    test_spelling_correction()