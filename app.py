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
    
    # Validate date format if provided
    if from_date:
        try:
            datetime.strptime(from_date, '%Y-%m-%d')
        except ValueError:
            return False, "Invalid date format for From Date (expected YYYY-MM-DD)"
    
    if to_date:
        try:
            datetime.strptime(to_date, '%Y-%m-%d')
        except ValueError:
            return False, "Invalid date format for To Date (expected YYYY-MM-DD)"
    
    # Check date range
    if from_date and to_date:
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            if from_dt > to_dt:
                return False, "From Date must be earlier than To Date"
        except ValueError:
            pass  # Already caught above
    
    return True, None


@app.route('/')
def index():
    """Home page - show search form"""
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    return render_template('search.html', today_date=today)


@app.route('/search', methods=['GET', 'POST'])
def search():
    """Handle search request"""
    try:
        # Get form data (from POST or GET for pagination)
        if request.method == 'POST':
            ship_id = request.form.get('ship_id', '').strip()
            interface_id = request.form.get('interface_id', '').strip() or None
            from_date = request.form.get('from_date', '').strip() or None
            to_date = request.form.get('to_date', '').strip() or None
            page = 1
        else:  # GET request for pagination
            ship_id = request.args.get('ship_id', '').strip()
            interface_id = request.args.get('interface_id', '').strip() or None
            from_date = request.args.get('from_date', '').strip() or None
            to_date = request.args.get('to_date', '').strip() or None
            page = int(request.args.get('page', 1))
        
        # Validate inputs
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        is_valid, error_message = validate_inputs(ship_id, from_date, to_date)
        if not is_valid:
            flash(error_message, 'error')
            return render_template('search.html',
                                 ship_id=ship_id,
                                 interface_id=interface_id or '',
                                 from_date=from_date or today,
                                 to_date=to_date or today,
                                 today_date=today)
        
        # Pagination - based on table rows, not DB records
        rows_per_page = 100
        rows_offset = (page - 1) * rows_per_page
        
        # Execute query to get all records and process into rows
        # We need to process all records to count rows accurately for pagination
        try:
            # Get all records (with reasonable limit for safety)
            all_records = execute_query(
                ship_id=ship_id,
                interface_id=interface_id,
                from_date=from_date,
                to_date=to_date,
                limit=10000,  # Safety limit
                offset=0
            )
            
            # Process all records into table rows
            all_table_rows = []
            for record in all_records:
                ship_id_val = record.get('ship_id')
                interface_id_val = record.get('interface_id') or ''
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
                            'interface_id': interface_id_val,
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
                        'interface_id': interface_id_val,
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
            from datetime import date
            today = date.today().strftime('%Y-%m-%d')
            return render_template('search.html',
                                 ship_id=ship_id,
                                 interface_id=interface_id or '',
                                 from_date=from_date or today,
                                 to_date=to_date or today,
                                 today_date=today)
        
        if not table_rows:
            flash("No data found", 'info')
        
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        return render_template('search.html',
                             ship_id=ship_id,
                             interface_id=interface_id or '',
                             from_date=from_date or today,
                             to_date=to_date or today,
                             table_rows=table_rows,
                             today_date=today,
                             page=page,
                             total_pages=total_pages,
                             total_count=total_count,
                             records_per_page=rows_per_page)
    
    except Exception as e:
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        app.logger.error(f"Error in search: {traceback.format_exc()}")
        flash(f"An error occurred: {str(e)}", 'error')
        return render_template('search.html', today_date=today)


@app.route('/api/realtime', methods=['GET'])
def realtime_api():
    """RealTime API endpoint - returns new records since last_timestamp"""
    try:
        # Get parameters
        ship_id = request.args.get('ship_id', '').strip()
        interface_id = request.args.get('interface_id', '').strip() or None
        last_timestamp_str = request.args.get('last_timestamp', '').strip()
        
        # Validation
        if not ship_id:
            return jsonify({
                'success': False,
                'error': 'ship_id is required'
            }), 400
        
        # Parse last_timestamp or use default (1 minute ago)
        if last_timestamp_str:
            try:
                # Try ISO format first
                last_timestamp = datetime.fromisoformat(last_timestamp_str.replace('Z', '+00:00').replace(' ', 'T'))
            except (ValueError, AttributeError):
                # Try alternative format: 'YYYY-MM-DD HH:MM:SS'
                try:
                    last_timestamp = datetime.strptime(last_timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Default to 1 minute ago
                    last_timestamp = datetime.now() - timedelta(minutes=1)
        else:
            # First request: get data from last 1 minute
            last_timestamp = datetime.now() - timedelta(minutes=1)
        
        # Query for new records
        try:
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
                    AND created_time > %s
            """
            
            params = [ship_id, last_timestamp]
            
            if interface_id:
                query += " AND interface_id LIKE %s"
                params.append(f'%{interface_id}%')
            
            query += " ORDER BY created_time DESC LIMIT 100"
            
            from utils.db import get_db_connection
            from psycopg2.extras import RealDictCursor
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    records = [dict(row) for row in results]
            
        except Exception as e:
            app.logger.error(f"Database error in realtime_api: {e}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500
        
        # Process records into table rows
        new_rows = []
        latest_timestamp = last_timestamp
        
        for record in records:
            ship_id_val = record.get('ship_id')
            interface_id_val = record.get('interface_id') or ''
            created_time_val = record.get('created_time')
            
            # Update latest timestamp
            if created_time_val:
                if isinstance(created_time_val, datetime):
                    if created_time_val > latest_timestamp:
                        latest_timestamp = created_time_val
                elif isinstance(created_time_val, str):
                    try:
                        dt = datetime.fromisoformat(created_time_val.replace('Z', '+00:00'))
                        if dt > latest_timestamp:
                            latest_timestamp = dt
                    except:
                        pass
            
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
                        'interface_id': interface_id_val,
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
                    'interface_id': interface_id_val,
                    'tag_name': '',
                    'value': '',
                    'description': '',
                    'unit': '',
                    'posix_micros': posix_micros_value,
                    'created_time': str(created_time_val) if created_time_val else '',
                    'value_type': 'str'
                })
        
        # Format latest timestamp for response
        last_timestamp_str = latest_timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(latest_timestamp, datetime) else str(latest_timestamp)
        
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
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    return render_template('search.html', error="Page not found", today_date=today), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
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

