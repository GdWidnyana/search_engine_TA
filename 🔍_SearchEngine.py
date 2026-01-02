import streamlit as st
import sys
import time
import pytz
from pathlib import Path
from datetime import datetime

from bm25_tuned_v2 import EnhancedBM25Ranker
from utils import (
    load_search_history,
    save_search_history,
    get_search_stats,
    format_timestamp
)
from config import (
    INDEX_PATH,
    BLOCKS_PATH,
    FRONTCODED_PATH,
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
    """Load Improved Dictionary BM25 ranker (cached)"""
    return EnhancedBM25Ranker(BLOCKS_PATH, FRONTCODED_PATH, INDEX_PATH)


def initialize_session_state():
    """Initialize session state variables"""

    if 'query_info' not in st.session_state:
        st.session_state.query_info = None

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
    
    if 'show_detail' not in st.session_state:
        st.session_state.show_detail = None
    
    if 'trigger_search' not in st.session_state:
        st.session_state.trigger_search = False


def render_header():
    """Render application header"""
    st.markdown("""
        <div class="main-header">
            <h1>🔍 Skripsi Search Engine</h1>
            <p class="subtitle">Sistem pencarian skripsi berbasis BM25</p>
        </div>
    """, unsafe_allow_html=True)


def render_search_box(ranker):
    """Render main search box"""
    col1, col2 = st.columns([6, 1])
    
    with col1:
        query = st.text_input(
            "Cari skripsi...",
            value=st.session_state.query,
            placeholder="Contoh: machine learning, analisissentimen (tanpa spasi ok!)",
            label_visibility="collapsed",
            key="search_input"
        )
    
    with col2:
        search_clicked = st.button("🔍 Cari", use_container_width=True, type="primary")
    
    # Example queries
    st.markdown("**Contoh query:**")
    
    cols = st.columns(5, gap="small")
    
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
        
        # Timezone selector
        st.markdown("#### ⏰ Timezone")
        if 'user_timezone' not in st.session_state:
            st.session_state.user_timezone = 'Asia/Makassar'
        
        tz_options = {
            'Asia/Jakarta': 'WIB (GMT+7)',
            'Asia/Makassar': 'WITA (GMT+8)',
            'Asia/Jayapura': 'WIT (GMT+9)'
        }
        
        selected_tz = st.selectbox(
            "Pilih timezone Anda",
            options=list(tz_options.keys()),
            format_func=lambda x: tz_options[x],
            index=1,
            help="Timezone untuk menampilkan waktu yang akurat"
        )
        st.session_state.user_timezone = selected_tz
        
        st.markdown("---")
        
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
        st.markdown("**Fitur Baru: Word Segmentation!**")
        st.markdown("• Tulis query tanpa spasi: `analisissentimen` → otomatis jadi `analisis sentimen`")
        st.markdown("• Wildcard: `sentim*` atau `ma?hine`")
        st.markdown("• Repeated chars: `sentimennnn` → otomatis jadi `sentimen`")
        st.markdown("---")
        for tip in SEARCH_TIPS:
            st.markdown(f"• {tip}")


def render_query_feedback():
    """Render query processing feedback"""
    qi = st.session_state.query_info
    if not qi:
        return

    original = qi["original_query"]
    
    # Word Segmentation feedback
    if qi.get("segmented_query"):
        st.success(f"✂️ **Query dipisah:** `{original}` → `{qi['segmented_query']}`")
    
    # Spelling correction feedback
    corrected = " ".join(qi["corrected_terms"])
    if corrected.lower() != original.lower() and not qi.get("segmented_query"):
        st.info(f"🔎 **Maksud Anda:** `{corrected}`")


def render_wildcard_expansion():
    """Render wildcard expansion info"""
    qi = st.session_state.query_info
    if not qi or not qi["is_wildcard"]:
        return

    expanded = qi["expanded_terms"]

    if expanded:
        with st.expander("✨ Ekspansi Wildcard"):
            st.markdown("Query diperluas menjadi:")
            for term in expanded[:30]:
                st.markdown(f"- `{term}`")
            if len(expanded) > 30:
                st.markdown(f"... dan {len(expanded) - 30} kata lainnya")


def render_result_card(result, index, advanced_mode):
    """Render single result card"""
    with st.container():
        st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <span class="result-number">{index}</span>
                    <span class="result-title">{result['title']}</span>
                </div>
        """, unsafe_allow_html=True)
        
        # Keywords
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
    """Save result to favorites with user's timezone"""
    from pages_utils import load_favorites, save_favorites_func
    import pytz
    
    favorites = load_favorites()
    
    # Check if already in favorites
    if result['doc_id'] not in [f['doc_id'] for f in favorites]:
        try:
            user_tz = pytz.timezone(st.session_state.get('user_timezone', 'Asia/Makassar'))
            timestamp = datetime.now(user_tz).isoformat()
        except:
            timestamp = datetime.now().isoformat()
        
        result['saved_at'] = timestamp
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
            for entry in st.session_state.search_history[-5:][::-1]:
                query = entry['query']
                timestamp = format_timestamp(entry['timestamp'])
                if st.button(f"🕐 {query}", key=f"history_{entry['timestamp']}", use_container_width=True):
                    # Set query dan trigger search
                    st.session_state.query = query
                    st.session_state.trigger_search = True
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
    
    # Check if showing detail
    if st.session_state.show_detail:
        st.markdown("---")
        render_document_detail(st.session_state.show_detail)
        
        if st.button("❌ Tutup Detail Skripsi", use_container_width=True, type="secondary"):
            st.session_state.show_detail = None
            st.rerun()
        
        return
    
    # Load ranker
    try:
        ranker = load_ranker()
        
        # Display dictionary stats in sidebar if advanced mode
        if st.session_state.advanced_mode:
            with st.sidebar:
                st.markdown("---")
                st.markdown("### 📚 Dictionary Info")
                stats = ranker.get_stats()
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
    render_query_feedback()
    render_wildcard_expansion()
    
    # Perform search
    should_search = (search_clicked and query) or st.session_state.trigger_search
    
    if should_search:
        # Use query from session state if triggered from history, otherwise use input query
        search_query = st.session_state.query if st.session_state.trigger_search else query
        
        # Reset trigger_search flag after using it
        if st.session_state.trigger_search:
            st.session_state.trigger_search = False
        
        st.session_state.query = search_query
        
        with st.spinner("🔍 Mencari..."):
            try:
                # Measure search time
                start_time = time.time()
                
                # FIXED: search() returns dictionary
                search_output = ranker.search(search_query, top_k=options['top_k'], verbose=False)
                
                # Extract results and query_info from dictionary
                results = search_output["results"]
                query_info = search_output["query_info"]
                
                st.session_state.query_info = query_info
                
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
                
                # Save to history with user's timezone
                try:
                    import pytz
                    user_tz = pytz.timezone(st.session_state.get('user_timezone', 'Asia/Makassar'))
                    timestamp = datetime.now(user_tz).isoformat()
                except:
                    timestamp = datetime.now().isoformat()
                
                st.session_state.search_history.append({
                    'query': search_query,
                    'timestamp': timestamp,
                    'num_results': len(results),
                    'search_time': search_time
                })
                save_search_history(st.session_state.search_history)
                
            except Exception as e:
                st.error(f"❌ Error during search: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
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
        
        # Export buttons
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        
        with col1:
            # PDF Export
            def create_pdf():
                from io import BytesIO
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
                from reportlab.lib import colors
                
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                       rightMargin=30, leftMargin=30,
                                       topMargin=30, bottomMargin=18)
                
                elements = []
                styles = getSampleStyleSheet()
                
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=16,
                    textColor=colors.HexColor('#667eea'),
                    spaceAfter=12,
                    alignment=1
                )
                
                title = Paragraph(f"Hasil Pencarian: {st.session_state.query}", title_style)
                elements.append(title)
                elements.append(Spacer(1, 0.2*inch))
                
                info_text = f"Jumlah hasil: {len(st.session_state.current_results)} | " \
                           f"Waktu: {st.session_state.search_time*1000:.2f} ms | " \
                           f"Tanggal: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                info = Paragraph(info_text, styles['Normal'])
                elements.append(info)
                elements.append(Spacer(1, 0.3*inch))
                
                for idx, result in enumerate(st.session_state.current_results, 1):
                    result_title = Paragraph(
                        f"<b>{idx}. {result.get('title', 'N/A')}</b>",
                        styles['Heading3']
                    )
                    elements.append(result_title)
                    elements.append(Spacer(1, 0.1*inch))
                    
                    details = [
                        f"<b>Score:</b> {result.get('score', 0):.2f}",
                        f"<b>Authors:</b> {result.get('authors', 'N/A')}",
                        f"<b>Keywords:</b> {result.get('keywords', 'N/A')[:100]}...",
                        f"<b>Abstract:</b> {result.get('abstract', 'N/A')[:200]}..."
                    ]
                    
                    for detail in details:
                        elements.append(Paragraph(detail, styles['Normal']))
                        elements.append(Spacer(1, 0.05*inch))
                    
                    elements.append(Spacer(1, 0.2*inch))
                    
                    if idx % 3 == 0 and idx < len(st.session_state.current_results):
                        elements.append(PageBreak())
                
                doc.build(elements)
                buffer.seek(0)
                return buffer
            
            try:
                pdf_buffer = create_pdf()
                st.download_button(
                    "📄 Download PDF",
                    pdf_buffer,
                    f"search_results_{st.session_state.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error PDF: {str(e)}")
        
        with col2:
            # Excel Export
            def create_excel():
                import pandas as pd
                from io import BytesIO
                
                data = []
                for idx, result in enumerate(st.session_state.current_results, 1):
                    data.append({
                        'No': idx,
                        'Title': result.get('title', 'N/A'),
                        'Score': round(result.get('score', 0), 2),
                        'Authors': result.get('authors', 'N/A'),
                        'Keywords': result.get('keywords', 'N/A'),
                        'Abstract': result.get('abstract', 'N/A')[:200] + '...',
                        'Domain': result.get('domain', 'N/A'),
                        'Specificity': result.get('specificity', 'N/A')
                    })
                
                df = pd.DataFrame(data)
                
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Search Results')
                    
                    workbook = writer.book
                    worksheet = writer.sheets['Search Results']
                    
                    for idx, col in enumerate(df.columns):
                        max_length = max(
                            df[col].astype(str).map(len).max(),
                            len(col)
                        )
                        worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
                
                buffer.seek(0)
                return buffer
            
            try:
                excel_buffer = create_excel()
                st.download_button(
                    "📊 Download Excel",
                    excel_buffer,
                    f"search_results_{st.session_state.query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error Excel: {str(e)}")
        
        with col3:
            if st.button("📈 Lihat Statistik", use_container_width=True):
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
            <p>Skripsi Search Engine v1.0 | Developed by Team 4</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
