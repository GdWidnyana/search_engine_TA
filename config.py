"""
Configuration for Streamlit Application
Updated to use Blocked Dictionary + Front Coding
"""

from pathlib import Path
#C:\Users\Widnyana\Documents\TUGAS AKHIR\Program TA\streamlit_ir\data\blocks.json
# Paths - UPDATED untuk menggunakan dictionary
BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "data/index.json"
BLOCKS_PATH = BASE_DIR / "data/blocks.json"
FRONTCODED_PATH = BASE_DIR / "data/frontcoded.json"
HISTORY_PATH = BASE_DIR / "data/search_history.json"

# Page configuration
PAGE_CONFIG = {
    "page_title": "Skripsi Search Engine",
    "page_icon": "🔍",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "menu_items": {
        'Get Help': None,
        'Report a bug': None,
        'About': "Skripsi Search Engine v2.0 - Sistem Pencarian dengan Dictionary Optimization"
    }
}

# Custom CSS
CUSTOM_CSS = """
<style>
    /* Main theme */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }
    
    .block-container {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin-top: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    
    /* Header */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        font-weight: 400;
    }
    
    /* Search input */
    .stTextInput input {
        border-radius: 50px !important;
        padding: 15px 25px !important;
        font-size: 1rem !important;
        border: 2px solid #e0e0e0 !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput input:focus {
        border-color: #667eea !important;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 50px !important;
        padding: 10px 25px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        border: none !important;
    }
    
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    
    .stButton button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton button[kind="secondary"] {
        background: white !important;
        color: #667eea !important;
        border: 2px solid #667eea !important;
    }
    
    /* Result cards */
    .result-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .result-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        border-color: #667eea;
    }
    
    .result-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .result-number {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 50%;
        width: 35px;
        height: 35px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 1rem;
        flex-shrink: 0;
    }
    
    .result-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #333;
        line-height: 1.4;
    }
    
    /* Keywords */
    .keyword-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .keyword-badge {
        background: linear-gradient(135deg, #667eea20 0%, #764ba220 100%);
        color: #667eea;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        border: 1px solid #667eea40;
    }
    
    /* Metrics */
    .stMetric {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    
    .stMetric label {
        font-weight: 600 !important;
        color: #666 !important;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        color: #333 !important;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%);
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Info boxes */
    .stInfo {
        background: linear-gradient(135deg, #667eea10 0%, #764ba210 100%);
        border-left: 4px solid #667eea;
        border-radius: 10px;
    }
    
    .stSuccess {
        background: linear-gradient(135deg, #11998e10 0%, #38ef7d10 100%);
        border-left: 4px solid #11998e;
        border-radius: 10px;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #f7971e10 0%, #ffd20010 100%);
        border-left: 4px solid #f7971e;
        border-radius: 10px;
    }
    
    .stError {
        background: linear-gradient(135deg, #eb334910 0%, #f45c4310 100%);
        border-left: 4px solid #eb3349;
        border-radius: 10px;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
</style>
"""

# Search tips
SEARCH_TIPS = [
    "Gunakan kata kunci spesifik untuk hasil lebih akurat",
    "Gabungkan beberapa kata untuk pencarian lebih detail (contoh: 'machine learning klasifikasi')",
    "Sistem otomatis memperbaiki typo dan kata yang salah eja",
    "Query expansion otomatis menambahkan sinonim untuk hasil lebih lengkap",
    "Mode Advanced menampilkan score, domain, dan specificity untuk analisis mendalam",
    "✨ NEW: Menggunakan Dictionary Optimization untuk pencarian lebih cepat!"
]

# Example queries
EXAMPLE_QUERIES = [
    "machine learning",
    "user interface",
    "sistem rekomendasi",
    "chatbot",
    "keamanan data"
]

# Domain mapping
DOMAIN_NAMES = {
    'ml_ai': 'Machine Learning & AI',
    'nlp': 'NLP & Text Mining',
    'security': 'Security & Cryptography',
    'ui_ux': 'UI/UX & Design',
    'recommender': 'Recommender System',
    'medical': 'Medical & Health',
    'iot': 'IoT & Embedded',
    'business': 'Business Intelligence',
    'mobile': 'Mobile Development',
    'general': 'General'
}

# Specificity labels
SPECIFICITY_LABELS = {
    'specific': '🎯 Spesifik',
    'moderate': '📊 Moderat',
    'generic': '🌐 Umum'
}
