"""
Database utility module
Handles database connections and queries
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from psycopg2 import OperationalError, InterfaceError
from contextlib import contextmanager
import time
from config import Config

config = Config()

# Connection pool
connection_pool = None
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def init_db_pool():
    """Initialize database connection pool"""
    global connection_pool
    try:
        # Close existing pool if it exists
        if connection_pool:
            try:
                connection_pool.closeall()
            except:
                pass
        
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # min connections
            10,  # max connections
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        if connection_pool:
            print("Database connection pool created successfully")
    except (Exception, psycopg2.Error) as error:
        print(f"Error while creating database connection pool: {error}")
        connection_pool = None
        raise


def is_connection_valid(conn):
    """Check if a database connection is still valid"""
    try:
        # Try to execute a simple query
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except (OperationalError, InterfaceError, psycopg2.InterfaceError):
        return False
    except Exception:
        return False


def recreate_pool():
    """Recreate the connection pool"""
    global connection_pool
    print("Recreating database connection pool...")
    connection_pool = None
    init_db_pool()


@contextmanager
def get_db_connection():
    """Get a database connection from the pool with automatic reconnection"""
    global connection_pool
    
    # Initialize pool if needed
    if connection_pool is None:
        init_db_pool()
    
    connection = None
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            # Try to get connection from pool
            if connection_pool is None:
                init_db_pool()
            
            try:
                connection = connection_pool.getconn()
            except (psycopg2.pool.PoolError, AttributeError):
                # Pool might be closed or invalid, recreate it
                recreate_pool()
                connection = connection_pool.getconn()
            
            # Check if connection is valid
            if not is_connection_valid(connection):
                # Connection is invalid, close it
                try:
                    connection.close()
                except:
                    pass
                connection = None
                
                # Recreate pool if needed
                if retries >= 1:
                    recreate_pool()
                    try:
                        connection = connection_pool.getconn()
                    except (psycopg2.pool.PoolError, AttributeError):
                        recreate_pool()
                        connection = connection_pool.getconn()
                else:
                    retries += 1
                    if retries < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                        recreate_pool()
                    continue
                
                # Validate new connection
                if not is_connection_valid(connection):
                    try:
                        connection.close()
                    except:
                        pass
                    connection = None
                    retries += 1
                    if retries < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)
                        recreate_pool()
                    continue
            
            # Connection is valid, use it
            try:
                yield connection
                # Successfully used connection, return it to pool
                try:
                    connection_pool.putconn(connection)
                except:
                    # If putting back fails, connection might be invalid
                    try:
                        connection.close()
                    except:
                        pass
                return
            except (OperationalError, InterfaceError, psycopg2.InterfaceError) as e:
                # Connection error during use, try to reconnect
                print(f"Connection error during query: {e}")
                try:
                    connection.close()
                except:
                    pass
                connection = None
                retries += 1
                if retries < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    recreate_pool()
                else:
                    raise Exception(f"Database connection lost during query after {MAX_RETRIES} retries: {e}")
            except Exception as e:
                # Other errors during query execution, return connection and re-raise
                try:
                    if is_connection_valid(connection):
                        connection_pool.putconn(connection)
                    else:
                        connection.close()
                except:
                    pass
                raise
                
        except (OperationalError, InterfaceError, psycopg2.InterfaceError, psycopg2.pool.PoolError) as e:
            # Pool error or connection error
            print(f"Database connection error (attempt {retries + 1}/{MAX_RETRIES}): {e}")
            if connection:
                try:
                    connection.close()
                except:
                    pass
            connection = None
            retries += 1
            
            if retries < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                recreate_pool()
            else:
                raise Exception(f"Failed to get database connection after {MAX_RETRIES} attempts: {e}")
    
    # If we get here, all retries failed
    raise Exception(f"Failed to get database connection after {MAX_RETRIES} attempts")


def execute_query(ship_id, interface_id=None, from_date=None, to_date=None, limit=100, offset=0):
    """
    Execute search query with given parameters
    
    Args:
        ship_id: Required ship ID
        interface_id: Optional interface ID (LIKE search)
        from_date: Optional start date
        to_date: Optional end date
        limit: Number of records to return (default: 100)
        offset: Number of records to skip (default: 0)
    
    Returns:
        List of records (dictionaries)
    """
    query = f"""
        SELECT 
            id,
            ship_id,
            interface_id,
            json_data,
            created_time,
            server_created_time
        FROM {config.DB_SCHEMA}.{config.DB_TABLE}
        WHERE ship_id = %s
    """
    
    params = [ship_id]
    
    # Add optional conditions
    if interface_id:
        query += " AND interface_id LIKE %s"
        params.append(f'%{interface_id}%')
    
    if from_date:
        query += " AND created_time >= %s"
        params.append(from_date)
    
    if to_date:
        query += " AND created_time <= %s::date + INTERVAL '1 day' - INTERVAL '1 second'"
        params.append(to_date)
    
    query += " ORDER BY created_time DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
    except (Exception, psycopg2.Error) as error:
        print(f"Error executing query: {error}")
        raise


def count_query(ship_id, interface_id=None, from_date=None, to_date=None):
    """
    Count total records matching the query
    
    Args:
        ship_id: Required ship ID
        interface_id: Optional interface ID (LIKE search)
        from_date: Optional start date
        to_date: Optional end date
    
    Returns:
        Total count of matching records
    """
    query = f"""
        SELECT COUNT(*) as total
        FROM {config.DB_SCHEMA}.{config.DB_TABLE}
        WHERE ship_id = %s
    """
    
    params = [ship_id]
    
    # Add optional conditions
    if interface_id:
        query += " AND interface_id LIKE %s"
        params.append(f'%{interface_id}%')
    
    if from_date:
        query += " AND created_time >= %s"
        params.append(from_date)
    
    if to_date:
        query += " AND created_time <= %s::date + INTERVAL '1 day' - INTERVAL '1 second'"
        params.append(to_date)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result['total'] if result else 0
    except (Exception, psycopg2.Error) as error:
        print(f"Error counting records: {error}")
        raise


def test_connection():
    """Test database connection"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False

