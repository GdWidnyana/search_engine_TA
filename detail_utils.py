"""
Detail Utils - Functions for fetching detailed document information from database_skripsi.json
"""

import json
from pathlib import Path
from typing import Dict, Optional
import streamlit as st

# Path to database_skripsi.json
CORPUS_PATH = Path(__file__).parent.parent / "streamlit_ir" / "data" / "database_skripsi.json"

@st.cache_data(ttl=3600)  # Cache selama 1 jam
def load_corpus_data():
    """Load data from database_skripsi.json"""
    try:
        if CORPUS_PATH.exists():
            with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        else:
            st.warning(f"File database_skripsi.json tidak ditemukan di: {CORPUS_PATH}")
            return []
    except Exception as e:
        st.error(f"Error loading corpus data: {e}")
        return []

def get_document_details(doc_id: str) -> Optional[Dict]:
    """Get detailed document information by doc_id"""
    try:
        data = load_corpus_data()
        
        if not data:
            return None
        
        # Cari dokumen berdasarkan doc_id
        for doc in data:
            if doc.get('doc_id') == doc_id:
                # Format data untuk ditampilkan - PERBAIKI: Cari link di berbagai lokasi
                formatted_doc = {
                    'Title': doc.get('title', doc.get('Title', '')),
                    'Authors': doc.get('authors', doc.get('Authors', doc.get('fields', {}).get('Authors', ''))),
                    'Advisors': doc.get('fields', {}).get('Advisors', ''),
                    'Keywords': doc.get('keywords', doc.get('Keywords', '')),
                    'Publisher': doc.get('publisher', doc.get('Publisher', doc.get('fields', {}).get('Publisher', ''))),
                    'Abstract': doc.get('abstract', doc.get('Abstract', '')),
                    'Issue Date': doc.get('issue_date', doc.get('Issue Date', doc.get('fields', {}).get('Issue Date', ''))),
                    
                    # PERBAIKAN: Cari link di berbagai kemungkinan lokasi
                    'Link Detail': get_link_from_doc(doc, 'link_detail', 'Link Detail'),
                    'Link PDF': get_link_from_doc(doc, 'link_pdf', 'Link PDF'),
                    
                    'BAB 1': doc.get('fields', {}).get('BAB 1', ''),
                    'BAB 2': doc.get('fields', {}).get('BAB 2', ''),
                    'BAB 3': doc.get('fields', {}).get('BAB 3', ''),
                    'BAB 4': doc.get('fields', {}).get('BAB 4', ''),
                    'BAB 5': doc.get('fields', {}).get('BAB 5', ''),
                    'doc_id': doc.get('doc_id', ''),
                    'domain': doc.get('domain', ''),
                    'specificity': doc.get('specificity', '')
                }
                return formatted_doc
        
        return None
    except Exception as e:
        st.error(f"Error getting document details: {e}")
        return None

def get_link_from_doc(doc: Dict, direct_key: str, field_key: str) -> str:
    """Get link from document with multiple fallback locations"""
    # Coba dari lokasi langsung
    link = doc.get(direct_key, '')
    if link and isinstance(link, str) and link.strip():
        return link.strip()
    
    # Coba dari fields
    fields = doc.get('fields', {})
    link = fields.get(field_key, '')
    if link and isinstance(link, str) and link.strip():
        return link.strip()
    
    # Coba dari root dengan key yang berbeda
    if field_key == 'Link Detail':
        for key in ['link', 'url', 'detail_link', 'source']:
            link = doc.get(key, '')
            if link and isinstance(link, str) and link.strip():
                return link.strip()
    
    if field_key == 'Link PDF':
        for key in ['pdf', 'pdf_link', 'file', 'document']:
            link = doc.get(key, '')
            if link and isinstance(link, str) and link.strip():
                return link.strip()
    
    return ''

def debug_document_structure(doc_id: str):
    """Debug function to see document structure"""
    try:
        data = load_corpus_data()
        
        if not data:
            st.error("Data kosong")
            return
        
        for doc in data:
            if doc.get('doc_id') == doc_id:
                st.info(f"🔍 Struktur dokumen {doc_id}:")
                st.json(doc)
                
                # Tampilkan semua keys
                st.write("🔑 Semua keys:", list(doc.keys()))
                
                # Cari link_detail
                if 'link_detail' in doc:
                    st.success(f"✅ link_detail ditemukan: {doc['link_detail']}")
                else:
                    st.warning("❌ link_detail tidak ditemukan di root")
                    
                    # Cari di fields
                    fields = doc.get('fields', {})
                    if 'Link Detail' in fields:
                        st.success(f"✅ Link Detail ditemukan di fields: {fields['Link Detail']}")
                    else:
                        st.warning("❌ Link Detail tidak ditemukan di fields")
                
                # Cari link_pdf
                if 'link_pdf' in doc:
                    st.success(f"✅ link_pdf ditemukan: {doc['link_pdf']}")
                else:
                    st.warning("❌ link_pdf tidak ditemukan di root")
                    
                    # Cari di fields
                    if 'Link PDF' in fields:
                        st.success(f"✅ Link PDF ditemukan di fields: {fields['Link PDF']}")
                    else:
                        st.warning("❌ Link PDF tidak ditemukan di fields")
                
                return
        
        st.error(f"❌ Dokumen {doc_id} tidak ditemukan")
    except Exception as e:
        st.error(f"Error debugging: {e}")
        
def parse_keywords(keywords_str: str):
    """Parse keywords string into list, supporting phrases"""
    if not keywords_str:
        return []
    
    # Bersihkan string
    keywords_str = keywords_str.strip()
    
    # Prioritize semicolon separation first
    if ';' in keywords_str:
        keywords = []
        for kw in keywords_str.split(';'):
            kw = kw.strip()
            if kw and ',' in kw:
                # Handle mixed separators
                sub_keywords = [sub.strip() for sub in kw.split(',') if sub.strip()]
                keywords.extend(sub_keywords)
            elif kw:
                keywords.append(kw)
    elif ',' in keywords_str:
        keywords = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
    else:
        keywords = [kw.strip() for kw in keywords_str.split() if kw.strip()]
    
    return [kw for kw in keywords if kw]
      
def render_document_detail(doc_id: str):
    """Render detailed document information"""
    details = get_document_details(doc_id)
    
    if not details:
        st.warning("❌ Detail dokumen tidak ditemukan")
        return
    
    # Custom CSS untuk halaman detail
    st.markdown("""
        <style>
        .detail-container {
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            border-left: 5px solid #667eea;
        }
        .detail-header {
            color: #667eea;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        .detail-section {
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #4c51bf;
        }
        .detail-section-title {
            color: #4c51bf;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .detail-item {
            margin-bottom: 12px;
            padding: 10px 15px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .detail-label {
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 5px;
        }
        .detail-value {
            color: #2d3748;
            line-height: 1.6;
        }
        .keyword-badge {
            display: inline-block;
            padding: 6px 15px;
            background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
            color: #667eea;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            margin-right: 8px;
            margin-bottom: 8px;
            border: 1px solid #667eea40;
        }
        .bab-content {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            margin-top: 10px;
            max-height: 400px;
            overflow-y: auto;
            line-height: 1.8;
        }
        .link-button {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            margin-right: 10px;
            margin-bottom: 10px;
            transition: all 0.3s ease;
        }
        .link-button:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        .link-text {
            color: #667eea;
            text-decoration: none;
            word-break: break-all;
            font-size: 0.9rem;
        }
        .link-text:hover {
            text-decoration: underline;
        }
        .no-link {
            color: #a0aec0;
            font-style: italic;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
        <div class="detail-container">
            <div class="detail-header">
                <h2 style="margin: 0; font-size: 1.8rem;">📄 {details.get('Title', 'N/A')}</h2>
                <p style="color: #718096; margin: 5px 0 0 0;">Doc ID: {details.get('doc_id', 'N/A')}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Main information in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
            <div class="detail-section">
                <div class="detail-section-title">👥 Informasi Penulis</div>
        """, unsafe_allow_html=True)
        
        # Authors
        if details.get('Authors'):
            st.markdown(f"""
                <div class="detail-item">
                    <div class="detail-label">📝 Penulis</div>
                    <div class="detail-value">{details.get('Authors', 'N/A')}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Advisors
        if details.get('Advisors'):
            st.markdown(f"""
                <div class="detail-item">
                    <div class="detail-label">🎓 Pembimbing</div>
                    <div class="detail-value">{details.get('Advisors', 'N/A')}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Publisher
        if details.get('Publisher'):
            st.markdown(f"""
                <div class="detail-item">
                    <div class="detail-label">🏛️ Penerbit</div>
                    <div class="detail-value">{details.get('Publisher', 'N/A')}</div>
                </div>
            """, unsafe_allow_html=True)
        
        # Issue Date
        if details.get('Issue Date'):
            st.markdown(f"""
                <div class="detail-item">
                    <div class="detail-label">📅 Tanggal Terbit</div>
                    <div class="detail-value">{details.get('Issue Date', 'N/A')}</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="detail-section">
                <div class="detail-section-title">🔗 Links & Metadata</div>
        """, unsafe_allow_html=True)
        
        # Link Detail - TAMPILKAN TERPISAH
        st.markdown("""
            <div class="detail-item">
                <div class="detail-label">🔗 Link Detail</div>
        """, unsafe_allow_html=True)
        
        if details.get('Link Detail') and details.get('Link Detail').strip():
            st.markdown(f"""
                <div class="detail-value">
                    <a href="{details.get('Link Detail')}" target="_blank" class="link-button">
                        📖 Lihat Detail
                    </a>
                    <div style="margin-top: 5px;">
                        <small><code>{details.get('Link Detail')[:80]}...</code></small>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="detail-value">
                    <span class="no-link">Tidak tersedia</span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Link PDF - TAMPILKAN TERPISAH
        st.markdown("""
            <div class="detail-item">
                <div class="detail-label">📄 Link PDF</div>
        """, unsafe_allow_html=True)
        
        if details.get('Link PDF') and details.get('Link PDF').strip():
            st.markdown(f"""
                <div class="detail-value">
                    <a href="{details.get('Link PDF')}" target="_blank" class="link-button">
                        📥 Download PDF
                    </a>
                    <div style="margin-top: 5px;">
                        <small><code>{details.get('Link PDF')[:80]}...</code></small>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="detail-value">
                    <span class="no-link">Tidak tersedia</span>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Domain & Specificity
        if details.get('domain'):
            st.markdown(f"""
                <div class="detail-item">
                    <div class="detail-label">🏷️ Domain</div>
                    <div class="detail-value">{details.get('domain', 'N/A').upper()}</div>
                </div>
            """, unsafe_allow_html=True)
        
        if details.get('specificity'):
            specificity_labels = {
                'specific': '🎯 Spesifik',
                'moderate': '📊 Moderat',
                'generic': '🌐 Umum'
            }
            specificity = specificity_labels.get(details.get('specificity'), details.get('specificity', 'N/A'))
            st.markdown(f"""
                <div class="detail-item">
                    <div class="detail-label">🎯 Specificity</div>
                    <div class="detail-value">{specificity}</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Keywords - TAMPILKAN SEMUA
    if details.get('Keywords'):
        st.markdown("""
            <div class="detail-section">
                <div class="detail-section-title">🏷️ Keywords</div>
        """, unsafe_allow_html=True)
        
        # Gunakan fungsi parse_keywords yang baru
        keywords = parse_keywords(details.get('Keywords', ''))
        
        # Tampilkan semua keyword, tidak dibatasi
        keyword_html = " ".join([f'<span class="keyword-badge">{kw}</span>' for kw in keywords if kw.strip()])
        st.markdown(f'<div style="padding: 10px 15px;">{keyword_html}</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="margin-top: 10px; color: #718096; font-size: 0.9rem;">
                Total keywords: {len(keywords)}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Abstract
    if details.get('Abstract'):
        st.markdown("""
            <div class="detail-section">
                <div class="detail-section-title">📝 Abstract</div>
                <div class="bab-content">{}</div>
            </div>
        """.format(details.get('Abstract', 'N/A')), unsafe_allow_html=True)
    
    # BAB Sections
    bab_sections = ['BAB 1', 'BAB 2', 'BAB 3', 'BAB 4', 'BAB 5']
    available_babs = [bab for bab in bab_sections if details.get(bab) and len(details.get(bab, '').strip()) > 50]
    
    if available_babs:
        st.markdown("""
            <div class="detail-section">
                <div class="detail-section-title">📚 Bab Skripsi</div>
        """, unsafe_allow_html=True)
        
        for bab in available_babs:
            bab_content = details.get(bab, '')
            if len(bab_content) > 500:  # Hanya tampilkan expander jika konten panjang
                with st.expander(f"{bab} ({len(bab_content)} karakter)"):
                    st.markdown(f"""
                        <div class="bab-content">
                            {bab_content}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"**{bab}:**")
                st.markdown(f"""
                    <div class="bab-content" style="max-height: 200px;">
                        {bab_content}
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("""
        <div style="display: flex; gap: 15px; justify-content: center; margin-top: 30px;">
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⬅️ Kembali", use_container_width=True, type="secondary"):
            if 'show_detail' in st.session_state:
                del st.session_state.show_detail
            st.rerun()
    
    with col2:
        if details.get('Link PDF') and details.get('Link PDF').strip():
            st.markdown(f"""
                <a href="{details.get('Link PDF')}" target="_blank" style="text-decoration: none; width: 100%;">
                    <button style="
                        width: 100%;
                        padding: 12px;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 5px 20px rgba(102, 126, 234, 0.4)';" 
                    onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='none';">
                        📥 Download PDF
                    </button>
                </a>
            """, unsafe_allow_html=True)
        else:
            st.button("📥 Download PDF", disabled=True, use_container_width=True)
    
    with col3:
        # TOMBOL SIMPAN KE FAVORITE
        if st.button("⭐ Simpan ke Favorite", use_container_width=True):
            from pages_utils import load_favorites, save_favorites_func
            from datetime import datetime
            
            favorites = load_favorites()
            
            # Buat data untuk disimpan
            favorite_data = {
                'doc_id': details.get('doc_id', ''),
                'title': details.get('Title', ''),
                'keywords': details.get('Keywords', ''),
                'abstract': details.get('Abstract', ''),
                'authors': details.get('Authors', ''),
                'domain': details.get('domain', ''),
                'specificity': details.get('specificity', ''),
                'publisher': details.get('Publisher', ''),
                'issue_date': details.get('Issue Date', ''),
                'link_detail': details.get('Link Detail', ''),
                'link_pdf': details.get('Link PDF', ''),
                'saved_at': datetime.now().isoformat()
            }
            
            # Cek apakah sudah ada di favorites
            if favorite_data['doc_id'] not in [f['doc_id'] for f in favorites]:
                favorites.append(favorite_data)
                save_favorites_func(favorites)
                st.success("✅ Berhasil disimpan ke favorites!")
            else:
                st.info("ℹ️ Dokumen ini sudah ada di favorites")
    
    st.markdown("</div>", unsafe_allow_html=True)