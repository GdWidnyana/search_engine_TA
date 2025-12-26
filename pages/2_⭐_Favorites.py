"""
Favorites Page - Manage saved documents
"""

import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime
import pandas as pd

# Add parent directory to path
PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import CUSTOM_CSS
from pages_utils import load_favorites, save_favorites_func
from detail_utils import render_document_detail, get_document_details
from timezone_utils import inject_timezone_detector, get_browser_time_info
from utils import parse_keywords
from reset_component import render_reset_menu
from utils import parse_and_convert_timestamp 

st.set_page_config(page_title="Favorites", page_icon="⭐", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def render_favorite_card(fav, index):
    """Render single favorite card"""
    # Dapatkan detail lengkap untuk mendapatkan link PDF dan link detail
    details = get_document_details(fav['doc_id'])
    
    st.markdown(f"""
        <div class="result-card">
            <div class="result-header">
                <span class="result-number">{index}</span>
                <span class="result-title">{fav['title']}</span>
            </div>
    """, unsafe_allow_html=True)
    
    # Keywords 
    if fav.get('keywords'):
        from utils import parse_keywords  # Pastikan import ini ada
        keywords = parse_keywords(fav['keywords'])  # Gunakan fungsi yang baru
            
        keyword_badges = " ".join([f'<span class="keyword-badge">{kw}</span>' for kw in keywords])
        st.markdown(f'<div class="keyword-container">{keyword_badges}</div>', unsafe_allow_html=True)
            
        # Tampilkan jumlah keyword
        st.markdown(f'<div style="font-size: 0.8rem; color: #666; margin-bottom: 10px;">Total keywords: {len(keywords)}</div>', unsafe_allow_html=True)
    
    # Abstract
    if fav.get('abstract'):
        st.markdown(f"**Abstract:** {fav['abstract']}")
    
    # Authors
    if fav.get('authors'):
        st.markdown(f"👤 **Penulis:** {fav['authors']}")
    
    # Links PDF dan Detail (jika ada) - DARI DETAIL, BUKAN DARI fav
    if details:
        # Tampilkan links dalam satu baris
        link_html = ""
        
        # Link Detail
        if details.get('Link Detail') and details.get('Link Detail').strip():
            link_html += f"""
                <a href="{details['Link Detail']}" target="_blank" style="
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    padding: 6px 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 500;
                    font-size: 0.9rem;
                    margin-right: 10px;
                    margin-bottom: 10px;
                ">
                    📖 Detail
                </a>
            """
        else:
            link_html += """
                <span style="
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    padding: 6px 12px;
                    background: #e2e8f0;
                    color: #718096;
                    border-radius: 6px;
                    font-weight: 500;
                    font-size: 0.9rem;
                    margin-right: 10px;
                    margin-bottom: 10px;
                ">
                    📖 Detail (tidak tersedia)
                </span>
            """
        
        # Link PDF
        if details.get('Link PDF') and details.get('Link PDF').strip():
            link_html += f"""
                <a href="{details['Link PDF']}" target="_blank" style="
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    padding: 6px 12px;
                    background: linear-gradient(135deg, #38a169 0%, #2f855a 100%);
                    color: white;
                    border-radius: 6px;
                    text-decoration: none;
                    font-weight: 500;
                    font-size: 0.9rem;
                    margin-right: 10px;
                    margin-bottom: 10px;
                ">
                    📥 PDF
                </a>
            """
        else:
            link_html += """
                <span style="
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    padding: 6px 12px;
                    background: #e2e8f0;
                    color: #718096;
                    border-radius: 6px;
                    font-weight: 500;
                    font-size: 0.9rem;
                    margin-right: 10px;
                    margin-bottom: 10px;
                ">
                    📥 PDF (tidak tersedia)
                </span>
            """
        
        if link_html:
            st.markdown(f"""
                <div style="margin-bottom: 15px;">
                    <strong style="color: #4a5568;">🔗 Links:</strong><br>
                    {link_html}
                </div>
            """, unsafe_allow_html=True)
    
    # Metadata dalam kolom
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Doc ID:** {fav['doc_id']}")
    with col2:
        if fav.get('saved_at'):
            try:
                # Konversi UTC ke WIB
                saved_dt = parse_and_convert_timestamp(fav['saved_at'], to_wib=True)
                saved_date = saved_dt.strftime('%d/%m/%Y %H:%M')
                st.markdown(f"**Disimpan:** {saved_date}")
                
                # Debug info
                if st.session_state.get('debug_time', False):
                    dt_utc = parse_and_convert_timestamp(fav['saved_at'], to_wib=False)
                    st.caption(f"UTC: {dt_utc.strftime('%d/%m/%Y %H:%M')}")
            except Exception as e:
                st.markdown(f"**Disimpan:** {fav['saved_at']}")
                print(f"Error parsing saved_at: {e}")
                
    with col3:
        if fav.get('domain'):
            st.markdown(f"**Domain:** {fav['domain'].upper()}")
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("📄 Detail", key=f"detail_fav_{fav['doc_id']}", use_container_width=True):
            st.session_state.show_detail = fav['doc_id']
    with col2:
        if st.button("🗑️ Hapus", key=f"remove_fav_{fav['doc_id']}", use_container_width=True):
            return True  # Signal to remove
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    return False

def create_favorites_pdf(favorites):
    """Create PDF report for all favorites"""
    try:
        from fpdf import FPDF
        import tempfile
        
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        for fav in favorites:
            pdf.add_page()
            
            # Use built-in fonts (no Unicode, ASCII only)
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, 'Favorites Report', 0, 1, 'C')
            pdf.ln(5)
            
            # Document info
            pdf.set_font('Arial', 'B', 12)
            
            # Clean title - remove non-ASCII characters
            title = fav.get('title', 'Untitled Document')
            title = title.encode('ascii', 'ignore').decode('ascii')[:100]
            if not title:
                title = "Untitled Document"
                
            pdf.cell(0, 10, title, 0, 1)
            pdf.ln(2)
            
            pdf.set_font('Arial', '', 10)
            
            # Clean text before adding to PDF
            doc_id = fav.get('doc_id', '').encode('ascii', 'ignore').decode('ascii')
            authors = fav.get('authors', '').encode('ascii', 'ignore').decode('ascii')[:100]
            domain = fav.get('domain', '').upper().encode('ascii', 'ignore').decode('ascii')
            
            pdf.cell(0, 8, f"Doc ID: {doc_id}", 0, 1)
            pdf.cell(0, 8, f"Penulis: {authors}", 0, 1)
            pdf.cell(0, 8, f"Domain: {domain}", 0, 1)
            
            # Format saved_at
            saved_at = fav.get('saved_at', '')
            if saved_at:
                try:
                    saved_date = datetime.fromisoformat(saved_at).strftime('%d/%m/%Y %H:%M')
                    pdf.cell(0, 8, f"Disimpan: {saved_date}", 0, 1)
                except:
                    pdf.cell(0, 8, "Disimpan: N/A", 0, 1)
            else:
                pdf.cell(0, 8, "Disimpan: N/A", 0, 1)
                
            pdf.ln(5)
            
            # Keywords - Clean
            if fav.get('keywords'):
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 8, "Keywords:", 0, 1)
                pdf.set_font('Arial', '', 10)
                
                from utils import parse_keywords
                keywords = parse_keywords(fav.get('keywords', ''))
                
                # Clean keywords
                clean_keywords = []
                for kw in keywords:
                    clean_kw = kw.encode('ascii', 'ignore').decode('ascii')
                    if clean_kw:
                        clean_keywords.append(clean_kw[:50])
                
                if clean_keywords:
                    keywords_text = " | ".join(clean_keywords[:20])  # Max 20 keywords
                    pdf.multi_cell(0, 8, keywords_text)
                else:
                    pdf.cell(0, 8, "No keywords available", 0, 1)
                    
                pdf.ln(3)
            
            # Abstract - Clean
            if fav.get('abstract'):
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 8, "Abstract:", 0, 1)
                pdf.set_font('Arial', '', 10)
                
                abstract = fav.get('abstract', '')
                clean_abstract = abstract.encode('ascii', 'ignore').decode('ascii')[:500]
                if len(abstract) > 500:
                    clean_abstract += "..."
                    
                pdf.multi_cell(0, 8, clean_abstract)
                pdf.ln(5)
            
            # Links
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, "Links:", 0, 1)
            pdf.set_font('Arial', '', 10)
            
            if fav.get('link_detail'):
                link = fav.get('link_detail', '')[:80]
                pdf.cell(0, 8, f"Detail: {link}", 0, 1)
            if fav.get('link_pdf'):
                link = fav.get('link_pdf', '')[:80]
                pdf.cell(0, 8, f"PDF: {link}", 0, 1)
            
            pdf.ln(10)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
        
        # Add summary page
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Summary', 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f"Total Documents: {len(favorites)}", 0, 1)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            return tmp_file.name
        
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        import traceback
        st.error(f"Traceback: {traceback.format_exc()}")
        return None

def create_favorites_excel(favorites):
    """Create Excel report for all favorites"""
    try:
        import tempfile
        import pandas as pd
        
        # Prepare data for Excel
        data = []
        for fav in favorites:
            # Parse keywords dengan fungsi yang benar
            keywords = parse_keywords(fav.get('keywords', ''))
            
            data.append({
                'Doc ID': fav.get('doc_id', ''),
                'Title': fav.get('title', ''),
                'Authors': fav.get('authors', ''),
                'Keywords': ', '.join(keywords),
                'Abstract': fav.get('abstract', '')[:500] + "..." if len(fav.get('abstract', '')) > 500 else fav.get('abstract', ''),
                'Domain': fav.get('domain', ''),
                'Specificity': fav.get('specificity', ''),
                'Publisher': fav.get('publisher', ''),
                'Issue Date': fav.get('issue_date', ''),
                'Link Detail': fav.get('link_detail', ''),
                'Link PDF': fav.get('link_pdf', ''),
                'Saved At': datetime.fromisoformat(fav.get('saved_at', '')).strftime('%d/%m/%Y %H:%M') if fav.get('saved_at') else ''
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Save to temporary Excel file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Favorites', index=False)
                
                # Format the worksheet
                worksheet = writer.sheets['Favorites']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return tmp_file.name
        
    except Exception as e:
        st.error(f"Error creating Excel: {e}")
        return None

def main():
    # Inject timezone detector
    inject_timezone_detector()
    
    # Check if detail should be shown
    if 'show_detail' in st.session_state and st.session_state.show_detail:
        st.markdown("---")
        render_document_detail(st.session_state.show_detail)
        if st.button("✖️ Tutup Detail", use_container_width=True, type="secondary"):
            del st.session_state.show_detail
            st.rerun()
        return
    
    st.markdown("""
        <div class="main-header">
            <h1>⭐ Favorites</h1>
            <p class="subtitle">Dokumen yang telah Anda simpan</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Load favorites
    favorites = load_favorites()

    if not favorites:
        st.info("📭 Belum ada dokumen favorit. Simpan dokumen dari hasil pencarian untuk menambahkan ke favorites.")
        render_reset_menu()
        return
    
    # Stats
    st.markdown(f"### 📚 Total: {len(favorites)} dokumen")

    # Sort options - FIX ALIGNMENT
    col1, col2 = st.columns([4, 2])

    with col1:
        sort_by = st.selectbox(
            "Urutkan berdasarkan",
            ["Terbaru", "Terlama", "Judul A-Z", "Judul Z-A"],
            key="sort_select"
        )

    with col2:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)

        delete_clicked = st.button(
            "🗑️ Hapus Semua",
            use_container_width=True,
            type="secondary"
        )

        if delete_clicked:
            if st.session_state.get("confirm_delete_all"):
                save_favorites_func([])
                st.success("✅ Semua favorites berhasil dihapus!")
                st.session_state.confirm_delete_all = False
                st.rerun()
            else:
                st.session_state.confirm_delete_all = True
                st.warning("⚠️ Klik sekali lagi untuk konfirmasi hapus semua")
                st.rerun()
    
    # Sort favorites
    if sort_by == "Terbaru":
        favorites_sorted = sorted(favorites, key=lambda x: x.get('saved_at', ''), reverse=True)
    elif sort_by == "Terlama":
        favorites_sorted = sorted(favorites, key=lambda x: x.get('saved_at', ''))
    elif sort_by == "Judul A-Z":
        favorites_sorted = sorted(favorites, key=lambda x: x.get('title', ''))
    else:  # Z-A
        favorites_sorted = sorted(favorites, key=lambda x: x.get('title', ''), reverse=True)
    
    st.markdown("---")
    
    # Render favorites
    to_remove = []
    for i, fav in enumerate(favorites_sorted, 1):
        should_remove = render_favorite_card(fav, i)
        if should_remove:
            to_remove.append(fav['doc_id'])
    
    # Remove items
    if to_remove:
        updated_favorites = [f for f in favorites if f['doc_id'] not in to_remove]
        save_favorites_func(updated_favorites)
        st.success(f"✅ {len(to_remove)} dokumen berhasil dihapus!")
        st.rerun()
    
    # Export options - SINGLE CLICK
    # Export options - PERBAIKAN: PDF dan Excel
    st.markdown("---")
    st.markdown("### 💾 Export Favorites")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if favorites:
            # PDF Export
            if st.button("📥 Export PDF", use_container_width=True):
                pdf_path = create_favorites_pdf(favorites)
                if pdf_path:
                    with open(pdf_path, 'rb') as f:
                        pdf_bytes = f.read()
                    
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"favorites_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        else:
            st.button("📥 Export PDF", disabled=True, use_container_width=True)
    
    with col2:
        if favorites:
            # Excel Export
            if st.button("📊 Export Excel", use_container_width=True):
                excel_path = create_favorites_excel(favorites)
                if excel_path:
                    with open(excel_path, 'rb') as f:
                        excel_bytes = f.read()
                    
                    st.download_button(
                        label="📥 Download Excel Report",
                        data=excel_bytes,
                        file_name=f"favorites_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        else:
            st.button("📊 Export Excel", disabled=True, use_container_width=True)
    
    render_reset_menu()

if __name__ == "__main__":
    main()
