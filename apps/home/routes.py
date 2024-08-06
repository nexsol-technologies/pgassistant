# -*- encoding: utf-8 -*-
"""
Main routes
"""

from apps.home import blueprint
from flask import render_template, request, session,redirect
from flask_login import login_required, current_user
from jinja2 import TemplateNotFound
import sqlfluff
from sqlfluff.core import FluffConfig
from . import database
from . import llm
import re

def handle_database_post(segment: str):
    dbinfo = {}
    session.permanent = True
    for key, val in request.form.items():
        session[key] = val
    session.modified = True

    dbinfo = database.get_db_info(session)

    if "error" in dbinfo:
        return render_template(f"home/{segment}", segment=segment, dbinfo=dbinfo)  

    return render_template("home/dashboard.html", segment="dashboard.html", dbinfo=dbinfo)

def handle_database_get(segment: str):
    return render_template(f"home/{segment}", segment=segment, dbinfo={})

def handle_dashboard_get(segment: str):
    if session.get("db_name"):
        dbinfo = database.get_db_info(session)
        return render_template("home/dashboard.html", segment=segment, dbinfo=dbinfo)
    else:
        return redirect("/database.html")

def handle_topqueries_get(template: str, segment: str):
    if session.get("db_name"):
        rows = database.get_top_queries(session)
        return render_template(f"home/{template}", segment=segment, rows=rows)
    else:
        return redirect("/database.html")

def handle_reset_pg_statistics():
    database.exec_cmd(session, "pg_stat_statements_reset")
    rows = database.get_top_queries(session)
    return render_template("home/topqueries.html", segment="topqueries.html", rows=rows)

def handle_enable_pg_statistics():
    database.exec_cmd(session, "pg_stat_statements_enable")
    rows = database.get_top_queries(session)
    return render_template("home/topqueries.html", segment="topqueries.html", rows=rows)

def handle_lint_post():
    original_sql = request.form.get('sqlo')
    config = FluffConfig(
    overrides={
        "dialect": "postgres",
        # NOTE: We explicitly set the string "none" here rather
        # than a None literal so that it overrides any config
        # set by any config files in the path.
        "library_path": "none",
        "capitalisation_policy": "upper"
    }
)
    linted_sql = sqlfluff.fix(original_sql, 
                              #dialect='postgres', 
                              fix_even_unparsable=True,
                              config=config)
    return render_template("home/lint.html", segment="lint.html",
                           sqlo=original_sql, linted=linted_sql)

def handle_search_post():
    searchkey = request.form.get('searchkey')
    rows = database.search(searchkey)
    return render_template("home/search.html", segment="search.html", rows=rows, searchkey=searchkey)


@blueprint.route('/index')
def index():
    return redirect("/database.html")

@blueprint.route('/generic/<genericid>', methods=['GET', 'POST'])
def generic(genericid):
    try:
        if session.get("db_name"):
            segment=genericid
            query_rows,description=database.generic_select(session,genericid)
            return render_template("home/generic.html", rows=query_rows, segment=segment, genericid=genericid, description=description )
        else:
            return redirect("/database.html")
    except Exception as e1:
        return render_template('home/page-500.html', err=e1), 500

@blueprint.route('/generic_param/<genericid>', methods=['GET', 'POST'])
def generic_param(genericid):
    try:
        if session.get("db_name"):
            rows = []
            query = database.get_query_by_id(genericid)
            sql_query = query['sql']
            # extract parameters list
            pattern = r'\$[0-9]+' 
            parameters = re.findall(pattern, query['sql'])
            print ( parameters )

            if request.method == 'POST':
                for key, val in request.form.items():
                    sql_query = sql_query.replace (key,val)
                rows = database.generic_select_with_sql(session,sql_query)

            return render_template('home/generic_param.html', parameters=parameters, query=sql_query, rows=rows, description=query['description'] )
        else:
            redirect("/database.html")
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception as e1:
        return render_template('home/page-500.html', err=e1), 500

@blueprint.route('/analyze/<querid>', methods=['GET', 'POST'])
def analyze_query(querid):
    try:
        chatgpt = ""
        if session.get("db_name"):
            rows = []
            sql_query = database.get_pgstat_query_by_id(session,querid)
            
            # extract parameters list
            pattern = r'\$[0-9]+' 
            parameters = re.findall(pattern, sql_query)

            if request.method == 'POST':
                for key, val in request.form.items():
                    print (key,val)
                    sql_query = sql_query.replace (key,val)
                sql_query_analzye = 'EXPLAIN ANALYZE  ' + sql_query
                rows = database.generic_select_with_sql(session,sql_query_analzye)
                chatgpt = llm.get_llm_query_for_query_analyze(sql_query=sql_query_analzye, rows=rows)
                if request.form.get('submit')=='chatgpt':
                    chatgpt_response=llm.query_chatgpt(chatgpt)
                    return render_template('home/chatgpt.html', chatgpt_response=chatgpt_response)
                elif request.form.get('submit')=='optimize':
                    question_optimize=llm.get_llm_query_for_query_optimize(sql_query)
                    chatgpt_response=llm.query_chatgpt(question_optimize)
                    return render_template('home/chatgpt.html', chatgpt_response=chatgpt_response)

            return render_template('home/analyze.html', parameters=parameters, query=sql_query, rows=rows, description='Analyze query',chatgpt=chatgpt )
        else:
            dbinfo= {}
            return redirect("/database.html")
    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception as e1:
        return render_template('home/page-500.html', err=e1), 500


@blueprint.route('/<template>', methods=['GET', 'POST'])
def route_template(template: str):
    try:
        if not template.endswith('.html'):
            template += '.html'

        segment = get_segment(request)
        if segment == "database.html" and request.method == 'POST':
            return handle_database_post(segment)
        elif segment == "database.html":
            return handle_database_get(segment)
        elif segment == "dashboard.html" and request.method == 'GET':
            return handle_dashboard_get(segment)
        elif segment == "topqueries.html" and request.method == 'GET':
            return handle_topqueries_get(template, segment)
        elif segment == "reset_pg_statistics.html":
            return handle_reset_pg_statistics()
        elif segment == "enable_pg_statistics.html":
            return handle_enable_pg_statistics()
        elif segment == "lint.html" and request.method == 'POST':
            return handle_lint_post()
        elif segment == "search.html" and request.method == 'POST':
            return handle_search_post()
        
        return render_template(f"home/{template}", segment=segment, dbinfo={})

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404
    except Exception as e:
        return render_template('home/page-500.html', err=str(e)), 500

# Helper - Extract current page name from request
def get_segment(request):
    try:
        segment = request.path.split('/')[-1]
        if segment == '':
            segment = 'database'
        return segment
    except:
        return None
