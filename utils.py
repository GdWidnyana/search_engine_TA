"""
Utility functions for the Search Engine
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import hashlib

from config import HISTORY_PATH, BASE_DIR


def load_search_history() -> List[Dict[str, Any]]:
    """Load search history from file"""
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_search_history(history: List[Dict[str, Any]]) -> bool:
    """Save search history to file"""
    try:
        HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving history: {e}")
        return False


def get_search_stats(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate search statistics"""
    if not history:
        return {
            'total_searches': 0,
            'unique_queries': 0,
            'avg_results': 0,
            'today_searches': 0,
            'avg_search_time': 0,
            'top_queries': []
        }
    
    today = datetime.now().date()
    queries = [entry['query'] for entry in history]
    results = [entry.get('num_results', 0) for entry in history]
    search_times = [entry.get('search_time', 0) for entry in history]
    
    # Count query frequency
    from collections import Counter
    query_counter = Counter(queries)
    
    return {
        'total_searches': len(history),
        'unique_queries': len(set(queries)),
        'avg_results': sum(results) / len(results) if results else 0,
        'avg_search_time': sum(search_times) / len(search_times) if search_times else 0,
        'today_searches': sum(1 for entry in history 
                             if datetime.fromisoformat(entry['timestamp']).date() == today),
        'top_queries': query_counter.most_common(10)
    }


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format"""
    try:
        # Parse timestamp
        dt = datetime.fromisoformat(iso_timestamp)
        
        # Remove any timezone info
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        
        now = datetime.now()
        
        # If today
        if dt.date() == now.date():
            return f"Hari ini {dt.strftime('%H:%M')}"
        
        # If yesterday
        yesterday = now.date() - timedelta(days=1)
        if dt.date() == yesterday:
            return f"Kemarin {dt.strftime('%H:%M')}"
        
        # Within this year
        if dt.year == now.year:
            return dt.strftime("%d %b %H:%M")
        
        return dt.strftime("%d %b %Y")
    except Exception as e:
        print(f"Error formatting timestamp: {e}")
        return iso_timestamp

def get_current_time_for_display() -> datetime:
    """Get current time for display (uses server time as local time)"""
    return datetime.now()


def generate_doc_id(title: str, author: str) -> str:
    """Generate unique document ID"""
    content = f"{title}_{author}".encode('utf-8')
    return hashlib.md5(content).hexdigest()[:8]


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + "..."


def get_domain_color(domain: str) -> str:
    """Get color for domain badge"""
    colors = {
        'ml_ai': '#667eea',
        'nlp': '#4c51bf',
        'security': '#e53e3e',
        'ui_ux': '#d69e2e',
        'recommender': '#38a169',
        'medical': '#319795',
        'iot': '#805ad5',
        'business': '#d53f8c',
        'mobile': '#dd6b20',
        'general': '#718096'
    }
    return colors.get(domain, '#718096')


def calculate_relevance_score(score: float) -> str:
    """Convert numerical score to relevance label"""
    if score >= 0.8:
        return "Sangat Relevan"
    elif score >= 0.6:
        return "Relevan"
    elif score >= 0.4:
        return "Cukup Relevan"
    else:
        return "Kurang Relevan"


def export_to_json(data: List[Dict], filename: str) -> str:
    """Export data to JSON file"""
    output_path = BASE_DIR / "exports" / f"{filename}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return str(output_path)


def export_to_csv(data: List[Dict], filename: str) -> str:
    """Export data to CSV file"""
    import csv
    
    output_path = BASE_DIR / "exports" / f"{filename}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not data:
        return ""
    
    # Get all possible keys
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
        writer.writeheader()
        writer.writerows(data)
    
    return str(output_path)

def get_current_wib_datetime() -> datetime:
    """
    Get current datetime in WIB (UTC+7) regardless of server timezone
    """
    # Always get UTC time and add 7 hours for WIB
    utc_now = datetime.now(timezone.utc)
    wib_now = utc_now + timedelta(hours=7)
    return wib_now

def add_search_to_history(query: str, num_results: int, search_time: float):
    """Add search to history - Always save as WIB time string"""
    history = load_search_history()
    
    # Save as simple WIB time string
    timestamp = get_current_wib_datetime().strftime('%Y-%m-%d %H:%M:%S')
    
    history.insert(0, {
        'timestamp': timestamp,
        'query': query,
        'num_results': num_results,
        'search_time': search_time
    })
    
    if len(history) > 100:
        history = history[:100]
    
    save_search_history(history)
    return True

def save_favorite_document(doc_data: dict):
    """Save document to favorites - Always save as WIB time string"""
    favorites = load_favorites()
    
    # Check if already exists
    for fav in favorites:
        if fav.get('doc_id') == doc_data.get('doc_id'):
            return False
    
    # Save as WIB time string
    doc_data['saved_at'] = get_current_wib_datetime().strftime('%Y-%m-%d %H:%M:%S')
    favorites.append(doc_data)
    
    save_favorites_func(favorites)
    return True

def parse_timestamp_to_wib(timestamp_str: str) -> datetime:
    """
    Parse timestamp string and ensure it's in WIB time
    
    Handles multiple formats:
    1. '2025-12-26 10:36:12' (simple format - assume WIB)
    2. '2025-12-26T03:36:12Z' (ISO UTC - convert to WIB)
    3. '2025-12-26T10:36:12+07:00' (ISO with offset)
    """
    try:
        # Format 1: Simple string '2025-12-26 10:36:12'
        if 'T' not in timestamp_str and 'Z' not in timestamp_str:
            # Parse as WIB time directly
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        
        # Format 2: ISO with UTC '2025-12-26T03:36:12Z'
        elif 'Z' in timestamp_str:
            # Parse as UTC
            dt_utc = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Convert to WIB (UTC+7)
            return dt_utc + timedelta(hours=7)
        
        # Format 3: ISO with offset '2025-12-26T10:36:12+07:00'
        else:
            # Parse with timezone info
            dt = datetime.fromisoformat(timestamp_str)
            # If it has timezone info, convert to naive WIB
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None) - dt.utcoffset() + timedelta(hours=7)
            return dt
            
    except Exception as e:
        print(f"Error parsing timestamp '{timestamp_str}': {e}")
        # Fallback to current WIB time
        return get_current_wib_datetime()

def format_datetime_for_display(dt: datetime, format_type: str = 'full') -> str:
    """
    Format datetime for display in user-friendly format
    """
    if format_type == 'full':
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    elif format_type == 'date_time':
        return dt.strftime('%d/%m/%Y %H:%M')
    elif format_type == 'date':
        return dt.strftime('%d/%m/%Y')
    elif format_type == 'time':
        return dt.strftime('%H:%M:%S')
    elif format_type == 'relative':
        now_wib = get_current_wib_datetime()
        
        if dt.date() == now_wib.date():
            return f"Hari ini {dt.strftime('%H:%M')}"
        
        yesterday = now_wib.date() - timedelta(days=1)
        if dt.date() == yesterday:
            return f"Kemarin {dt.strftime('%H:%M')}"
        
        if dt.year == now_wib.year:
            return dt.strftime("%d %b %H:%M")
        
        return dt.strftime("%d %b %Y")
    else:
        return dt.strftime('%d/%m/%Y %H:%M')

# Fungsi bantu untuk debugging
def debug_timestamp_info(timestamp_str: str):
    """Debug function to show timestamp conversion info"""
    print(f"\n=== DEBUG TIMESTAMP ===")
    print(f"Original string: {timestamp_str}")
    
    try:
        dt_parsed = parse_timestamp_to_wib(timestamp_str)
        print(f"Parsed as WIB: {dt_parsed}")
        print(f"Formatted: {format_datetime_for_display(dt_parsed, 'date_time')}")
        
        # Show current times for comparison
        print(f"\nCurrent UTC: {datetime.now(timezone.utc)}")
        print(f"Current WIB: {get_current_wib_datetime()}")
        print(f"Current Server: {datetime.now()}")
    except Exception as e:
        print(f"Error: {e}")
    print("=====================\n")
                
def validate_email(email: str) -> bool:
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def clean_query(query: str) -> str:
    """Clean and normalize search query"""
    import re
    
    # Remove extra spaces
    query = re.sub(r'\s+', ' ', query).strip()
    
    # Remove special characters but keep Indonesian characters
    query = re.sub(r'[^\w\sà-ÿÀ-ßĀ-žąćęłńóśźżĄĆĘŁŃÓŚŹŻ\-\']', ' ', query)
    
    # Lowercase
    query = query.lower()
    
    return query


def get_file_size(filepath: Path) -> str:
    """Get human readable file size"""
    try:
        size = filepath.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except:
        return "0 B"

def parse_keywords(keywords_str: str):
    """Parse keywords string into list, supporting multiple separators"""
    if not keywords_str:
        return []
    
    # Bersihkan string
    keywords_str = keywords_str.strip()
    
    # First, try to split by semicolon if present
    if ';' in keywords_str:
        keywords = []
        for kw in keywords_str.split(';'):
            kw = kw.strip()
            if kw and ',' in kw:
                # If comma also exists, split by comma
                sub_keywords = [sub.strip() for sub in kw.split(',') if sub.strip()]
                keywords.extend(sub_keywords)
            elif kw:
                keywords.append(kw)
    elif ',' in keywords_str:
        # If only comma, split by comma
        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
    else:
        # If no separators, split by space (traditional)
        keywords = [kw.strip() for kw in keywords_str.split() if kw.strip()]
    
    # Hapus duplikat dan kosong
    keywords = [kw for kw in keywords if kw]
    return list(dict.fromkeys(keywords)) 

def reset_all_data():
    """Reset search_history.json and favorites.json to empty arrays"""
    import json
    
    try:
        # Reset search history
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        
        # Reset favorites
        from pages_utils import FAVORITES_PATH
        if FAVORITES_PATH.exists():
            with open(FAVORITES_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting data: {e}")
        return False
    
def create_index_summary(index_path: Path) -> Dict[str, Any]:
    """Create summary of index file - PERBAIKAN: Baca dari corpus.json jika index.json kosong"""
    try:
        # Coba baca dari index.json dulu
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Cek struktur data
            if isinstance(data, dict) and 'documents' in data:
                total_docs = len(data.get('documents', []))
            elif isinstance(data, list):
                total_docs = len(data)
            else:
                total_docs = 0
            
            if total_docs > 0:
                # Hitung dari index.json
                if isinstance(data, dict) and 'documents' in data:
                    documents = data.get('documents', [])
                else:
                    documents = data if isinstance(data, list) else []
                
                # Count by domain
                domains = {}
                total_keywords = 0
                
                for doc in documents:
                    domain = doc.get('domain', 'general')
                    domains[domain] = domains.get(domain, 0) + 1
                    
                    # Count keywords
                    keywords = doc.get('keywords', '')
                    if keywords:
                        total_keywords += len(keywords.split())
                
                # Average keywords per doc
                avg_keywords = total_keywords / total_docs if total_docs > 0 else 0
                
                return {
                    'total_documents': total_docs,
                    'total_keywords': total_keywords,
                    'avg_keywords_per_doc': avg_keywords,
                    'domains': domains,
                    'file_size': get_file_size(index_path),
                    'last_modified': datetime.fromtimestamp(index_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                }
        
        # Jika index.json tidak ada atau kosong, coba baca dari corpus.json
        corpus_path = index_path.parent / "corpus.json"
        if corpus_path.exists():
            with open(corpus_path, 'r', encoding='utf-8') as f:
                corpus_data = json.load(f)
            
            if isinstance(corpus_data, list):
                total_docs = len(corpus_data)
                
                # Count by domain
                domains = {}
                total_keywords = 0
                
                for doc in corpus_data:
                    domain = doc.get('domain', 'general')
                    domains[domain] = domains.get(domain, 0) + 1
                    
                    # Count keywords
                    keywords = doc.get('keywords', '')
                    if keywords:
                        total_keywords += len(keywords.split())
                
                # Average keywords per doc
                avg_keywords = total_keywords / total_docs if total_docs > 0 else 0
                
                return {
                    'total_documents': total_docs,
                    'total_keywords': total_keywords,
                    'avg_keywords_per_doc': avg_keywords,
                    'domains': domains,
                    'file_size': get_file_size(corpus_path),
                    'last_modified': datetime.fromtimestamp(corpus_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                }
        
        # Jika kedua file tidak ada atau kosong
        return {
            'total_documents': 0,
            'total_keywords': 0,
            'avg_keywords_per_doc': 0,
            'domains': {},
            'file_size': '0 B',
            'last_modified': 'N/A'
        }
        
    except Exception as e:
        print(f"Error reading index/corpus: {e}")
        # Return default values
        return {
            'total_documents': 0,
            'total_keywords': 0,
            'avg_keywords_per_doc': 0,
            'domains': {},
            'file_size': '0 B',
            'last_modified': 'N/A'
        }
