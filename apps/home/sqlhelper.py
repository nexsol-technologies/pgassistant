from sql_metadata import Parser

def get_tables(query):
    try:
        tables = Parser(query.lower()).tables
        return tables
    except:
        return []

