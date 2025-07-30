import datetime
import decimal
import json
import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor

from flask import g
from . import sqlhelper

PGA_QUERIES={}
PGA_TABLES=[]

def dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], dict)):  #noqa
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]

def connectdb(db_config):
    """
    Establishes a connection to a PostgreSQL database using psycopg2.
    
    :param db_config: Dictionary containing database connection details.
    :return: Connection object or None in case of failure, along with a status message.
    """    
    try:
        con = psycopg2.connect(database=db_config["db_name"],
                            host=db_config["db_host"],
                            user=db_config["db_user"],
                            password=db_config["db_password"],
                            port=db_config["db_port"],
                            connect_timeout=5,
                            application_name="pgAssistant")
    
        con.autocommit = True
    except psycopg2.Error as err:
        return None, format(err).rstrip()
    return con, "OK"

def db_exec(conn, sql):
    """
    Executes a SQL statement that does not return a result (e.g., INSERT, UPDATE).
    
    :param conn: The active database connection.
    :param sql: The SQL statement to execute.
    """    
    sql = '/* launched by pgAssistant */ ' + sql
    conn.set_session(autocommit=True)
    cursor = conn.cursor()
    cursor.execute(sql)

def db_exec_recommandation(conn, sql):
    """
    Execute a non-SELECT SQL clause on the given PostgreSQL connection.
    
    :param conn: The active psycopg2 connection object.
    :param sql: The SQL clause to execute.
    :return: A success message or error message.
    """
    sql = '/* launched by pgAssistant */ ' + sql
    try:
        conn.set_session(autocommit=True)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()  
        return {"success": True, "message": f"SQL executed successfully: {sql}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()

def get_json_cursor(conn):
    """
    Returns a database cursor that fetches results as a dictionary (JSON-like).
    """    
    return conn.cursor(cursor_factory=RealDictCursor)

def execute_and_fetch(cursor, query):
    """
    Executes a SQL query and fetches all results.
    
    :param cursor: The active database cursor.
    :param query: The SQL query to execute.
    :return: Fetched query results.
    """    
    query = '/* launched by pgAssistant */ ' + query
    cursor.execute(query)
    res = cursor.fetchall()
    cursor.close()
    return res

def get_json_response(conn, query):
    """
    Executes a SQL query and returns the result as a JSON string.
    
    :param conn: The active database connection.
    :param query: The SQL query to execute.
    :return: JSON string of the query results.
    """    
    cursor = get_json_cursor(conn)
    response = execute_and_fetch(cursor, query)
    return json.dumps(response)

def defaultconverter(o):
    """
    Converts datetime and decimal objects to strings for JSON serialization.
    """    
    if isinstance(o, datetime.datetime):
        return o.__str__()
    elif isinstance(o, decimal.Decimal):
        return str(o)
    
def db_fetch_json(conn,sql):
    """
    Executes a SQL query and returns results as a JSON string with type conversion.
    
    :param conn: The active database connection.
    :param sql: The SQL query to execute.
    :return: JSON string containing the query results.
    """
    cursor = get_json_cursor(conn)
    response = execute_and_fetch(cursor, sql)
    return json.dumps(response, default = defaultconverter)

def get_top_queries(db_config):
    """
    Retrieves the top queries executed in the database.
    """    
    rows = []
    con, message = connectdb(db_config)
    if con:
       try:
           rows,description=db_query(con,'top_queries')
       except:
           rows=[] 
       con.close()  
    return rows

def get_rank_queries(db_config):
    """
    Retrieves ranked database queries.
    """    
    rows = [] 
    con, message = connectdb(db_config)
    if con:
       try:
           rows,description=db_query(con,'rank_queries')
       except:
           rows=[] 
       con.close()
    return rows

def exec_cmd(db_config,query_id):
    """
    Executes a predefined query by its ID.
    """    
    con, message = connectdb(db_config)
    if con:
       db_query(con,query_id)
       con.close()

def generic_select(db_config,query_id):
    rows = []
    con, message = connectdb(db_config)
    if con:
       rows,description=db_query(con,query_id)
       con.close()
       return rows, description

def generic_select_with_sql(db_config,sql):
    rows = []
    con, message = connectdb(db_config)
    if con:
       rows=json.loads(db_fetch_json(con,sql))
       con.close()
    return rows

def get_db_info(db_config,con=None):
    info = {}

    if not con:
        con, message = connectdb(db_config)

    if con:
        if db_config:
            # Enable pg_stat_statements_enable if it is not enabled (it is not enable by default)
            try:
                cursor = con.cursor()
                cursor.execute('/* launched by pgAssistant */ CREATE EXTENSION IF NOT EXISTS pg_stat_statements;')
            except psycopg2.Error as e:  # Catch PostgreSQL-specific errors
                error_msg = f"Error while enabling pg_stat_statements: {e.pgcode or 'Unknown Code'} - {e.pgerror or str(e)}"
                info["error"] = error_msg  
                return info
            except Exception as e:  # Catch any other exceptions
                info["error"] = f"Unexpected error: {str(e)}"
                return info
            finally:
                if cursor is not None:  
                    cursor.close()  # Ensure the cursor is closed properly

            version, _= db_query(con,'db_version')
            info['version']=version[0]['server_version']

            size, _= db_query(con,'db_size',db_config['db_name'])
            info["size"]=size[0]['pg_size_pretty']

            try:
                cache, _= db_query(con,'db_cache')
                info["cache"]=cache[0]['ratio']
            except:
                info["cache"]=0

            table_size, _= db_query(con,'table_size_top_5')
            info["table_size"]=table_size

            info['profile'], _= db_query(con,'database_profile')

            connexions, _= db_query(con,'database_count_connexions')
            info['connexions']=connexions[0]['nb']

            max_connexions, _= db_query(con,'database_max_connexions')
            info['max_connexions']=max_connexions[0]['setting']

            database_top_clients, _= db_query(con,'database_top_clients')
            info['top_clients']=database_top_clients

            issue_idx_redundant, _= db_query(con,'issue_idx_redundant')
            info['issue_idx_redundant'] = len(issue_idx_redundant)

            issue_idx_fk_missing, _= db_query(con,'issue_idx_fk_missing')
            info['issue_idx_fk_missing'] = len(issue_idx_fk_missing)    

            issue_no_pk, _= db_query(con,'issue_no_pk')
            info['issue_no_pk'] = len(issue_no_pk)  

            issue_idx_fk_datatype, _= db_query(con,'issue_idx_fk_datatype')
            info['issue_idx_fk_datatype'] = len(issue_idx_fk_datatype)

            try:
                conflicts, _=  db_query(con,'database_count_conlicts')
                info['conflicts']=conflicts[0]['nb']
            except:
                info['conflicts']="???"
        con.close()
    else:
        info["error"]=message
    return info

def get_pgstat_query_by_id(db_config, query_id):
    query = get_query_by_id('pgstat_get_sqlquery_by_id')
    sql=query['sql'].replace ('$1', query_id)
    con, _ = connectdb(db_config)
    sql_text=''
    if con:
        sql_rows=json.loads(db_fetch_json(con,sql))
        sql_text=sql_rows[0]['query']
    return sql_text

def get_query_by_id(query_id):
    get_queries()

    for query in PGA_QUERIES['sql']:
        if query_id == query['id']:
            return query
    return None

def search(key):
    get_queries()

    rows=[]
    searchkey=key.lower().strip()
    for query in PGA_QUERIES['sql']:
        if searchkey in query['description'].lower() or searchkey in query['category'].lower() or searchkey in query['id'].lower():
            rows.append(query)
    return rows
    
def db_query(cnx, query_id, db_name=None):
    get_queries()

    for query in PGA_QUERIES['sql']:
        if query['id']==query_id:
            sql=query['sql']
            if db_name:
                sql = sql.replace ('$1', db_name)
            if query['type']=='select' or query['type']=='param_query':
                return json.loads(db_fetch_json(cnx,sql)),query
            else:
                db_exec(cnx,sql)

def get_my_queries():
    if os.path.isfile("myqueries.json"):
        rows=[]
        with open("myqueries.json", encoding="utf-8") as f_in:
            userqueries=json.load(f_in)
        for query in userqueries['sql']:
            rows.append(query)
        return rows
    return []

def get_pga_tables():
    return PGA_TABLES

def get_queries():
    global PGA_QUERIES
    global PGA_TABLES

    # get the standard json queries
    if PGA_QUERIES=={}:
    #if not PGA_QUERIES.get('sql'):
        with open("queries.json", encoding="utf-8") as f_in:
            PGA_QUERIES=json.load(f_in)

            # get tables names from each pgassistant queries
            PGA_TABLES=[]
            for query in PGA_QUERIES.get('sql'):
                tables=sqlhelper.get_tables(query['sql'])
                for table in tables:
                    if table not in PGA_TABLES:
                        PGA_TABLES.append(table)

        #get the user defined queries
        if os.path.isfile("myqueries.json"):
            with open("myqueries.json", encoding="utf-8") as f_in:
                userqueries=json.load(f_in)
            PGA_QUERIES['sql']=PGA_QUERIES['sql']+userqueries['sql']
            
def get_pg_tune_parameter(db_config):
    """
    Retrieves PostgreSQL tuning parameters and version.
    
    :param db_config: Database configuration dictionary.
    :return: Dictionary of tuning parameters and major version.
    """    
    con, message = connectdb(db_config)
    if con:
        # get the the current setting of key pgtune run-time parameters.
        running_values={}
        params=['max_connections','shared_buffers','effective_cache_size',
                'maintenance_work_mem','checkpoint_completion_target','wal_buffers',
                'default_statistics_target','random_page_cost','effective_io_concurrency',
                'work_mem','huge_pages','min_wal_size','max_wal_size',
                'max_worker_processes','max_parallel_workers_per_gather',
                'max_parallel_workers','max_parallel_maintenance_workers']
        for aparam in params:
            sql = 'SHOW ' + aparam + ';'
            value=json.loads(db_fetch_json(con,sql))
            running_values[aparam]=value[0][aparam]

        # get the database version
        version_raw, _= db_query(con,'db_version')
        version=version_raw[0]['server_version']

        # alter system command supported by versions >= 12
        if '.' in version:
            major=version.split('.',1)[0]
        else:
            major=version
        
        con.close()
        return running_values, major


def get_existing_indexes(db_config):
    """
    Retrieves existing indexes from PostgreSQL.
    
    :param db_config: Database configuration dictionary.
    :return: Dictionary {table_name: set(frozenset(columns))} of existing indexes.
    """
    existing_indexes = {}
    try:
        conn, message = connectdb(db_config)
        if (conn):
            cur = conn.cursor()

            query = """
            SELECT tablename, indexdef FROM pg_indexes where schemaname !='pg_catalog';
            """

            cur.execute(query)
            indexes = cur.fetchall()

            for table, index_def in indexes:
                
                # Extract column names
                match = re.search(r"ON\s+(?:ONLY\s+)?\S+\s+USING\s+\w+\s*\((.*?)\)", index_def, re.IGNORECASE)
                if not match:
                    print ("**** ERROR WHILE PARSING INDEXE DEFINITION > ", index_def, table)
                if match:
                    indexed_columns = tuple(col.strip() for col in match.group(1).split(","))  # Convertir en tuple (ordre important)
                    
                    if table not in existing_indexes:
                        existing_indexes[table] = set()
                    existing_indexes[table].add(indexed_columns)  # Stocker sous forme de tuple immuable

            cur.close()
            conn.close()
    except Exception as e:
        print(f"⚠️ Error while getting indexes definition : {e}")

    return existing_indexes