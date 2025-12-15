"""
AMS Bypass Web Query Application
Main Flask application
"""
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from datetime import datetime, timedelta
import traceback
from config import Config
from utils.db import init_db_pool, execute_query, count_query, test_connection
from utils.parser import parse_json_data

app = Flask(__name__)
app.config.from_object(Config)


def validate_inputs(ship_id, from_date, to_date):
    """
    Validate user inputs
    
    Returns:
        (is_valid, error_message)
    """
    # Check required field
    if not ship_id or not ship_id.strip():
        return False, "Ship ID is required"
    
    # Validate datetime format if provided
    if from_date:
        try:
            # Try datetime-local format: YYYY-MM-DDTHH:MM
            datetime.strptime(from_date, '%Y-%m-%dT%H:%M')
        except ValueError:
            try:
                # Try date format: YYYY-MM-DD (for backward compatibility)
                datetime.strptime(from_date, '%Y-%m-%d')
            except ValueError:
                return False, "Invalid date format for From Date (expected YYYY-MM-DDTHH:MM or YYYY-MM-DD)"
    
    if to_date:
        try:
            # Try datetime-local format: YYYY-MM-DDTHH:MM
            datetime.strptime(to_date, '%Y-%m-%dT%H:%M')
        except ValueError:
            try:
                # Try date format: YYYY-MM-DD (for backward compatibility)
                datetime.strptime(to_date, '%Y-%m-%d')
            except ValueError:
                return False, "Invalid date format for To Date (expected YYYY-MM-DDTHH:MM or YYYY-MM-DD)"
    
    # Check date range
    if from_date and to_date:
        try:
            # Try to parse as datetime-local first
            try:
                from_dt = datetime.strptime(from_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            
            try:
                to_dt = datetime.strptime(to_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            
            if from_dt > to_dt:
                return False, "From Date must be earlier than To Date"
        except ValueError:
            pass  # Already caught above
    
    return True, None


@app.route('/')
def index():
    """Home page - show search form"""
    # today_date will be set by JavaScript in local time
    return render_template('search.html', today_date='')


@app.route('/search', methods=['GET', 'POST'])
def search():
    """Handle search request"""
    try:
        # Get form data (from POST or GET for pagination)
        from datetime import datetime
        # Default to local time now
        today = datetime.now().strftime('%Y-%m-%dT%H:%M')
        
        if request.method == 'POST':
            ship_id = request.form.get('ship_id', '').strip()
            from_date = request.form.get('from_date', '').strip() or today
            to_date = request.form.get('to_date', '').strip() or today
            refresh_interval = request.form.get('refresh_interval', '5').strip() or '5'
            page = 1
        else:  # GET request for pagination
            ship_id = request.args.get('ship_id', '').strip()
            from_date = request.args.get('from_date', '').strip() or today
            to_date = request.args.get('to_date', '').strip() or today
            refresh_interval = request.args.get('refresh_interval', '5').strip() or '5'
            page = int(request.args.get('page', 1))
        
        # Note: from_date and to_date are in local time (datetime-local format)
        # But DB's created_time is in UTC, so we need to convert local time to UTC for query
        
        # Convert local time to UTC for database query
        from datetime import timezone
        from_date_utc = from_date
        to_date_utc = to_date
        
        if from_date and 'T' in from_date:
            try:
                # Parse as local time
                local_dt = datetime.strptime(from_date, '%Y-%m-%dT%H:%M')
                # Convert to UTC (assume local timezone, server's timezone)
                # Get timezone offset
                local_tz = datetime.now().astimezone().tzinfo
                local_dt = local_dt.replace(tzinfo=local_tz)
                utc_dt = local_dt.astimezone(timezone.utc)
                from_date_utc = utc_dt.strftime('%Y-%m-%dT%H:%M')
            except Exception as e:
                app.logger.warning(f"Error converting from_date to UTC: {e}")
                from_date_utc = from_date
        
        if to_date and 'T' in to_date:
            try:
                # Parse as local time
                local_dt = datetime.strptime(to_date, '%Y-%m-%dT%H:%M')
                # Convert to UTC
                local_tz = datetime.now().astimezone().tzinfo
                local_dt = local_dt.replace(tzinfo=local_tz)
                utc_dt = local_dt.astimezone(timezone.utc)
                to_date_utc = utc_dt.strftime('%Y-%m-%dT%H:%M')
            except Exception as e:
                app.logger.warning(f"Error converting to_date to UTC: {e}")
                to_date_utc = to_date
        
        # Validate inputs (use original local time for validation)
        is_valid, error_message = validate_inputs(ship_id, from_date, to_date)
        if not is_valid:
            flash(error_message, 'error')
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%dT%H:%M')
            return render_template('search.html',
                                 ship_id=ship_id,
                                 from_date=from_date or today,
                                 to_date=to_date or today,
                                 refresh_interval=refresh_interval,
                                 today_date='')
        
        # Pagination - based on table rows, not DB records
        rows_per_page = 100
        rows_offset = (page - 1) * rows_per_page
        
        # Execute query to get all records and process into rows
        # We need to process all records to count rows accurately for pagination
        try:
            # Get all records (with reasonable limit for safety)
            # Use UTC times for query
            app.logger.info(f"Executing query: ship_id={ship_id}, from_date={from_date} (local) -> {from_date_utc} (UTC), to_date={to_date} (local) -> {to_date_utc} (UTC)")
            all_records = execute_query(
                ship_id=ship_id,
                interface_id=None,  # Interface ID removed
                from_date=from_date_utc,
                to_date=to_date_utc,
                limit=10000,  # Safety limit
                offset=0
            )
            app.logger.info(f"Query returned {len(all_records)} records")
            
            # Process all records into table rows
            all_table_rows = []
            for record in all_records:
                ship_id_val = record.get('ship_id')
                created_time_val = record.get('created_time')
                
                # Parse JSON data
                parsed_json = parse_json_data(record.get('json_data', ''))
                
                # Extract $ship_posixmicros value for this record
                posix_micros_value = ''
                for json_row in parsed_json:
                    if json_row.get('key') == '$ship_posixmicros':
                        posix_micros_value = json_row.get('value', '')
                        break
                
                if parsed_json:
                    # Create a row for each JSON key
                    for json_row in parsed_json:
                        tag_name = json_row.get('key')
                        
                        # Skip $ship_posixmicros as a separate row, it's shown in its own column
                        if tag_name == '$ship_posixmicros':
                            continue
                        
                        all_table_rows.append({
                            'ship_id': ship_id_val,
                            'tag_name': tag_name,
                            'value': json_row.get('value'),
                            'description': json_row.get('description'),
                            'unit': json_row.get('unit'),
                            'posix_micros': posix_micros_value,
                            'created_time': created_time_val,
                            'value_type': json_row.get('value_type', 'str')
                        })
                
                # If no JSON data or only $ship_posixmicros, create at least one row
                if not parsed_json or (len(parsed_json) == 1 and parsed_json[0].get('key') == '$ship_posixmicros'):
                    all_table_rows.append({
                        'ship_id': ship_id_val,
                        'tag_name': '',
                        'value': '',
                        'description': '',
                        'unit': '',
                        'posix_micros': posix_micros_value,
                        'created_time': created_time_val,
                        'value_type': 'str'
                    })
            
            # Get total count of rows
            total_count = len(all_table_rows)
            
            # Get paginated rows for current page
            table_rows = all_table_rows[rows_offset:rows_offset + rows_per_page]
            
            # Calculate pagination info
            total_pages = (total_count + rows_per_page - 1) // rows_per_page if total_count > 0 else 1
        except Exception as e:
            flash(f"Database error: {str(e)}", 'error')
            app.logger.error(f"Database error in search: {traceback.format_exc()}")
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%dT%H:%M')
            return render_template('search.html',
                                 ship_id=ship_id,
                                 from_date=from_date or today,
                                 to_date=to_date or today,
                                 refresh_interval=refresh_interval,
                                 today_date='')
        
        if not table_rows:
            flash("No data found", 'info')
        
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%dT%H:%M')
        return render_template('search.html',
                             ship_id=ship_id,
                             from_date=from_date or today,
                             to_date=to_date or today,
                             refresh_interval=refresh_interval,
                             table_rows=table_rows,
                             today_date='',
                             page=page,
                             total_pages=total_pages,
                             total_count=total_count,
                             records_per_page=rows_per_page)
    
    except Exception as e:
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%dT%H:%M')
        app.logger.error(f"Error in search: {traceback.format_exc()}")
        flash(f"An error occurred: {str(e)}", 'error')
        return render_template('search.html', today_date=today)


@app.route('/api/realtime', methods=['GET'])
def realtime_api():
    """RealTime API endpoint - returns new records since last_timestamp"""
    try:
        # Get parameters
        ship_id = request.args.get('ship_id', '').strip()
        last_timestamp_str = request.args.get('last_timestamp', '').strip()
        
        # Validation
        if not ship_id:
            return jsonify({
                'success': False,
                'error': 'ship_id is required'
            }), 400
        
        # Parse last_timestamp or use default (1 minute ago)
        # last_timestamp_str is in local time, but DB's created_time is in UTC
        from datetime import timezone
        if last_timestamp_str:
            try:
                # Try format: 'YYYY-MM-DD HH:MM:SS' (local time)
                try:
                    local_timestamp = datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S')
                    # Convert local time to UTC
                    local_tz = datetime.now().astimezone().tzinfo
                    local_timestamp = local_timestamp.replace(tzinfo=local_tz)
                    last_timestamp = local_timestamp.astimezone(timezone.utc)
                    app.logger.info(f"Parsed last_timestamp: local={last_timestamp_str} -> UTC={last_timestamp}")
                except ValueError:
                    # Try ISO format
                    try:
                        last_timestamp = datetime.fromisoformat(last_timestamp_str.replace('Z', '+00:00').replace(' ', 'T'))
                        if last_timestamp.tzinfo is None:
                            # Assume UTC if no timezone info
                            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
                        app.logger.info(f"Parsed last_timestamp (ISO): {last_timestamp}")
                    except (ValueError, AttributeError) as e:
                        app.logger.warning(f"Error parsing last_timestamp (ISO): {e}")
                        # Default to 1 minute ago in UTC
                        last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=1)
            except Exception as e:
                app.logger.warning(f"Error parsing last_timestamp: {e}")
                # Default to 1 minute ago in UTC
                last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=1)
        else:
            # First request: get data from last 1 minute (UTC)
            last_timestamp = datetime.now(timezone.utc) - timedelta(minutes=1)
            app.logger.info(f"No last_timestamp provided, using: {last_timestamp}")
        
        # Query for new records
        # last_timestamp is already in UTC (datetime object with timezone)
        try:
            # Format last_timestamp for PostgreSQL (UTC timestamp)
            if isinstance(last_timestamp, datetime):
                # Convert to string format for PostgreSQL
                last_timestamp_str = last_timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_timestamp_str = str(last_timestamp)
            
            query = f"""
                SELECT 
                    id,
                    ship_id,
                    interface_id,
                    json_data,
                    created_time,
                    server_created_time
                FROM {Config().DB_SCHEMA}.{Config().DB_TABLE}
                WHERE ship_id = %s
                    AND created_time > %s::timestamp
            """
            
            params = [ship_id, last_timestamp_str]
            
            query += " ORDER BY created_time DESC LIMIT 100"
            
            app.logger.info(f"Realtime query: ship_id={ship_id}, last_timestamp (UTC)={last_timestamp_str}")
            
            from utils.db import get_db_connection
            from psycopg2.extras import RealDictCursor
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    records = [dict(row) for row in results]
                    app.logger.info(f"Realtime query returned {len(records)} records")
            
        except Exception as e:
            app.logger.error(f"Database error in realtime_api: {e}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
        
        # Process records into table rows
        new_rows = []
        # Initialize latest_timestamp to last_timestamp, but will update if we find newer records
        latest_timestamp = last_timestamp
        found_newer_records = False
        
        for record in records:
            ship_id_val = record.get('ship_id')
            created_time_val = record.get('created_time')
            
            # Update latest timestamp
            if created_time_val:
                from datetime import timezone
                record_timestamp = None
                
                if isinstance(created_time_val, datetime):
                    # Ensure it's timezone-aware
                    if created_time_val.tzinfo is None:
                        # Assume UTC if no timezone info
                        record_timestamp = created_time_val.replace(tzinfo=timezone.utc)
                    elif created_time_val.tzinfo != timezone.utc:
                        record_timestamp = created_time_val.astimezone(timezone.utc)
                    else:
                        record_timestamp = created_time_val
                elif isinstance(created_time_val, str):
                    try:
                        # Try to parse as UTC
                        dt = datetime.fromisoformat(created_time_val.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            record_timestamp = dt.replace(tzinfo=timezone.utc)
                        elif dt.tzinfo != timezone.utc:
                            record_timestamp = dt.astimezone(timezone.utc)
                        else:
                            record_timestamp = dt
                    except Exception as e:
                        app.logger.warning(f"Error parsing created_time: {e}")
                        record_timestamp = None
                
                # Update latest_timestamp if this record is newer
                if record_timestamp and record_timestamp > latest_timestamp:
                    latest_timestamp = record_timestamp
                    found_newer_records = True
            
            # Parse JSON data
            parsed_json = parse_json_data(record.get('json_data', ''))
            
            # Extract $ship_posixmicros value for this record
            posix_micros_value = ''
            for json_row in parsed_json:
                if json_row.get('key') == '$ship_posixmicros':
                    posix_micros_value = json_row.get('value', '')
                    break
            
            if parsed_json:
                # Create a row for each JSON key
                for json_row in parsed_json:
                    tag_name = json_row.get('key')
                    
                    # Skip $ship_posixmicros as a separate row
                    if tag_name == '$ship_posixmicros':
                        continue
                    
                    new_rows.append({
                        'ship_id': ship_id_val,
                        'tag_name': tag_name,
                        'value': json_row.get('value'),
                        'description': json_row.get('description'),
                        'unit': json_row.get('unit'),
                        'posix_micros': posix_micros_value,
                        'created_time': str(created_time_val) if created_time_val else '',
                        'value_type': json_row.get('value_type', 'str')
                    })
            
            # If no JSON data or only $ship_posixmicros, create at least one row
            if not parsed_json or (len(parsed_json) == 1 and parsed_json[0].get('key') == '$ship_posixmicros'):
                new_rows.append({
                    'ship_id': ship_id_val,
                    'tag_name': '',
                    'value': '',
                    'description': '',
                    'unit': '',
                    'posix_micros': posix_micros_value,
                    'created_time': str(created_time_val) if created_time_val else '',
                    'value_type': 'str'
                })
        
        # Format latest timestamp for response (in UTC)
        # If no newer records found, use current UTC time minus 1 second to avoid missing data
        from datetime import timezone
        if not found_newer_records and len(records) == 0:
            # No records found, advance timestamp slightly to avoid infinite loop
            latest_timestamp = datetime.now(timezone.utc) - timedelta(seconds=1)
            app.logger.info(f"No new records found, advancing timestamp to: {latest_timestamp}")
        
        # Convert to UTC string if it's a datetime object
        if isinstance(latest_timestamp, datetime):
            # Ensure it's in UTC
            if latest_timestamp.tzinfo is None:
                # Assume UTC
                latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
            elif latest_timestamp.tzinfo != timezone.utc:
                latest_timestamp = latest_timestamp.astimezone(timezone.utc)
            last_timestamp_str = latest_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_timestamp_str = str(latest_timestamp)
        
        app.logger.info(f"Realtime API: found {len(new_rows)} new rows from {len(records)} records, last_timestamp={last_timestamp_str}")
        
        return jsonify({
            'success': True,
            'new_rows': new_rows,
            'count': len(new_rows),
            'last_timestamp': last_timestamp_str
        })
    
    except Exception as e:
        app.logger.error(f"Error in realtime_api: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }), 500


@app.route('/reset', methods=['POST'])
def reset():
    """Reset form"""
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%dT%H:%M')
    return render_template('search.html', error="Page not found", today_date=today), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%dT%H:%M')
    app.logger.error(f"Internal error: {traceback.format_exc()}")
    flash("An internal error occurred. Please try again.", 'error')
    return render_template('search.html', today_date=today), 500


@app.before_request
def initialize():
    """Initialize database connection pool (called before each request)"""
    global _db_initialized
    if '_db_initialized' not in globals():
        init_db_pool()
        # Test connection
        if test_connection():
            app.logger.info("Database connection successful")
        else:
            app.logger.error("Database connection failed")
        globals()['_db_initialized'] = True


if __name__ == '__main__':
    # Initialize database pool
    init_db_pool()
    app.run(debug=True, host='0.0.0.0', port=8765)

