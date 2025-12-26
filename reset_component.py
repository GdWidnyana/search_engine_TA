"""
Reset Component - Reusable reset menu for all pages
"""

import streamlit as st
import time
from utils import reset_all_data


def render_reset_menu():
    """Render reset menu in sidebar with confirmation - Reusable component"""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🔄 Reset Data")
        
        # Buat popover untuk konfirmasi
        with st.popover("🗑️ Reset Semua Data", use_container_width=True):
            st.warning("⚠️ **Konfirmasi Reset**")
            st.markdown("""
                Anda akan menghapus:
                - ✅ Semua riwayat pencarian
                - ✅ Semua data favorites
                - ✅ Semua data analytics
                
                **Tindakan ini tidak dapat dibatalkan!**
            """)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Ya, Hapus", 
                            use_container_width=True, 
                            type="primary",
                            key="confirm_reset_yes"):
                    # Perform reset
                    if reset_all_data():
                        # Clear session state
                        keys_to_clear = [
                            'search_history', 
                            'current_results', 
                            'query', 
                            'show_detail'
                        ]
                        
                        for key in keys_to_clear:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        st.success("✅ Semua data berhasil dihapus!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error("❌ Gagal menghapus data!")
            
            with col2:
                if st.button("❌ Batal", 
                            use_container_width=True,
                            key="confirm_reset_no"):
                    # Tutup popover (tidak perlu action khusus)
                    pass