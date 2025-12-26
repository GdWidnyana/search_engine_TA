# build_corpus.py
import pandas as pd
import re
import json
import chardet
from pathlib import Path

# Path configuration
RAW_DATA_PATH = Path("C:/Users/Widnyana/Documents/TUGAS AKHIR/Program TA/streamlit_ir/data/skripsi_raw.csv")
OUTPUT_DIR = Path("C:/Users/Widnyana/Documents/TUGAS AKHIR/Program TA/streamlit_ir/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "corpus.json"

# Prioritize important fields
FIELD_WEIGHTS = {
    "Title": 5.0,      # Title sangat penting
    "Keywords": 4.0,   # Keywords juga penting
    "Abstract": 3.0,   # Abstract memberikan overview
    "BAB 1": 2.0,      # Pendahuluan
    "BAB 2": 1.5,      # Tinjauan pustaka
    "BAB 3": 1.0,      # Metodologi
    "BAB 4": 1.0,      # Hasil
    "BAB 5": 1.0,      # Kesimpulan
    "Authors": 0.5,
    "Advisors": 0.5
}

def detect_encoding(filepath):
    """Deteksi encoding file"""
    with open(filepath, 'rb') as f:
        raw_data = f.read(10000)
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        print(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")
        return encoding

def smart_preprocess(text, aggressive=False):
    """
    Preprocessing yang lebih cerdas - tidak terlalu agresif
    aggressive=False untuk Title/Keywords, True untuk body text
    """
    if pd.isna(text):
        return ""
    
    text = str(text)
    
    # Fix encoding issues
    try:
        text = text.encode('utf-8', 'ignore').decode('utf-8')
    except:
        text = text.encode('latin-1', 'ignore').decode('latin-1')
    
    # Lowercase
    text = text.lower()
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    if aggressive:
        # Untuk body text: hapus stopwords
        stopwords_id = {
            'yang', 'dan', 'di', 'dengan', 'untuk', 'pada', 'dari', 
            'dalam', 'ini', 'itu', 'atau', 'juga', 'dapat', 'akan',
            'ada', 'adalah', 'ke', 'oleh', 'sebagai', 'tersebut',
            'karena', 'namun', 'tetapi', 'sehingga', 'maka', 'bagi'
        }
        
        # Simpan alphanumeric dan underscore
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        words = [w for w in words if w not in stopwords_id and len(w) > 2]
        return ' '.join(words).strip()
    else:
        # Untuk Title/Keywords: preprocessing minimal
        # Hapus karakter khusus tapi simpan kata-kata penting
        text = re.sub(r'[^\w\s-]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        words = text.split()
        # Hanya hapus kata sangat pendek (1 karakter)
        words = [w for w in words if len(w) > 1]
        return ' '.join(words).strip()

def extract_fields(row, columns):
    """Extract dan preprocess fields dengan prioritas berbeda"""
    fields = {}
    
    for col in columns:
        if col not in row or pd.isna(row[col]):
            fields[col] = ""
            continue
        
        # Preprocessing berbeda untuk field berbeda
        if col in ['Title', 'Keywords']:
            # Minimal preprocessing untuk title dan keywords
            fields[col] = smart_preprocess(row[col], aggressive=False)
        else:
            # Preprocessing lebih agresif untuk body text
            fields[col] = smart_preprocess(row[col], aggressive=True)
    
    return fields

def build_weighted_text(fields):
    """Gabungkan field dengan bobot"""
    weighted_parts = []
    
    for field, text in fields.items():
        if not text or field not in FIELD_WEIGHTS:
            continue
        
        weight = FIELD_WEIGHTS[field]
        # Repeat text berdasarkan bobot (approach sederhana tapi efektif)
        # Untuk weight 5.0, text muncul 5x
        repetitions = int(weight)
        for _ in range(repetitions):
            weighted_parts.append(text)
    
    return ' '.join(weighted_parts)

def main():
    print(f"Loading data from: {RAW_DATA_PATH}")
    
    if not RAW_DATA_PATH.exists():
        print(f"[ERROR] File not found: {RAW_DATA_PATH}")
        return
    
    # Load CSV dengan encoding detection
    encoding = detect_encoding(RAW_DATA_PATH)
    
    for enc in [encoding, 'latin-1', 'ISO-8859-1', 'cp1252', 'utf-8-sig']:
        try:
            print(f"Trying encoding: {enc}")
            df = pd.read_csv(RAW_DATA_PATH, encoding=enc)
            print(f"✓ Successfully read with {enc}")
            print(f"  Shape: {df.shape}")
            break
        except Exception as e:
            print(f"  ✗ Failed with {enc}")
            continue
    else:
        print("[ERROR] Could not read CSV")
        return
    
    print(f"\nDataset Info:")
    print(f"  Total rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    
    corpus = []
    skipped = 0
    
    for idx, row in df.iterrows():
        # Extract fields
        fields = extract_fields(row, list(FIELD_WEIGHTS.keys()))
        
        # Check if document has enough content
        total_words = sum(len(text.split()) for text in fields.values())
        if total_words < 10:
            skipped += 1
            continue
        
        # Build weighted text untuk indexing
        weighted_text = build_weighted_text(fields)
        
        if len(weighted_text.split()) < 5:
            skipped += 1
            continue
        
        # Build raw text untuk display
        raw_parts = []
        for field in ['Title', 'Authors', 'Keywords', 'Abstract']:
            if field in row and pd.notna(row[field]):
                raw_parts.append(f"{field}: {row[field]}")
        raw_text = "\n".join(raw_parts)
        
        corpus.append({
            "doc_id": f"doc_{idx}",
            "title": fields.get('Title', ''),
            "keywords": fields.get('Keywords', ''),
            "abstract": fields.get('Abstract', ''),
            "authors": fields.get('Authors', ''),
            "raw_text": raw_text[:1000],  # Save untuk display
            "weighted_text": weighted_text,  # Untuk indexing
            "fields": fields  # Simpan semua field
        })
        
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1} documents...")
    
    # Save corpus
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Corpus built:")
    print(f"  Total documents: {len(corpus)}")
    print(f"  Skipped (too short): {skipped}")
    print(f"  Saved to: {OUTPUT_PATH}")
    
    # Sample output
    print("\n" + "="*80)
    print("SAMPLE DOCUMENTS:")
    print("="*80)
    for i, doc in enumerate(corpus[:2]):
        print(f"\nDocument {i+1} (ID: {doc['doc_id']}):")
        print(f"  Title: {doc['title'][:80]}...")
        print(f"  Keywords: {doc['keywords'][:80]}...")
        print(f"  Weighted text word count: {len(doc['weighted_text'].split())}")
        print(f"  First 100 chars of weighted text: {doc['weighted_text'][:100]}...")

if __name__ == "__main__":
    main()