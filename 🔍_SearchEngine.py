"""
Streamlit Search Engine Application
Modern, elegant, and feature-rich interface
UPDATED: Using Dictionary BM25 (Blocks + Front Coding)
"""

import streamlit as st
import sys
import time
from pathlib import Path
from datetime import datetime

# Add scripts directory to path
# SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
# sys.path.insert(0, str(SCRIPTS_DIR))

# UPDATED: Import ImprovedDictionaryBM25Ranker with better spelling correction
from bm25_with_dictionary_improved import ImprovedDictionaryBM25Ranker
from utils import (
    load_search_history,
    save_search_history,
    get_search_stats,
    format_timestamp
)
from config import (
    INDEX_PATH,
    BLOCKS_PATH,  # NEW
    FRONTCODED_PATH,  # NEW
    PAGE_CONFIG,
    CUSTOM_CSS,
    SEARCH_TIPS,
    EXAMPLE_QUERIES
)
from detail_utils import render_document_detail
from reset_component import render_reset_menu

# Page configuration
st.set_page_config(**PAGE_CONFIG)

# Custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_resource
def load_ranker():
    """Load Improved Dictionary BM25 ranker (cached) - UPDATED"""
    return ImprovedDictionaryBM25Ranker(BLOCKS_PATH, FRONTCODED_PATH, INDEX_PATH)


def initialize_session_state():
    """Initialize session state variables"""
    if 'search_history' not in st.session_state:
        st.session_state.search_history = load_search_history()
    
    if 'current_results' not in st.session_state:
        st.session_state.current_results = []
    
    if 'query' not in st.session_state:
        st.session_state.query = ""
    
    if 'advanced_mode' not in st.session_state:
        st.session_state.advanced_mode = False
    
    if 'show_stats' not in st.session_state:
        st.session_state.show_stats = False
    
    if 'search_time' not in st.session_state:
        st.session_state.search_time = 0
    
    # Tambah state untuk detail modal
    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = None


def render_header():
    """Render application header"""
    st.markdown("""
        <div class="main-header">
            <h1>🔍 Skripsi Search Engine</h1>
            <p class="subtitle">Sistem pencarian skripsi berbasis BM25 dengan Dictionary Optimization</p>
        </div>
    """, unsafe_allow_html=True)


def render_search_box(ranker):
    """Render main search box"""
    col1, col2 = st.columns([6, 1])
    
    with col1:
        query = st.text_input(
            "Cari skripsi...",
            value=st.session_state.query,
            placeholder="Contoh: machine learning, sistem rekomendasi, user interface",
            label_visibility="collapsed",
            key="search_input"
        )
    
    with col2:
        search_clicked = st.button("🔍 Cari", use_container_width=True, type="primary")
    
    # Example queries
    st.markdown("**Contoh query:**")
    cols = st.columns(len(EXAMPLE_QUERIES))
    for i, example in enumerate(EXAMPLE_QUERIES):
        with cols[i]:
            if st.button(f"💡 {example}", key=f"example_{i}", use_container_width=True):
                st.session_state.query = example
                st.rerun()
    
    return query, search_clicked


def render_search_options():
    """Render search options sidebar"""
    with st.sidebar:
        st.markdown("### ⚙️ Pengaturan Pencarian")
        
        # Number of results
        top_k = st.number_input(
            "Jumlah hasil",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            help="Masukkan jumlah hasil yang ingin ditampilkan (1-100)"
        )
        
        # Advanced mode toggle
        advanced = st.checkbox(
            "Mode Advanced",
            value=st.session_state.advanced_mode,
            help="Tampilkan informasi detail seperti score, domain, dan specificity"
        )
        st.session_state.advanced_mode = advanced
        
        # Sort options
        sort_by = st.selectbox(
            "Urutkan berdasarkan",
            ["Relevansi (Score)", "Terbaru", "Judul A-Z"],
            index=0
        )
        
        # Filter by domain (if advanced mode)
        domain_filter = None
        if advanced:
            st.markdown("---")
            st.markdown("### 🏷️ Filter Domain")
            domain_options = [
                "Semua",
                "Machine Learning & AI",
                "NLP & Text Mining",
                "Security & Cryptography",
                "UI/UX & Design",
                "Recommender System",
                "Medical & Health",
                "IoT & Embedded",
                "Business Intelligence",
                "Mobile Development"
            ]
            domain_filter = st.selectbox("Domain", domain_options)
            if domain_filter == "Semua":
                domain_filter = None
        
        return {
            'top_k': int(top_k),
            'sort_by': sort_by,
            'domain_filter': domain_filter
        }


def render_search_tips():
    """Render search tips"""
    with st.expander("💡 Tips Pencarian"):
        for tip in SEARCH_TIPS:
            st.markdown(f"• {tip}")


def render_result_card(result, index, advanced_mode):
    """Render single result card - DENGAN SEMUA KEYWORD"""
    with st.container():
        st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <span class="result-number">{index}</span>
                    <span class="result-title">{result['title']}</span>
                </div>
        """, unsafe_allow_html=True)
        
        # Keywords - TAMPILKAN SEMUA
        if result.get('keywords'):
            keywords = result['keywords'].split()
            keyword_badges = " ".join([f'<span class="keyword-badge">{kw}</span>' for kw in keywords])
            st.markdown(f'<div class="keyword-container">{keyword_badges}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="font-size: 0.8rem; color: #666; margin-bottom: 10px;">Total keywords: {len(keywords)}</div>', unsafe_allow_html=True)
        
        # Abstract
        if result.get('abstract'):
            st.markdown(f"**Abstract:** {result['abstract']}")
        
        # Authors
        if result.get('authors'):
            st.markdown(f"👤 **Penulis:** {result['authors']}")
        
        # Advanced info
        if advanced_mode:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", f"{result['score']:.2f}")
            with col2:
                st.metric("Domain", result.get('domain', 'general').upper())
            with col3:
                st.metric("Specificity", result.get('specificity', 'N/A').upper())
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            detail_key = f"detail_{result['doc_id']}_{index}"
            if st.button("📄 Detail", key=detail_key, use_container_width=True):
                st.session_state.show_detail = result['doc_id']
                st.rerun()
        with col2:
            save_key = f"save_{result['doc_id']}_{index}"
            if st.button("💾 Simpan", key=save_key, use_container_width=True):
                save_to_favorites(result)
                st.success("✅ Disimpan!")
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)


def save_to_favorites(result):
    """Save result to favorites"""
    from pages_utils import load_favorites, save_favorites_func
    
    favorites = load_favorites()
    
    # Check if already in favorites
    if result['doc_id'] not in [f['doc_id'] for f in favorites]:
        result['saved_at'] = datetime.now().isoformat()
        favorites.append(result)
        save_favorites_func(favorites)


def render_statistics():
    """Render search statistics"""
    if st.session_state.show_stats and st.session_state.search_history:
        stats = get_search_stats(st.session_state.search_history)
        
        st.markdown("### 📊 Statistik Pencarian")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pencarian", stats['total_searches'])
        with col2:
            st.metric("Query Unik", stats['unique_queries'])
        with col3:
            st.metric("Rata-rata Hasil", f"{stats['avg_results']:.1f}")
        with col4:
            st.metric("Pencarian Hari Ini", stats['today_searches'])
        
        # Top queries
        if stats['top_queries']:
            st.markdown("**Query Populer:**")
            for query, count in stats['top_queries'][:5]:
                st.markdown(f"• {query} ({count}x)")


def render_search_history():
    """Render search history sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📜 Riwayat Pencarian")
        
        if st.session_state.search_history:
            # Show last 5 searches
            for entry in st.session_state.search_history[-5:][::-1]:
                query = entry['query']
                timestamp = format_timestamp(entry['timestamp'])
                if st.button(f"🕐 {query}", key=f"history_{entry['timestamp']}", use_container_width=True):
                    st.session_state.query = query
                    st.rerun()
            
            if st.button("🗑️ Hapus Riwayat", use_container_width=True):
                st.session_state.search_history = []
                save_search_history([])
                st.rerun()
        else:
            st.info("Belum ada riwayat pencarian")


def main():
    """Main application"""
    initialize_session_state()
    
    # PERIKSA APAKAH HARUS MENAMPILKAN DETAIL
    if st.session_state.show_detail:
        st.markdown("---")
        render_document_detail(st.session_state.show_detail)
        
        # Tombol untuk kembali ke hasil pencarian
        if st.button("❌ Tutup Detail Skripsi", use_container_width=True, type="secondary"):
            st.session_state.show_detail = None
            st.rerun()
        
        return
    
    # Load ranker - UPDATED
    try:
        ranker = load_ranker()
        
        # Display dictionary stats in sidebar if advanced mode
        if st.session_state.advanced_mode:
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 📚 Dictionary Info")
                stats = ranker.get_dictionary_stats()
                st.metric("Total Blocks", f"{stats['num_blocks']:,}")
                st.metric("Total Terms", f"{stats['num_terms']:,}")
                st.metric("Compression", f"{stats['compression_ratio']:.2f}x")
                
    except Exception as e:
        st.error(f"❌ Error loading ranker: {str(e)}")
        st.info("Pastikan file berikut tersedia:")
        st.code(f"""
- {BLOCKS_PATH}
- {FRONTCODED_PATH}
- {INDEX_PATH}
        """)
        st.stop()
    
    # Header
    render_header()
    
    # Search options
    options = render_search_options()
    
    # Search box
    query, search_clicked = render_search_box(ranker)
    
    # Search tips
    render_search_tips()
    
    # Perform search
    if search_clicked and query:
        st.session_state.query = query
        
        with st.spinner("🔍 Mencari..."):
            try:
                # Measure search time
                start_time = time.time()
                results = ranker.search(query, top_k=options['top_k'], verbose=False)
                search_time = time.time() - start_time
                st.session_state.search_time = search_time
                
                # Filter by domain if needed
                if options['domain_filter']:
                    domain_map = {
                        "Machine Learning & AI": "ml_ai",
                        "NLP & Text Mining": "nlp",
                        "Security & Cryptography": "security",
                        "UI/UX & Design": "ui_ux",
                        "Recommender System": "recommender",
                        "Medical & Health": "medical",
                        "IoT & Embedded": "iot",
                        "Business Intelligence": "business",
                        "Mobile Development": "mobile"
                    }
                    target_domain = domain_map.get(options['domain_filter'])
                    if target_domain:
                        results = [r for r in results if r.get('domain') == target_domain]
                
                # Sort results
                if options['sort_by'] == "Terbaru":
                    results = sorted(results, key=lambda x: x['doc_id'], reverse=True)
                elif options['sort_by'] == "Judul A-Z":
                    results = sorted(results, key=lambda x: x['title'])
                
                st.session_state.current_results = results
                
                # Save to history
                st.session_state.search_history.append({
                    'query': query,
                    'timestamp': datetime.now().isoformat(),
                    'num_results': len(results),
                    'search_time': search_time
                })
                save_search_history(st.session_state.search_history)
                
            except Exception as e:
                st.error(f"❌ Error during search: {str(e)}")
                st.session_state.current_results = []
    
    # Display results
    if st.session_state.current_results:
        # Header with search time
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 📚 Ditemukan {len(st.session_state.current_results)} hasil")
        with col2:
            st.markdown(f"""
                <div style='text-align: right; padding: 10px;'>
                    <span style='font-size: 0.9rem; color: #666;'>⏱️ Waktu pencarian:</span><br>
                    <span style='font-size: 1.3rem; font-weight: bold; color: #667eea;'>
                        {st.session_state.search_time*1000:.2f} ms
                    </span>
                </div>
            """, unsafe_allow_html=True)
        
        # Export button
        col1, col2, col3 = st.columns([1, 1, 4])
        
        with col1:
            import json
            json_str = json.dumps(st.session_state.current_results, indent=2, ensure_ascii=False)
            st.download_button(
                "📥 Export JSON",
                json_str,
                f"search_results_{st.session_state.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                "application/json",
                use_container_width=True
            )
        
        with col2:
            if st.button("📊 Lihat Statistik", use_container_width=True):
                st.session_state.show_stats = not st.session_state.show_stats
                st.rerun()
        
        # Statistics
        if st.session_state.show_stats:
            render_statistics()
        
        st.markdown("---")
        
        # Render results
        for i, result in enumerate(st.session_state.current_results, 1):
            render_result_card(result, i, st.session_state.advanced_mode)
    
    elif st.session_state.query:
        st.info("🔍 Tidak ada hasil ditemukan. Coba kata kunci lain.")
    
    # Search history
    render_search_history()
    
    # Reset data
    render_reset_menu()
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p>Skripsi Search Engine v2.0 | Powered by Dictionary BM25</p>
            <p>💡 Tips: Gunakan kata kunci spesifik untuk hasil lebih akurat</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
