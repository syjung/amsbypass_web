"""
JSON parser utility module
Handles JSON data parsing and timestamp conversion
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional


def parse_json_data(json_data_text: str) -> List[Dict[str, Any]]:
    """
    Parse JSON text data into table rows
    
    Args:
        json_data_text: JSON string from database
    
    Returns:
        List of dictionaries containing table row data
    """
    if not json_data_text:
        return []
    
    try:
        json_obj = json.loads(json_data_text)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []
    
    rows = []
    
    # Iterate through key-value pairs
    for key, value in json_obj.items():
        # Skip $ship_sensornodeid
        if key == '$ship_sensornodeid':
            continue
        
        # Handle $ship_posixmicros
        if key == '$ship_posixmicros':
            formatted_time = convert_timestamp(value)
            rows.append({
                'key': key,
                'description': '-',
                'unit': '-',
                'value': formatted_time,
                'value_type': 'str'
            })
            continue
        
        # Handle object values (with desc, unit, value)
        if isinstance(value, dict):
            desc = value.get('desc', '-')
            unit = value.get('unit', '-')
            val = value.get('value', '-')
            
            rows.append({
                'key': key,
                'description': desc,
                'unit': unit,
                'value': val,
                'value_type': type(val).__name__
            })
        else:
            # Handle primitive values
            rows.append({
                'key': key,
                'description': '-',
                'unit': '-',
                'value': value,
                'value_type': type(value).__name__
            })
    
    # Sort rows: put $ship_posixmicros at the end if exists
    rows.sort(key=lambda x: (x['key'].startswith('$'), x['key']))
    
    return rows


def convert_timestamp(posix_micros: int) -> str:
    """
    Convert POSIX microseconds to readable datetime string in UTC
    
    Args:
        posix_micros: Unix timestamp in microseconds
    
    Returns:
        Formatted datetime string in UTC
    """
    try:
        # Convert microseconds to seconds
        timestamp_seconds = posix_micros / 1_000_000
        
        # Create datetime object in UTC
        from datetime import timezone
        dt = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        
        # Format as string (UTC)
        formatted = dt.strftime('%Y-%m-%d %H:%M:%S.%f UTC')
        
        return formatted
    except (ValueError, TypeError, OSError) as e:
        print(f"Error converting timestamp: {e}")
        return str(posix_micros)

