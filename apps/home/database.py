import datetime
import decimal
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import collections
from flask import g
from . import pgtune
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
    try:
        con = psycopg2.connect(database=db_config["db_name"],
                            host=db_config["db_host"],
                            user=db_config["db_user"],
                            password=db_config["db_password"],
                            port=db_config["db_port"],
                            connect_timeout=5,
                            application_name="pgAssistant 1.7")
        con.set_session(autocommit=True)
    except psycopg2.Error as err:
        return None, format(err).rstrip()
    return con, "OK"

def db_exec(conn, sql):
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
    try:
        conn.set_session(autocommit=True)
        cursor = conn.cursor()
        cursor.execute(sql)
        return {"success": True, "message": f"SQL executed successfully: {sql}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()

def get_json_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)

def execute_and_fetch(cursor, query):
    cursor.execute(query)
    res = cursor.fetchall()
    cursor.close()
    return res

def get_json_response(conn, query):
    cursor = get_json_cursor(conn)
    response = execute_and_fetch(cursor, query)
    return json.dumps(response)

def defaultconverter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()
    elif isinstance(o, decimal.Decimal):
        return str(o)
    
def db_fetch_json(conn,sql):
    #Creating a cursor object using the cursor() method
    cursor = get_json_cursor(conn)
    response = execute_and_fetch(cursor, sql)
    return json.dumps(response, default = defaultconverter)

def get_top_queries(db_config):
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
            version, _= db_query(con,'db_version')
            info['version']=version[0]['server_version']

            size, _= db_query(con,'db_size',db_config['db_name'])
            info["size"]=size[0]['pg_size_pretty']

            try:
                cache, _= db_query(con,'db_cache')
                info["cache"]=cache[0]['ratio']
            except:
                info["cache"]="???"

            table_size, _= db_query(con,'table_size_top_5')
            info["table_size"]=table_size

            info['profile'], _= db_query(con,'database_profile')

            connexions, _= db_query(con,'database_count_connexions')
            info['connexions']=connexions[0]['nb']
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



