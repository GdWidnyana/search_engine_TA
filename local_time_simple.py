# """
# Simple Local Time Handler
# Saves and displays timestamps in user's local timezone
# NO CONVERSION NEEDED - Direct local time handling
# """

# import streamlit as st
# import streamlit.components.v1 as components
# from datetime import datetime


# def get_local_timestamp_js():
#     """
#     Get current timestamp in user's local timezone using JavaScript
#     Returns JavaScript code that can be executed to get local time
#     """
#     js_code = """
#     <script>
#     // Get current local time
#     const now = new Date();
    
#     // Format as ISO string but in LOCAL timezone (not UTC)
#     const year = now.getFullYear();
#     const month = String(now.getMonth() + 1).padStart(2, '0');
#     const day = String(now.getDate()).padStart(2, '0');
#     const hours = String(now.getHours()).padStart(2, '0');
#     const minutes = String(now.getMinutes()).padStart(2, '0');
#     const seconds = String(now.getSeconds()).padStart(2, '0');
    
#     const localTimestamp = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
    
#     // Send to parent
#     window.parent.postMessage({
#         type: 'streamlit:setComponentValue',
#         value: localTimestamp
#     }, '*');
#     </script>
#     """
    
#     return components.html(js_code, height=0)


# def display_timestamp_simple(timestamp_str: str, format_type: str = "full"):
#     """
#     Display timestamp AS-IS (no conversion)
#     Assumes timestamp is already in local timezone
    
#     Args:
#         timestamp_str: Timestamp string (e.g., "2025-12-27T01:21:00")
#         format_type: "full", "short", or "relative"
    
#     Returns:
#         Formatted string
#     """
#     try:
#         # Parse timestamp (assume local timezone)
#         if 'T' in timestamp_str:
#             dt = datetime.fromisoformat(timestamp_str.split('.')[0])  # Remove microseconds
#         else:
#             dt = datetime.fromisoformat(timestamp_str)
        
#         if format_type == "full":
#             # DD/MM/YYYY HH:MM:SS
#             return dt.strftime("%d/%m/%Y %H:%M:%S")
        
#         elif format_type == "short":
#             # DD/MM/YYYY HH:MM
#             return dt.strftime("%d/%m/%Y %H:%M")
        
#         elif format_type == "datetime_only":
#             # DD MMM HH:MM
#             return dt.strftime("%d %b %H:%M")
        
#         elif format_type == "relative":
#             # Relative time
#             now = datetime.now()
#             diff = now - dt
            
#             days = diff.days
#             seconds = diff.seconds
#             hours = seconds // 3600
#             minutes = (seconds % 3600) // 60
            
#             if days > 7:
#                 return dt.strftime("%d/%m/%Y")
#             elif days >= 2:
#                 return f"{days} hari lalu"
#             elif days == 1:
#                 return f"Kemarin {dt.strftime('%H:%M')}"
#             elif hours >= 1:
#                 return f"{hours} jam lalu"
#             elif minutes >= 1:
#                 return f"{minutes} menit lalu"
#             else:
#                 return "Baru saja"
        
#         return timestamp_str
        
#     except Exception as e:
#         print(f"Error formatting timestamp: {e}")
#         return timestamp_str


# def get_current_local_time() -> str:
#     """
#     Get current time in ISO format (local timezone)
#     This should be used when saving timestamps
    
#     Returns:
#         ISO format string (e.g., "2025-12-27T01:21:00")
#     """
#     return datetime.now().isoformat()


# def format_for_display(timestamp_str: str) -> str:
#     """
#     Format timestamp for display (DD/MM/YYYY HH:MM)
#     No timezone conversion - direct format
    
#     Args:
#         timestamp_str: ISO timestamp string
    
#     Returns:
#         Formatted string
#     """
#     return display_timestamp_simple(timestamp_str, format_type="short")


# def format_for_analytics(timestamp_str: str) -> str:
#     """
#     Format timestamp for analytics table (DD/MM/YYYY HH:MM:SS)
    
#     Args:
#         timestamp_str: ISO timestamp string
    
#     Returns:
#         Formatted string
#     """
#     return display_timestamp_simple(timestamp_str, format_type="full")
