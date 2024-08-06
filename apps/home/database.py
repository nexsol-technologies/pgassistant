import datetime
import decimal
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
import collections
from flask import g


PGA_QUERIES={}

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
                            application_name="pgAssistant 1.0")
        con.set_session(autocommit=True)
    except psycopg2.Error as err:
        return None, format(err).rstrip()
    return con, "OK"

def db_exec(conn, sql):
    conn.set_session(autocommit=True)
    cursor = conn.cursor()
    cursor.execute(sql)

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

            cache, _= db_query(con,'db_cache')
            if cache:
                info["cache"]=cache[0]['ratio']
            else:
                info["cache"]="???"

            table_size, _= db_query(con,'table_size_top_5')
            info["table_size"]=table_size

            info['users'], _= db_query(con,'users')
            info['profile'], _= db_query(con,'database_profile')

            connexions, _= db_query(con,'database_count_connexions')
            info['connexions']=connexions[0]['nb']

            conflicts, _=  db_query(con,'database_count_conlicts')
            info['conflicts']=conflicts[0]['nb']
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

def get_queries():
    # get the standard json queries
    global PGA_QUERIES

    if not PGA_QUERIES.get('sql'):
        with open("queries.json", encoding="utf-8") as f_in:
            PGA_QUERIES=json.load(f_in)

        #get the user defined queries
        if os.path.isfile("myqueries.json"):
            with open("myqueries.json", encoding="utf-8") as f_in:
                userqueries=json.load(f_in)
            PGA_QUERIES['sql']=PGA_QUERIES['sql']+userqueries['sql']
            
