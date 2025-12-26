# """
# Timezone utilities for Streamlit app
# Handles timezone conversion between server (UTC) and client timezone
# """

# import streamlit as st
# import streamlit.components.v1 as components
# from datetime import datetime, timezone
# import pytz


# def get_client_timezone():
#     """
#     Get client timezone using JavaScript
#     Returns timezone offset in minutes
#     """
#     # JavaScript code to get timezone offset
#     timezone_js = """
#     <script>
#     // Get timezone offset in minutes
#     const offset = new Date().getTimezoneOffset();
#     const timezoneName = Intl.DateTimeFormat().resolvedOptions().timeZone;
    
#     // Send to Streamlit
#     window.parent.postMessage({
#         type: 'streamlit:setComponentValue',
#         data: {
#             offset: offset,
#             timezone: timezoneName
#         }
#     }, '*');
#     </script>
#     """
    
#     # Return component
#     return components.html(timezone_js, height=0)


# def init_timezone():
#     """Initialize timezone in session state"""
#     if 'client_tz_offset' not in st.session_state:
#         # Default to UTC if not set
#         st.session_state.client_tz_offset = 0
#         st.session_state.client_timezone = 'UTC'
    
#     # Try to get timezone from JavaScript (non-blocking)
#     try:
#         tz_info = get_client_timezone()
#         if tz_info:
#             st.session_state.client_tz_offset = tz_info.get('offset', 0)
#             st.session_state.client_timezone = tz_info.get('timezone', 'UTC')
#     except:
#         pass


# def get_user_timezone():
#     """
#     Get user timezone from session state
#     Falls back to UTC if not available
#     """
#     if 'client_timezone' in st.session_state:
#         try:
#             return pytz.timezone(st.session_state.client_timezone)
#         except:
#             pass
    
#     # Fallback to UTC
#     return pytz.UTC


# def convert_utc_to_local(utc_datetime_str: str, tz=None) -> datetime:
#     """
#     Convert UTC datetime string to local timezone
    
#     Args:
#         utc_datetime_str: ISO format datetime string (assumed UTC)
#         tz: Target timezone (default: user timezone from session)
    
#     Returns:
#         datetime object in local timezone
#     """
#     if not utc_datetime_str:
#         return None
    
#     try:
#         # Parse datetime (remove timezone if present)
#         if isinstance(utc_datetime_str, str):
#             dt = datetime.fromisoformat(utc_datetime_str.replace('Z', '+00:00'))
#         else:
#             dt = utc_datetime_str
        
#         # Make timezone aware (UTC)
#         if dt.tzinfo is None:
#             dt = dt.replace(tzinfo=pytz.UTC)
        
#         # Get target timezone
#         if tz is None:
#             tz = get_user_timezone()
        
#         # Convert to local timezone
#         local_dt = dt.astimezone(tz)
        
#         return local_dt
        
#     except Exception as e:
#         print(f"Error converting timezone: {e}")
#         # Return as-is if conversion fails
#         try:
#             return datetime.fromisoformat(utc_datetime_str.replace('Z', ''))
#         except:
#             return datetime.now()


# def format_datetime_local(dt_str: str, format_str: str = "%d/%m/%Y %H:%M:%S") -> str:
#     """
#     Format datetime string in local timezone
    
#     Args:
#         dt_str: ISO datetime string
#         format_str: Output format string
    
#     Returns:
#         Formatted datetime string in local timezone
#     """
#     if not dt_str:
#         return "N/A"
    
#     try:
#         local_dt = convert_utc_to_local(dt_str)
#         return local_dt.strftime(format_str)
#     except Exception as e:
#         print(f"Error formatting datetime: {e}")
#         return dt_str


# def get_local_now() -> datetime:
#     """Get current time in user's local timezone"""
#     utc_now = datetime.now(pytz.UTC)
#     user_tz = get_user_timezone()
#     return utc_now.astimezone(user_tz)


# def save_timestamp_utc() -> str:
#     """
#     Get current timestamp in UTC for saving to database
#     Always save in UTC, convert on display
#     """
#     return datetime.now(pytz.UTC).isoformat()

