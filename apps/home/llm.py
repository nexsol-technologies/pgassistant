from openai import OpenAI
from .ddl import generate_tables_ddl
from .sqlhelper import get_tables
import os
import markdown

def query_chatgpt(question):
    api_key=os.environ.get('OPENAI_API_KEY', None)
    project=os.environ.get('OPENAI_API_PROJECT', None)

    if not api_key:
        raise Exception("The environment variable OPENAI_API_KEY is not set. I can't use OpenAPI !")

    #client = OpenAI(api_key=api_key, project=project,base_url = 'http://localhost:11434/v1')
    client = OpenAI(api_key=api_key, project=project)
    completion = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a Postgresql database expert"},
        {"role": "user", "content": question }
    ]
    )
    print (markdown.markdown(completion.choices[0].message.content,
            extensions=["fenced_code", "codehilite", "extra"]))
    return(markdown.markdown(completion.choices[0].message.content,extensions=["fenced_code", "codehilite", "extra"]))

def get_llm_query_for_query_analyze (host, port, database, user, password, sql_query, rows):
    query = sql_query.replace ("EXPLAIN ANALYZE  ", "")
    tables = get_tables(query)
    print (sql_query, tables)
    ddl = generate_tables_ddl(host, port, database, user, password, tables)

    llm = (
        "I have a PostgreSQL query that I would like to optimize. Below, I have provided the necessary details:\n"
        f"1. **DDL of the table(s) involved**:\n{ddl}\n"
        f"2. **The SQL query**:\n{sql_query}\n"
        "3. **`EXPLAIN ANALYZE` output**:\n"
    )
    llm += "\n".join(row['QUERY PLAN'] for row in rows)
    llm += "\n"
    llm += "Could you analyze this query and suggest optimizations? If optimizations are possible, please provide the necessary SQL statements (e.g., additional indexes or query rewrites) and explain the reasoning behind your recommendations."
    return llm

def get_llm_query_for_query_optimize (sql_query):
    llm = (
        "Could you optimize this postgresql query for me : \n "
        f"{sql_query}\n"
    )
    return llm