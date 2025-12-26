"""
Simple timezone-aware datetime display using JavaScript
This displays timestamps in user's local timezone automatically
"""

import streamlit as st
import streamlit.components.v1 as components


def display_local_datetime(iso_timestamp: str, format_type: str = "full", component_key: str = None):
    """
    Display datetime in user's local timezone using JavaScript
    
    Args:
        iso_timestamp: ISO format timestamp string (can be UTC or any timezone)
        format_type: "full" (DD/MM/YYYY HH:MM:SS), "short" (DD MMM HH:MM), "relative" (2 hours ago)
        component_key: Unique key for the component
    
    Returns:
        HTML component with local datetime
    """
    
    # JavaScript code to convert and display local time
    html_code = f"""
    <div id="datetime-{component_key}" style="display: inline;">
        <span id="display-{component_key}">Loading...</span>
    </div>
    
    <script>
    (function() {{
        const timestamp = "{iso_timestamp}";
        const formatType = "{format_type}";
        const displayEl = document.getElementById("display-{component_key}");
        
        try {{
            // Parse ISO timestamp
            const date = new Date(timestamp);
            
            // Check if valid
            if (isNaN(date.getTime())) {{
                displayEl.textContent = timestamp;
                return;
            }}
            
            // Format based on type
            if (formatType === "full") {{
                // DD/MM/YYYY HH:MM:SS in local timezone
                const day = String(date.getDate()).padStart(2, '0');
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const year = date.getFullYear();
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                const seconds = String(date.getSeconds()).padStart(2, '0');
                
                displayEl.textContent = `${{day}}/${{month}}/${{year}} ${{hours}}:${{minutes}}:${{seconds}}`;
                
            }} else if (formatType === "short") {{
                // DD MMM HH:MM in local timezone
                const day = String(date.getDate()).padStart(2, '0');
                const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                const month = monthNames[date.getMonth()];
                const hours = String(date.getHours()).padStart(2, '0');
                const minutes = String(date.getMinutes()).padStart(2, '0');
                
                displayEl.textContent = `${{day}} ${{month}} ${{hours}}:${{minutes}}`;
                
            }} else if (formatType === "relative") {{
                // Relative time (e.g., "2 hours ago")
                const now = new Date();
                const diffMs = now - date;
                const diffSec = Math.floor(diffMs / 1000);
                const diffMin = Math.floor(diffSec / 60);
                const diffHour = Math.floor(diffMin / 60);
                const diffDay = Math.floor(diffHour / 24);
                
                if (diffDay > 7) {{
                    // More than 7 days ago, show date
                    const day = String(date.getDate()).padStart(2, '0');
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const year = date.getFullYear();
                    displayEl.textContent = `${{day}}/${{month}}/${{year}}`;
                }} else if (diffDay >= 2) {{
                    displayEl.textContent = `${{diffDay}} hari lalu`;
                }} else if (diffDay === 1) {{
                    const hours = String(date.getHours()).padStart(2, '0');
                    const minutes = String(date.getMinutes()).padStart(2, '0');
                    displayEl.textContent = `Kemarin ${{hours}}:${{minutes}}`;
                }} else if (diffHour >= 1) {{
                    displayEl.textContent = `${{diffHour}} jam lalu`;
                }} else if (diffMin >= 1) {{
                    displayEl.textContent = `${{diffMin}} menit lalu`;
                }} else {{
                    displayEl.textContent = `Baru saja`;
                }}
            }}
            
        }} catch (error) {{
            console.error("Error formatting date:", error);
            displayEl.textContent = timestamp;
        }}
    }})();
    </script>
    """
    
    # Return HTML component
    return components.html(html_code, height=25)


def format_datetime_js(iso_timestamp: str, key_suffix: str = "") -> str:
    """
    Return HTML/JS code to display datetime in local timezone
    Use this in markdown with unsafe_allow_html=True
    
    Args:
        iso_timestamp: ISO timestamp string
        key_suffix: Unique suffix for this timestamp
    
    Returns:
        HTML string with embedded JavaScript
    """
    return f"""
    <span id="dt-{key_suffix}">
        <script>
        (function() {{
            const date = new Date("{iso_timestamp}");
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            document.getElementById("dt-{key_suffix}").innerHTML = `${{day}}/${{month}}/${{year}} ${{hours}}:${{minutes}}`;
        }})();
        </script>
    </span>
    """
