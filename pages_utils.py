"""
Utility functions for pages (Favorites, Analytics, etc.)
"""

import json
from pathlib import Path
from config import BASE_DIR

# Favorites file path
FAVORITES_PATH = BASE_DIR / "data/favorites.json"


def load_favorites():
    """Load favorites from file"""
    if FAVORITES_PATH.exists():
        try:
            with open(FAVORITES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_favorites_func(favorites):
    """Save favorites to file"""
    try:
        FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FAVORITES_PATH, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving favorites: {e}")
        return False


def add_links_to_favorites():
    """Add link_pdf and link_detail to existing favorites"""
    from detail_utils import load_corpus_data
    
    favorites = load_favorites()
    if not favorites:
        return favorites
    
    corpus_data = load_corpus_data()
    if not corpus_data:
        return favorites
    
    # Create mapping from doc_id to corpus document
    corpus_map = {doc.get('doc_id'): doc for doc in corpus_data}
    
    # Update favorites with links
    updated_favorites = []
    for fav in favorites:
        doc_id = fav.get('doc_id')
        if doc_id in corpus_map:
            corpus_doc = corpus_map[doc_id]
            # Add links if not already present
            if 'link_pdf' not in fav:
                fav['link_pdf'] = corpus_doc.get('link_pdf', corpus_doc.get('fields', {}).get('Link PDF', ''))
            if 'link_detail' not in fav:
                fav['link_detail'] = corpus_doc.get('link_detail', corpus_doc.get('fields', {}).get('Link Detail', ''))
        updated_favorites.append(fav)
    
    # Save updated favorites
    save_favorites_func(updated_favorites)
    return updated_favorites