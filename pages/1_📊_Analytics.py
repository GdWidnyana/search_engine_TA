"""
Analytics Dashboard - Search statistics and insights
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from timezone_utils import inject_timezone_detector, get_browser_time_info, adjust_datetime_to_local
from utils import parse_and_convert_timestamp
import sys
from pathlib import Path

# Add parent directory to path
PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import CUSTOM_CSS, DOMAIN_NAMES
from utils import (
    load_search_history, 
    get_search_stats, 
    create_index_summary,
    parse_timestamp_to_wib,
    format_datetime_for_display,
    get_current_wib_datetime
)
from pages_utils import load_favorites
from reset_component import render_reset_menu

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_analytics_header():
    """Render analytics header"""
    st.markdown("""
        <div class="main-header">
            <h1>📊 Analytics Dashboard</h1>
            <p class="subtitle">Statistik dan insights sistem pencarian</p>
        </div>
    """, unsafe_allow_html=True)

def render_search_stats(history):
    """Render search statistics"""
    stats = get_search_stats(history)
    
    if not history:
        st.info("📊 Belum ada data pencarian. Mulai pencarian untuk melihat statistik.")
        return
    
    # Debug info di sidebar
    with st.sidebar.expander("🕒 Time Debug Info", expanded=False):
        if history and len(history) > 0:
            sample_entry = history[0]
            st.write(f"**Sample timestamp:** {sample_entry.get('timestamp')}")
            
            # Parse dan tampilkan
            dt_parsed = parse_timestamp_to_wib(sample_entry['timestamp'])
            st.write(f"**Parsed as WIB:** {dt_parsed}")
            st.write(f"**Formatted:** {format_datetime_for_display(dt_parsed, 'date_time')}")
            
            # Current times
            st.write(f"**Current UTC:** {datetime.now(timezone.utc).strftime('%H:%M:%S')}")
            st.write(f"**Current WIB:** {get_current_wib_datetime().strftime('%H:%M:%S')}")
            st.write(f"**Current Server:** {datetime.now().strftime('%H:%M:%S')}")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Pencarian", stats['total_searches'])
    
    with col2:
        st.metric("Query Unik", stats['unique_queries'])
    
    with col3:
        st.metric("Rata-rata Hasil", f"{stats['avg_results']:.1f}")
    
    with col4:
        st.metric("Pencarian Hari Ini", stats['today_searches'])
    
    st.markdown("---")
    
    # Charts in tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Tren Pencarian",
        "🔝 Query Populer", 
        "🕒 Performa Waktu",
        "📄 Distribusi Hasil"
    ])
    
    with tab1:
        render_search_trends(history)
    
    with tab2:
        render_popular_queries(stats)
    
    with tab3:
        render_performance_stats(stats, history)
    
    with tab4:
        render_result_distribution(history)


def render_search_trends(history):
    """Render search trends over time"""
    if not history:
        st.info("Belum ada data untuk tren")
        return
    
    # Create DataFrame dengan parsing ke WIB
    df_data = []
    for entry in history:
        try:
            # Parse ke WIB
            dt = parse_timestamp_to_wib(entry['timestamp'])
            
            df_data.append({
                'date': dt.date(),
                'hour': dt.hour,
                'query': entry['query'],
                'results': entry.get('num_results', 0),
                'search_time': entry.get('search_time', 0)
            })
        except Exception as e:
            print(f"Error parsing entry: {e}")
            continue
    
    if not df_data:
        st.warning("Tidak dapat memproses data")
        return
    
    df = pd.DataFrame(df_data)
    
    # Daily trends
    daily_counts = df.groupby('date').size().reset_index(name='count')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📅 Tren Harian")
        fig = px.line(
            daily_counts, 
            x='date', 
            y='count',
            markers=True,
            line_shape='spline'
        )
        fig.update_layout(
            xaxis_title="Tanggal",
            yaxis_title="Jumlah Pencarian",
            plot_bgcolor='rgba(0,0,0,0)',
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 🕐 Pencarian Terbaru")
        
        # Tabel pencarian terbaru - tampilkan dalam WIB
        recent_searches = history[-10:][::-1]
        table_data = []
        for entry in recent_searches:
            dt = parse_timestamp_to_wib(entry['timestamp'])
            table_data.append({
                'timestamp': format_datetime_for_display(dt, 'full'),
                'query': entry['query'],
                'hasil': entry.get('num_results', 0),
                'waktu_ms': f"{entry.get('search_time', 0)*1000:.2f}"
            })
        
        if table_data:
            table_df = pd.DataFrame(table_data)
            st.dataframe(
                table_df,
                column_config={
                    'timestamp': 'Waktu (WIB)',
                    'query': 'Query',
                    'hasil': 'Hasil',
                    'waktu_ms': 'Waktu (ms)'
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("Belum ada data pencarian")

def render_popular_queries(stats):
    """Render popular queries"""
    if not stats['top_queries']:
        st.info("Belum ada data query populer")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔝 10 Query Terpopuler")
        top_queries_df = pd.DataFrame(
            stats['top_queries'][:10], 
            columns=['Query', 'Frekuensi']
        )
        fig = px.bar(
            top_queries_df,
            x='Frekuensi',
            y='Query',
            orientation='h',
            color='Frekuensi',
            color_continuous_scale='purples'
        )
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=400,
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📋 Detail Query")
        for query, count in stats['top_queries'][:10]:
            st.markdown(f"**{query}** - {count}x pencarian")
            st.progress(min(count / stats['top_queries'][0][1], 1.0))
    
    # Debug info untuk melihat waktu
    with st.expander("🕒 Debug Time Info", expanded=False):
        if history and len(history) > 0:
            sample_entry = history[0]
            st.write(f"Sample timestamp from DB: {sample_entry.get('timestamp')}")
            # Perbaiki: gunakan fungsi dari utils
            from utils import parse_and_convert_timestamp
            dt_utc = parse_and_convert_timestamp(sample_entry['timestamp'], to_wib=False)
            dt_wib = parse_and_convert_timestamp(sample_entry['timestamp'], to_wib=True)
            st.write(f"UTC: {dt_utc}")
            st.write(f"WIB: {dt_wib}")
            st.write(f"Server time now: {datetime.now()}")
            from datetime import timezone
            st.write(f"UTC time now: {datetime.now(timezone.utc)}")


def render_performance_stats(stats, history):
    """Render performance statistics"""
    if not history:
        st.info("Belum ada data performa")
        return
    
    # Calculate performance metrics
    search_times = [h.get('search_time', 0) for h in history]
    results_counts = [h.get('num_results', 0) for h in history]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ⚡ Performa Waktu Pencarian")
        
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        
        with metrics_col1:
            avg_time = sum(search_times) / len(search_times) * 1000
            st.metric("Rata-rata", f"{avg_time:.0f} ms")
        
        with metrics_col2:
            min_time = min(search_times) * 1000
            st.metric("Tercepat", f"{min_time:.0f} ms")
        
        with metrics_col3:
            max_time = max(search_times) * 1000
            st.metric("Tertinggi", f"{max_time:.0f} ms")
        
        # Time distribution
        time_df = pd.DataFrame({'waktu_ms': [t * 1000 for t in search_times]})
        fig = px.histogram(
            time_df,
            x='waktu_ms',
            nbins=20,
            title="Distribusi Waktu Pencarian"
        )
        fig.update_layout(
            xaxis_title="Waktu (ms)",
            yaxis_title="Frekuensi",
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📊 Distribusi Query User")
        
        # Buat DataFrame untuk query vs jumlah hasil
        query_results = {}
        for entry in history:
            query = entry['query']
            num_results = entry.get('num_results', 0)
            if query not in query_results:
                query_results[query] = []
            query_results[query].append(num_results)
        
        # Rata-rata hasil per query
        avg_results_per_query = []
        for query, results in query_results.items():
            avg_results = sum(results) / len(results)
            avg_results_per_query.append({
                'Query': query[:30] + '...' if len(query) > 30 else query,
                'Jumlah Hasil': avg_results
            })
        
        # Urutkan dan ambil top 10
        avg_results_df = pd.DataFrame(avg_results_per_query)
        avg_results_df = avg_results_df.sort_values('Jumlah Hasil', ascending=False).head(10)
        
        fig = px.bar(
            avg_results_df,
            x='Query',
            y='Jumlah Hasil',
            title="Rata-rata Hasil per Query (Top 10)",
            color='Jumlah Hasil',
            color_continuous_scale='viridis'
        )
        fig.update_layout(
            xaxis_title="Query",
            yaxis_title="Jumlah Hasil",
            height=300,
            xaxis_tickangle=45
        )
        st.plotly_chart(fig, use_container_width=True)

def render_result_distribution(history):
    """Render result distribution analysis"""
    if not history:
        return
    
    # Analyze success rate
    successful_searches = [h for h in history if h.get('num_results', 0) > 0]
    success_rate = (len(successful_searches) / len(history)) * 100
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 🎯 Success Rate")
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=success_rate,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Rate Keberhasilan"},
            gauge={'axis': {'range': [0, 100]},
                  'bar': {'color': "#667eea"},
                  'steps': [
                      {'range': [0, 50], 'color': "lightgray"},
                      {'range': [50, 80], 'color': "gray"},
                      {'range': [80, 100], 'color': "darkgray"}
                  ]}
        ))
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### 📈 Tren Keberhasilan")
        
        # Group by day - HANYA TANGGAL
        df_data = []
        for entry in history:
            dt = datetime.fromisoformat(entry['timestamp'])
            df_data.append({
                'date': dt.date(),
                'successful': 1 if entry.get('num_results', 0) > 0 else 0
            })
        
        df = pd.DataFrame(df_data)
        daily_success = df.groupby('date')['successful'].mean().reset_index()
        
        fig = px.line(
            daily_success,
            x='date',
            y='successful',
            title="Tren Rate Keberhasilan Harian",
            markers=True,
            line_shape='spline'
        )
        fig.update_layout(
            xaxis_title="Tanggal",
            yaxis_title="Rate Keberhasilan",
            yaxis_tickformat=".0%",
            height=250,
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)
        
# def render_result_distribution(history):
#     """Render result distribution analysis"""
#     if not history:
#         return
    
#     # Analyze success rate
#     successful_searches = [h for h in history if h.get('num_results', 0) > 0]
#     success_rate = (len(successful_searches) / len(history)) * 100
    
#     col1, col2, col3 = st.columns(3)
    
#     with col1:
#         st.markdown("#### 🎯 Success Rate")
#         fig = go.Figure(go.Indicator(
#             mode="gauge+number",
#             value=success_rate,
#             domain={'x': [0, 1], 'y': [0, 1]},
#             title={'text': "Rate Keberhasilan"},
#             gauge={'axis': {'range': [0, 100]},
#                   'bar': {'color': "#667eea"},
#                   'steps': [
#                       {'range': [0, 50], 'color': "lightgray"},
#                       {'range': [50, 80], 'color': "gray"},
#                       {'range': [80, 100], 'color': "darkgray"}
#                   ]}
#         ))
#         fig.update_layout(height=250)
#         st.plotly_chart(fig, use_container_width=True)
    
#     with col2:
#         st.markdown("#### 📈 Tren Keberhasilan")
        
#         # Group by day
#         df_data = []
#         for entry in history:
#             dt = datetime.fromisoformat(entry['timestamp'])
#             df_data.append({
#                 'date': dt.date(),
#                 'successful': 1 if entry.get('num_results', 0) > 0 else 0
#             })
        
#         df = pd.DataFrame(df_data)
#         daily_success = df.groupby('date')['successful'].mean().reset_index()
        
#         fig = px.line(
#             daily_success,
#             x='date',
#             y='successful',
#             title="Tren Rate Keberhasilan Harian"
#         )
#         fig.update_layout(
#             xaxis_title="Tanggal",
#             yaxis_title="Rate Keberhasilan",
#             yaxis_tickformat=".0%",
#             height=250
#         )
#         st.plotly_chart(fig, use_container_width=True)


def render_index_analytics():
    """Render index file analytics"""
    from config import INDEX_PATH
    
    st.markdown("---")
    st.markdown("### 📁 Index Analytics")
    
    summary = create_index_summary(INDEX_PATH)
    
    if not summary:
        st.warning("Index file tidak ditemukan atau error")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Dokumen", summary['total_documents'])
    
    with col2:
        st.metric("Total Keywords", summary['total_keywords'])
    
    with col3:
        st.metric("Avg Keywords/Doc", f"{summary['avg_keywords_per_doc']:.1f}")
    
    with col4:
        st.metric("Ukuran File", summary['file_size'])
    
    # Domain distribution
    st.markdown("#### 🏷️ Distribusi Domain")
    
    if summary.get('domains'):
        domains_data = []
        for domain, count in summary['domains'].items():
            domains_data.append({
                'Domain': DOMAIN_NAMES.get(domain, domain.title()),
                'Count': count,
                'Percentage': (count / summary['total_documents']) * 100
            })
        
        domains_df = pd.DataFrame(domains_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(
                domains_df,
                values='Count',
                names='Domain',
                title="Distribusi Domain",
                hole=0.4
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                domains_df.sort_values('Count', ascending=True),
                x='Count',
                y='Domain',
                orientation='h',
                color='Count',
                title="Jumlah Dokumen per Domain"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def render_favorites_analytics():
    """Render favorites analytics"""
    favorites = load_favorites()
    
    if not favorites:
        return
    
    st.markdown("---")
    st.markdown("### ⭐ Favorites Analytics")
    
    total_favorites = len(favorites)
    
    # Count by domain
    domain_counts = {}
    for fav in favorites:
        domain = fav.get('domain', 'general')
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Favorites", total_favorites)
    
    with col2:
        # Most saved domain
        if domain_counts:
            top_domain = max(domain_counts.items(), key=lambda x: x[1])
            st.metric(
                "Domain Terpopuler", 
                DOMAIN_NAMES.get(top_domain[0], top_domain[0].title())
            )
    
    with col3:
        avg_keywords = sum(len(f.get('keywords', '').split()) for f in favorites) / total_favorites
        st.metric("Avg Keywords", f"{avg_keywords:.1f}")


# def main():
#     render_analytics_header()
    
#     # Load data
#     history = load_search_history()
    
#     # Main tabs
#     tab1, tab2 = st.tabs(["📊 Search Analytics", "📁 System Insights"])
    
#     with tab1:
#         render_search_stats(history)
#         render_favorites_analytics()
    
#     with tab2:
#         render_index_analytics()
        
#         # System information
#         st.markdown("---")
#         st.markdown("### 🖥️ System Information")
        
#         import platform
#         import psutil
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             st.markdown("**Platform:**")
#             st.code(f"""
#                 System: {platform.system()} {platform.release()}
#                 Python: {platform.python_version()}
#                 Streamlit: {st.__version__}
#                 CPU Cores: {psutil.cpu_count()}
#                 RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB
#             """)
        
#         with col2:
#             st.markdown("**Data Information:**")
#             st.code(f"""
#                 Search History: {len(history)} entries
#                 Favorites: {len(load_favorites())} items
#                 Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M')}
#             """)
        
#         # Export data
#         st.markdown("---")
#         st.markdown("### 💾 Export Data")
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             if st.button("📥 Export Search History", use_container_width=True):
#                 import json
#                 from io import BytesIO
                
#                 history_json = json.dumps(history, indent=2, ensure_ascii=False)
                
#                 st.download_button(
#                     label="Download JSON",
#                     data=history_json,
#                     file_name=f"search_history_{datetime.now().strftime('%Y%m%d')}.json",
#                     mime="application/json",
#                     use_container_width=True
#                 )
        
#         with col2:
#             if st.button("📊 Export Analytics Report", use_container_width=True):
#                 stats = get_search_stats(history)
#                 stats_json = json.dumps(stats, indent=2, ensure_ascii=False)
                
#                 st.download_button(
#                     label="Download Report",
#                     data=stats_json,
#                     file_name=f"analytics_report_{datetime.now().strftime('%Y%m%d')}.json",
#                     mime="application/json",
#                     use_container_width=True
#                 )

def create_search_history_pdf(history):
    """Create PDF for search history"""
    try:
        from fpdf import FPDF
        import tempfile
        
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Search History Report', 0, 1, 'C')
        pdf.ln(5)
        
        # Add date
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1)
        pdf.ln(5)
        
        # Summary
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f'Total Searches: {len(history)}', 0, 1)
        pdf.ln(5)
        
        # Create table
        pdf.set_font('Arial', 'B', 10)
        col_widths = [40, 60, 25, 25]
        headers = ['Timestamp', 'Query', 'Results', 'Time (ms)']
        
        # Header
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, 'C')
        pdf.ln()
        
        # Data
        pdf.set_font('Arial', '', 10)
        for entry in history[-50:]:  # Last 50 entries
            dt = datetime.fromisoformat(entry['timestamp'])
            timestamp = dt.strftime('%d/%m/%Y %H:%M')
            query = entry['query'][:35] + '...' if len(entry['query']) > 35 else entry['query']
            results = str(entry.get('num_results', 0))
            time_ms = f"{entry.get('search_time', 0)*1000:.2f}"
            
            pdf.cell(col_widths[0], 10, timestamp, 1)
            pdf.cell(col_widths[1], 10, query, 1)
            pdf.cell(col_widths[2], 10, results, 1, 0, 'C')
            pdf.cell(col_widths[3], 10, time_ms, 1, 0, 'C')
            pdf.ln()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            return tmp_file.name
        
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        return None

def create_analytics_pdf(stats):
    """Create PDF for analytics report"""
    try:
        from fpdf import FPDF
        import tempfile
        
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Add title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Analytics Report', 0, 1, 'C')
        pdf.ln(5)
        
        # Add date
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1)
        pdf.ln(10)
        
        # Summary stats
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Summary Statistics', 0, 1)
        pdf.ln(5)
        
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 8, f'Total Searches: {stats["total_searches"]}', 0, 1)
        pdf.cell(0, 8, f'Unique Queries: {stats["unique_queries"]}', 0, 1)
        pdf.cell(0, 8, f'Average Results: {stats["avg_results"]:.1f}', 0, 1)
        pdf.cell(0, 8, f'Searches Today: {stats["today_searches"]}', 0, 1)
        pdf.cell(0, 8, f'Average Search Time: {stats["avg_search_time"]*1000:.2f} ms', 0, 1)
        pdf.ln(10)
        
        # Top queries
        if stats['top_queries']:
            pdf.set_font('Arial', 'B', 14)
            pdf.cell(0, 10, 'Top 10 Queries', 0, 1)
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(100, 10, 'Query', 1)
            pdf.cell(40, 10, 'Frequency', 1, 0, 'C')
            pdf.ln()
            
            pdf.set_font('Arial', '', 10)
            for query, count in stats['top_queries'][:10]:
                query_display = query[:40] + '...' if len(query) > 40 else query
                pdf.cell(100, 10, query_display, 1)
                pdf.cell(40, 10, str(count), 1, 0, 'C')
                pdf.ln()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf.output(tmp_file.name)
            return tmp_file.name
        
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        return None


# UPDATE bagian main() untuk export
def main():
    render_analytics_header()
    
    # Load data
    history = load_search_history()
    
    # Main tabs
    tab1, tab2 = st.tabs(["📊 Search Analytics", "📁 System Insights"])
    
    with tab1:
        render_search_stats(history)
        render_favorites_analytics()
    
    with tab2:
        render_index_analytics()
        
        # System information
        st.markdown("---")
        st.markdown("### 🖥️ System Information")
        
        import platform
        import psutil
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Platform:**")
            st.code(f"""
                System: {platform.system()} {platform.release()}
                Python: {platform.python_version()}
                Streamlit: {st.__version__}
                CPU Cores: {psutil.cpu_count()}
                RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB
            """)
        
        with col2:
            st.markdown("**Data Information:**")
            st.code(f"""
                Search History: {len(history)} entries
                Favorites: {len(load_favorites())} items
                Last Update: {get_current_wib_datetime().strftime('%Y-%m-%d %H:%M')}
            """)
        
        # Export data - SINGLE CLICK PDF
        st.markdown("---")
        st.markdown("### 💾 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export Search History (PDF)", use_container_width=True):
                if history:
                    pdf_path = create_search_history_pdf(history)
                    if pdf_path:
                        with open(pdf_path, 'rb') as f:
                            pdf_bytes = f.read()
                        
                        st.download_button(
                            label="📥 Download PDF",
                            data=pdf_bytes,
                            file_name=f"search_history_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.warning("Belum ada data pencarian")
        
        with col2:
            if st.button("📊 Export Analytics Report (PDF)", use_container_width=True):
                if history:
                    stats = get_search_stats(history)
                    pdf_path = create_analytics_pdf(stats)
                    if pdf_path:
                        with open(pdf_path, 'rb') as f:
                            pdf_bytes = f.read()
                        
                        st.download_button(
                            label="📥 Download PDF",
                            data=pdf_bytes,
                            file_name=f"analytics_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.warning("Belum ada data analisis")
    render_reset_menu()

if __name__ == "__main__":
    main()
