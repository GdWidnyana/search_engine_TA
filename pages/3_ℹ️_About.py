"""
About Page - System Information and Documentation
"""

import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path
PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import CUSTOM_CSS, INDEX_PATH
from utils import load_search_history
from pages_utils import load_favorites

st.set_page_config(page_title="About", page_icon="ℹ️", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def load_index_stats():
    """Load statistics from index file"""
    try:
        if INDEX_PATH.exists():
            with open(INDEX_PATH, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            return {
                'total_documents': len(index_data.get('documents', [])),
                'total_terms': len(index_data.get('index', {})),
                'index_version': index_data.get('metadata', {}).get('version', 'N/A'),
                'created_at': index_data.get('metadata', {}).get('created_at', 'N/A'),
                'has_domain_classifier': 'domain_classifier' in index_data,
                'has_specificity': 'specificity_scores' in index_data
            }
        else:
            return None
    except:
        return None


def render_system_info():
    """Render system information"""
    st.markdown("""
        <div class="main-header">
            <h1>ℹ️ Tentang Sistem</h1>
            <p class="subtitle">Informasi lengkap tentang Skripsi Search Engine</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🎯 Overview")
    
    st.markdown("""
    **Skripsi Search Engine** adalah sistem pencarian dokumen skripsi berbasis algoritma **BM25 (Best Match 25)** 
    yang dioptimalkan dengan berbagai fitur advanced untuk memberikan hasil pencarian yang akurat dan relevan.
    
    Sistem ini dikembangkan sebagai bagian dari penelitian tugas akhir dengan fokus pada:
    - Information Retrieval menggunakan algoritma BM25
    - Query expansion dengan sinonim dan stemming
    - Domain classification untuk kategorisasi dokumen
    - Specificity scoring untuk menentukan kekhususan dokumen
    - User interface yang modern dan responsif
    """)


def render_features():
    """Render features list"""
    st.markdown("## ✨ Fitur Utama")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🔍 Core Features
        - **BM25 Ranking Algorithm**: Algoritma ranking state-of-the-art untuk IR
        - **Query Expansion**: Ekspansi query otomatis dengan sinonim
        - **Stemming**: Normalisasi kata dengan Sastrawi stemmer
        - **Typo Correction**: Koreksi kesalahan ketik otomatis
        - **Boolean Operators**: Support untuk AND, OR, NOT operators
        
        ### 🎨 User Interface
        - **Modern Design**: Interface yang clean dan intuitif
        - **Responsive Layout**: Optimal di berbagai ukuran layar
        - **Dark Mode Ready**: CSS variables untuk tema gelap
        - **Interactive Components**: Smooth animations dan transitions
        - **Real-time Search**: Hasil pencarian instant
        """)
    
    with col2:
        st.markdown("""
        ### 🏷️ Advanced Features
        - **Domain Classification**: Klasifikasi otomatis ke 9+ domain
        - **Specificity Scoring**: Penilaian kekhususan dokumen
        - **Advanced Mode**: Informasi detail untuk analisis
        - **Sorting Options**: Multiple opsi pengurutan hasil
        - **Domain Filtering**: Filter hasil berdasarkan domain
        
        ### 📊 Analytics & History
        - **Search History**: Tracking semua pencarian
        - **Usage Statistics**: Analisis pola penggunaan
        - **Performance Metrics**: Monitoring kecepatan pencarian
        - **Export Functions**: Export ke CSV/JSON
        - **Favorites System**: Simpan dokumen favorit
        """)


def render_algorithm_info():
    """Render algorithm information"""
    st.markdown("## 🧮 Algoritma BM25")
    
    st.markdown("""
    ### Penjelasan BM25
    
    BM25 (Best Match 25) adalah algoritma ranking probabilistik yang digunakan untuk 
    menghitung relevansi dokumen terhadap query pencarian.
    
    **Formula BM25:**
    """)
    
    st.latex(r'''
    \text{Score}(D,Q) = \sum_{i=1}^{n} \text{IDF}(q_i) \cdot \frac{f(q_i, D) \cdot (k_1 + 1)}{f(q_i, D) + k_1 \cdot (1 - b + b \cdot \frac{|D|}{\text{avgdl}})}
    ''')
    
    st.markdown("""
    **Keterangan:**
    - `D` = Dokumen
    - `Q` = Query
    - `f(qi, D)` = Frekuensi term qi dalam dokumen D
    - `|D|` = Panjang dokumen D
    - `avgdl` = Rata-rata panjang dokumen dalam koleksi
    - `k1` = Parameter tuning (default: 1.5)
    - `b` = Parameter tuning untuk length normalization (default: 0.75)
    - `IDF(qi)` = Inverse Document Frequency dari term qi
    
    ### Parameter Tuning
    
    Sistem ini menggunakan parameter optimal:
    - **k1 = 1.5**: Mengontrol term frequency saturation
    - **b = 0.75**: Mengontrol pengaruh panjang dokumen
    - **k3 = 1000**: Mengontrol query term frequency (untuk query expansion)
    
    ### Query Expansion
    
    Sistem melakukan ekspansi query dengan:
    1. **Stemming**: Normalisasi kata ke bentuk dasar (Sastrawi)
    2. **Synonym Expansion**: Menambahkan sinonim dari thesaurus
    3. **Typo Correction**: Memperbaiki kesalahan ketik
    4. **Boolean Operators**: Support AND, OR, NOT
    """)


def render_domain_classification():
    """Render domain classification info"""
    st.markdown("## 🏷️ Domain Classification")
    
    st.markdown("""
    Sistem mengklasifikasikan dokumen ke dalam 9+ domain utama menggunakan 
    keyword-based classification dengan weighted scoring.
    
    ### Domain yang Didukung:
    """)
    
    domains = {
        "🤖 Machine Learning & AI": "Sistem pembelajaran mesin, neural networks, deep learning, artificial intelligence",
        "💬 NLP & Text Mining": "Natural language processing, text analysis, sentiment analysis, topic modeling",
        "🔐 Security & Cryptography": "Keamanan sistem, enkripsi, kriptografi, network security",
        "🎨 UI/UX & Design": "User interface, user experience, design thinking, usability",
        "⭐ Recommender System": "Sistem rekomendasi, collaborative filtering, content-based filtering",
        "🏥 Medical & Health": "Aplikasi kesehatan, medical imaging, healthcare systems",
        "📡 IoT & Embedded": "Internet of Things, embedded systems, sensor networks",
        "📊 Business Intelligence": "Data analytics, business analysis, decision support systems",
        "📱 Mobile Development": "Aplikasi mobile, Android, iOS, cross-platform"
    }
    
    for domain, desc in domains.items():
        with st.expander(domain):
            st.markdown(f"**Deskripsi:** {desc}")


def render_specificity_scoring():
    """Render specificity scoring info"""
    st.markdown("## 🎯 Specificity Scoring")
    
    st.markdown("""
    Sistem menilai tingkat kekhususan dokumen berdasarkan beberapa faktor:
    
    ### Metrik yang Digunakan:
    
    1. **Keyword Density**: Kepadatan kata kunci dalam dokumen
    2. **Title Relevance**: Relevansi judul dengan domain
    3. **Abstract Quality**: Kualitas dan panjang abstrak
    4. **Domain Confidence**: Kepercayaan klasifikasi domain
    
    ### Kategori Specificity:
    
    - **🎯 Specific (Spesifik)**: Score > 0.7
      - Dokumen sangat fokus pada topik tertentu
      - Kata kunci domain sangat dominan
      - Judul dan abstrak sangat relevan
    
    - **📊 Moderate (Moderat)**: Score 0.4 - 0.7
      - Dokumen cukup fokus
      - Kombinasi beberapa topik related
      - Relevansi sedang
    
    - **🌐 Generic (Umum)**: Score < 0.4
      - Dokumen bersifat umum
      - Tidak terfokus pada domain spesifik
      - Kata kunci generik
    """)


def render_system_statistics():
    """Render system statistics"""
    st.markdown("## 📊 Statistik Sistem")
    
    # Load statistics
    index_stats = load_index_stats()
    history = load_search_history()
    favorites = load_favorites()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📚 Koleksi Dokumen")
        if index_stats:
            st.metric("Total Dokumen", index_stats['total_documents'])
            st.metric("Total Term", f"{index_stats['total_terms']:,}")
            st.metric("Versi Index", index_stats['index_version'])
        else:
            st.warning("Index tidak ditemukan")
    
    with col2:
        st.markdown("### 🔍 Aktivitas Pencarian")
        st.metric("Total Pencarian", len(history))
        unique_queries = len(set(entry['query'] for entry in history))
        st.metric("Query Unik", unique_queries)
        if history:
            avg_results = sum(entry.get('num_results', 0) for entry in history) / len(history)
            st.metric("Avg. Hasil", f"{avg_results:.1f}")
    
    with col3:
        st.markdown("### ⭐ Favorites")
        st.metric("Total Favorites", len(favorites))
        if favorites:
            domains = [f.get('domain', 'general') for f in favorites]
            most_common = max(set(domains), key=domains.count) if domains else 'N/A'
            st.metric("Domain Populer", most_common.upper())


def render_tech_stack():
    """Render technology stack"""
    st.markdown("## 🛠️ Technology Stack")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Backend
        - **Python 3.8+**: Core programming language
        - **NumPy**: Numerical computations
        - **Pandas**: Data manipulation
        - **Sastrawi**: Indonesian stemmer
        - **scikit-learn**: Machine learning utilities
        
        ### Frontend
        - **Streamlit**: Web application framework
        - **HTML/CSS**: Custom styling
        - **JavaScript**: Interactive components
        """)
    
    with col2:
        st.markdown("""
        ### Data & Storage
        - **JSON**: Index and data storage
        - **CSV**: Export functionality
        - **File System**: Document storage
        
        ### Development
        - **Git**: Version control
        - **VS Code**: Development environment
        - **Python venv**: Virtual environment
        """)


def render_usage_guide():
    """Render usage guide"""
    st.markdown("## 📖 Panduan Penggunaan")
    
    with st.expander("🔍 Cara Melakukan Pencarian"):
        st.markdown("""
        1. Masukkan kata kunci di search box
        2. Klik tombol **🔍 Cari** atau tekan Enter
        3. Hasil akan muncul dengan ranking berdasarkan relevansi
        4. Gunakan contoh query untuk pencarian cepat
        
        **Tips:**
        - Gunakan kata kunci spesifik untuk hasil lebih akurat
        - Gabungkan beberapa kata untuk pencarian detail
        - Sistem otomatis memperbaiki typo
        - Query expansion menambahkan sinonim
        """)
    
    with st.expander("⚙️ Mode Advanced"):
        st.markdown("""
        Aktifkan **Mode Advanced** untuk melihat:
        - **Score**: Nilai relevansi dokumen
        - **Domain**: Kategori domain dokumen
        - **Specificity**: Tingkat kekhususan dokumen
        
        Mode ini berguna untuk:
        - Analisis mendalam hasil pencarian
        - Evaluasi kualitas ranking
        - Research dan development
        """)
    
    with st.expander("🎯 Filter dan Sorting"):
        st.markdown("""
        **Filter Domain:**
        - Pilih domain spesifik untuk menyaring hasil
        - Hanya dokumen dari domain terpilih yang ditampilkan
        
        **Sorting Options:**
        - **Relevansi (Score)**: Urutkan berdasarkan skor BM25
        - **Terbaru**: Urutkan dari dokumen terbaru
        - **Judul A-Z**: Urutkan alfabetis
        """)
    
    with st.expander("⭐ Favorites"):
        st.markdown("""
        1. Klik tombol **💾 Simpan** pada hasil pencarian
        2. Dokumen tersimpan di halaman Favorites
        3. Akses cepat dokumen penting
        4. Export favorites ke JSON/CSV
        5. Hapus dokumen yang tidak diperlukan
        """)
    
    with st.expander("📊 Analytics"):
        st.markdown("""
        Halaman Analytics menyediakan:
        - **Overview Metrics**: Statistik pencarian keseluruhan
        - **Search Trends**: Grafik tren pencarian harian
        - **Top Queries**: Query paling sering dicari
        - **Popular Keywords**: Kata kunci yang trending
        - **Domain Distribution**: Sebaran domain yang dicari
        - **Performance Stats**: Metrik performa sistem
        - **Recent Searches**: History pencarian terbaru
        
        Export data dalam format CSV/JSON untuk analisis lebih lanjut.
        """)


def render_contact_info():
    """Render contact and credits"""
    st.markdown("## 👨‍💻 Credits & Contact")
    
    st.markdown("""
    ### 👨‍💻 Developed by: **KELOMPOK 4 - TEMU KEMBALI INFORMASI TEKSTUAL**
    - 1.	I Gede Widnyana         (2208561016)
    - 2.	Ni Kadek Yuni Suratri	(2208561050)
    - 3.	I Komang Dwiprayoga		(2208561117)
    
    **Program Studi Informatika**  
    **Universitas Udayana**
    
    ### 👨‍🏫 Dosen Pengampu Mata Kuliah:
    - **Dr. Ir. Ngurah Agus Sanjaya ER, S.Kom., M.Kom**
    
    ### ☎️ Contact:
    - 📧 Email: widnyana.2208561016@student.unud.ac.id
    - 💼 LinkedIn: https://www.linkedin.com/in/i-gede-widnyana
    - 🐙 GitHub: https://github.com/GdWidnyana
    
    ### ℹ️ Version Information:
    - **Version**: 1.0.0
    - **Release Date**: December 2024
    - **Last Update**: """ + datetime.now().strftime('%d %B %Y') + """
    
    ---
    
    ### 🙏 Acknowledgments
    
    Terima kasih kepada:
    - Dosen pengampu mata kuliah yang telah membimbing project ini
    - Teman-teman developer yang berkontribusi mengembangkan project ini
    - Komunitas open source yang menyediakan tools dan libraries
    """)


def render_license():
    """Render license information"""
    st.markdown("## 📄 License")
    
    st.markdown("""
    This project is developed as part of academic research.
    
    **Usage Terms:**
    - This system is intended for educational and research purposes
    - Commercial use requires permission from the author
    - Citation is required if used for academic purposes
    
    **Citation Format:**
    ```
    Widnyana, I.G., Suratri, N.K.Y., Dwiprayoga, I.K. (2025). Skripsi Search Engine: 
    Sistem Pencarian Dokumen Skripsi Berbasis BM25.
    Project Information Retrieval, Program Studi Informatika, 
    Universitas Udayana.
    ```
    """)


def main():
    render_system_info()
    
    st.markdown("---")
    render_features()
    
    st.markdown("---")
    render_algorithm_info()
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        render_domain_classification()
    with col2:
        render_specificity_scoring()
    
    st.markdown("---")
    render_system_statistics()
    
    st.markdown("---")
    render_tech_stack()
    
    st.markdown("---")
    render_usage_guide()
    
    st.markdown("---")
    render_contact_info()
    
    st.markdown("---")
    render_license()
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p><strong>Skripsi Search Engine v1.0</strong></p>
            <p>Project Information Retrieval</p>
            <p>©2025 - Built with ❤️ Team 4</p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()