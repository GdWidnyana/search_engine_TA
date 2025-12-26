"""
Timezone utilities for handling browser local time
"""
import streamlit as st
import json
from datetime import datetime, timedelta
import time

def inject_timezone_detector():
    """
    Inject JavaScript to detect browser timezone and send to Streamlit
    Returns: JavaScript code as string
    """
    js_code = """
    <script>
    function detectTimezone() {
        try {
            // Get browser timezone info
            const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const offset = new Date().getTimezoneOffset(); // in minutes
            const localTime = new Date().toISOString();
            
            // Create hidden elements to send data to Streamlit
            const timezoneInput = document.createElement('input');
            timezoneInput.type = 'hidden';
            timezoneInput.id = 'browser_timezone';
            timezoneInput.value = timezone;
            document.body.appendChild(timezoneInput);
            
            const offsetInput = document.createElement('input');
            offsetInput.type = 'hidden';
            offsetInput.id = 'browser_offset';
            offsetInput.value = offset.toString();
            document.body.appendChild(offsetInput);
            
            const localTimeInput = document.createElement('input');
            localTimeInput.type = 'hidden';
            localTimeInput.id = 'browser_localtime';
            localTimeInput.value = localTime;
            document.body.appendChild(localTimeInput);
            
            console.log('Timezone detected:', timezone, 'Offset:', offset);
            
            // Trigger Streamlit to read these values
            if (window.parent) {
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    value: {
                        timezone: timezone,
                        offset: offset,
                        localTime: localTime
                    }
                }, '*');
            }
            
            return { timezone: timezone, offset: offset, localTime: localTime };
        } catch (error) {
            console.error('Error detecting timezone:', error);
            return null;
        }
    }
    
    // Run detection when page loads
    window.addEventListener('load', function() {
        setTimeout(detectTimezone, 1000);
    });
    
    // Also run when user interacts (for Streamlit reruns)
    document.addEventListener('click', function() {
        setTimeout(detectTimezone, 500);
    });
    
    // Initial detection
    detectTimezone();
    </script>
    """
    
    # Inject the JavaScript
    st.components.v1.html(js_code, height=0)

def get_browser_time_info():
    """
    Try to get browser time info from session state or return default
    """
    # Initialize in session state if not exists
    if 'browser_time_info' not in st.session_state:
        st.session_state.browser_time_info = {
            'timezone': 'Asia/Jakarta',  # Default fallback
            'offset': -420,  # WIB: UTC+7 = -420 minutes
            'detected': False,
            'detection_time': datetime.now().isoformat()
        }
    
    return st.session_state.browser_time_info

def adjust_datetime_to_local(iso_timestamp: str, offset_minutes: int = None) -> datetime:
    """
    Adjust UTC timestamp to local time using offset
    offset_minutes: Minutes from UTC (negative for east of UTC, positive for west)
    Example: WIB (UTC+7) = -420 minutes
    """
    try:
        # Parse the timestamp
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        
        # If no offset provided, use default WIB
        if offset_minutes is None:
            offset_minutes = -420  # WIB default
        
        # Apply offset
        dt_adjusted = dt - timedelta(minutes=offset_minutes)
        return dt_adjusted
        
    except Exception as e:
        print(f"Error adjusting datetime: {e}")
        # Fallback to server time
        return datetime.now()

def format_datetime_for_display(dt: datetime, format_type: str = 'full') -> str:
    """
    Format datetime for display
    format_type: 'full', 'date', 'time', 'relative'
    """
    if format_type == 'full':
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    elif format_type == 'date':
        return dt.strftime('%d/%m/%Y')
    elif format_type == 'time':
        return dt.strftime('%H:%M:%S')
    elif format_type == 'relative':
        now = datetime.now()
        
        if dt.date() == now.date():
            return f"Hari ini {dt.strftime('%H:%M')}"
        
        yesterday = now.date() - timedelta(days=1)
        if dt.date() == yesterday:
            return f"Kemarin {dt.strftime('%H:%M')}"
        
        if dt.year == now.year:
            return dt.strftime("%d %b %H:%M")
        
        return dt.strftime("%d %b %Y")
    else:
        return dt.strftime('%d/%m/%Y %H:%M')