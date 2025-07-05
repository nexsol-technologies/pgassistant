import re
import psycopg2
from datetime import datetime
from sql_metadata import Parser
from sql_formatter.core import format_sql
from . import database
from . import analyze_param
import json

def get_tables(query):
    """
    Extracts table names from an SQL query.

    :param query: The SQL query as a string.
    :return: A list of table names used in the query. Returns an empty list if extraction fails.
    """    
    try:
        tables = Parser(query.lower()).tables
        return tables
    except:
        return []

def get_sql_type(sql_query):
    """
    which query type  : SELECT, INSERT, UPDATE, DELETE, etc.
    
    :param sql_query: the SQL query.
    :return: query type (str).
    """
    try:
        parser = Parser(sql_query)
        sqltype = parser.query_type.replace ('QueryType.', '')
        return sqltype.lower()
    except:
        return "unknown"

def get_formated_sql(sql_query):
    """
    Formats an SQL query for better readability.

    :param sql_query: The raw SQL query as a string.
    :return: The formatted SQL query if formatting succeeds, otherwise returns the original query.
    """    
    try:
        sqlf = format_sql(sql_query)
        return sqlf
    except:
        return sql_query
    
def replace_query_parameters(query, params):
    """
    Remplace les paramètres ($1, $2, etc.) dans une chaîne SQL par leurs valeurs.

    Args:
        query (str): La chaîne SQL contenant les paramètres sous la forme $1, $2, etc.
        params (dict): Un dictionnaire contenant les paramètres (ex: {1: 'xx', 2: 'yy'}).

    Returns:
        str: La chaîne SQL avec les paramètres remplacés par leurs valeurs.
    """
    def replace_match(match):
        # Extraire le numéro du paramètre
        param_index = int(match.group(1))
        # Obtenir la valeur du paramètre
        value = params.get(param_index)
        if value is None:
            value = ''
        return str(value)

    # Remplacer tous les paramètres $1, $2, ... dans la requête
    if "$" in query:
        modified_query = re.sub(r"\$(\d+)", replace_match, query)
    else:
        modified_query=query

    return modified_query

def parse_most_common_vals(value):
    """Parse PostgreSQL's most_common_vals field into a Python list."""
    
    print(value)
    if not value or value == "{}":
        return []  # Retourne une liste vide si NULL ou vide

    # Vérifier si la valeur est bien une chaîne
    if isinstance(value, tuple):  
        value = value[0]  # Extraire la première valeur du tuple

    if value is None:
        return []

    # Supprimer les accolades `{}` autour de la chaîne
    value = value.strip("{}")

    # Expression régulière pour capturer :
    # - Les valeurs entre guillemets (ex: "John Doe", "2024-12-23 08:31:35.616712")
    # - Les valeurs non guillemetées (ex: F, M, 2020-07-21, 1238)
    pattern = r'"([^"]+)"|([^,]+)'

    matches = re.findall(pattern, value)
    
    parsed_values = []
    for match in matches:
        raw_value = match[0] if match[0] else match[1]  # Priorité à la valeur entre guillemets

        # Tentative de conversion en date (format PostgreSQL)
        try:
            parsed_value = str(datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S.%f"))  # Format timestamp
        except ValueError:
            try:
                parsed_value = str(datetime.strptime(raw_value, "%Y-%m-%d"))  # Format date simple
            except ValueError:
                # Tentative de conversion en entier
                try:
                    parsed_value = int(raw_value)
                except ValueError:
                    parsed_value = raw_value  # Garder sous forme de chaîne si tout échoue
        
        parsed_values.append(parsed_value)

    return parsed_values

def extract_schema_table(full_name):
    """Split vars 'schema.table' or 'table'."""
    parts = full_name.split('.')
    if len(parts) == 2:
        schema, table = parts
    else:
        schema, table = None, parts[0]  # No schema=None
    return schema, table

def fetch_column_data(table, column, data_type, session):
    """
    Fetch up to 10 rows from a specific column of a table and return the result as a typed JSON array.

    Args:
        table (str): The name of the table.
        column (str): The name of the column.
        data_type (str): The PostgreSQL data type of the column.
        connection_params (dict): Connection parameters for psycopg2.

    Returns:
        list: A JSON array of the results with correctly typed data.
    """
    try:
        conn, msg = database.connectdb(session)
        if "OK" in msg:
        # Connect to the database
            with conn.cursor() as cursor:

                # Try to select pg_stats most_columns_vals
                schema, tablename = extract_schema_table(table)
                if schema is None:
                    query = f"select most_common_vals from pg_stats where tablename='{table}' and attname='{column}' limit 1"
                else:
                    query = f"select most_common_vals from pg_stats where schemaname='{schema}' and tablename='{tablename}' and attname='{column}' limit 1"

                cursor.execute (query)
                row = cursor.fetchall()
               

                if row and row[0]:  # check null values
                    values_common=parse_most_common_vals(row[0])
                    if len(values_common)>0:
                        return values_common

                # Generate the SQL query
                query = f"SELECT {column} FROM {table} LIMIT 10;"
                              
                # Execute the query
                cursor.execute(query)
                rows = cursor.fetchall()
                

                # Map PostgreSQL types to Python types
                def convert_value(value):
                    if value is None:
                        return None
                    if data_type in ('integer', 'bigint', 'smallint'):
                        return int(value)
                    elif data_type in ('real', 'double precision', 'numeric'):
                        return float(value)
                    elif data_type in ('boolean',):
                        return bool(value)
                    else:
                        return str(value)  # Default: Treat as string

                # Process the results
                result = [convert_value(row[0]) for row in rows]
                return result

    except Exception as e:
        print(f"Error: {e}")
        return []

def get_column_data_types(connection, table_column_pairs):
    """
    Query PostgreSQL to get the data types of specific columns in tables.
    Args:
        connection: psycopg2 connection object.
        table_column_pairs: A list of tuples (table_name, column_name).
    Returns:
        A dictionary { (table_name, column_name): column_type }.
    """
    column_types = {}
    query = """
        SELECT
            table_schema,
            table_name,
            column_name,
            data_type
        FROM
            information_schema.columns
        WHERE
            (table_name, column_name) IN %s;
    """
    try:
        # Prepare data for the IN clause
        formatted_pairs = [(table, column) for table, column in table_column_pairs]
        if not formatted_pairs:
            print("No table-column pairs provided.")
            return {}

        # Execute the query
        with connection.cursor() as cursor:
            cursor.execute(query, (tuple(formatted_pairs),))
            for row in cursor.fetchall():
                schema_name = row[0]
                table_name = row[1]
                column_name = row[2]
                column_type = row[3]
                column_types[(f"{schema_name}.{table_name}", column_name)] = column_type
    except Exception as e:
        print(f"Error querying column data types: {e}")
    
    return column_types


def map_query_parameters(query, connection):
    """
    Extracts SQL parameters and retrieves their corresponding data types from PostgreSQL.
    
    Args:
        query: The SQL query string.
        connection: psycopg2 connection object.
    
    Returns:
        A dictionary { parameter: (table_name, column_name, data_type) }.
    """
    # Extraire les paramètres SQL et leurs colonnes associées
    param_columns = analyze_param.extract_parameter_columns(query)

    if not param_columns:
        print("No SQL parameters found.")
        return {}

    # Convertir les données pour la requête PostgreSQL
    table_column_pairs = [(table_column.split('.')[0], table_column.split('.')[1]) for table_column in param_columns.values()]

    # Récupérer les types de données des colonnes
    column_types = get_column_data_types(connection, table_column_pairs)


    # Associer chaque paramètre SQL à son (table, colonne, data_type)
    param_mapping = {}
    for param, column in param_columns.items():
        table_name, column_name = column.split('.')
        column_key = (table_name, column_name)

        # Vérifier si la clé est présente avec un schéma (ex: public.authors)
        matching_key = next((key for key in column_types.keys() if key[1] == column_name and key[0].endswith(table_name)), None)

        if matching_key:
            column_type = column_types[matching_key]
            resolved_table_name = matching_key[0]  # Utiliser le nom de la table avec schéma
        else:
            column_type = "UNKNOWN"
            resolved_table_name = table_name
            print(f"⚠️ Warning: Column {column_key} not found in column_types. Returning UNKNOWN.")

        param_mapping[param] = (resolved_table_name, column_name, column_type)
    return param_mapping


def split_query_by_parameters(query, parameters):
    """
    Split the query into smaller parts based on the presence of multiple parameters in a single line.
    Args:
        query: The SQL query string.
        parameters: List of parameters ($1, $2, etc.).
    Returns:
        A list of query fragments, each containing at most one parameter.
    """
    fragments = []
    for line in query.splitlines():
        # Split the line further if it contains multiple parameters
        parts = re.split(rf"({'|'.join(parameters)})", line)
        for part in parts:
            if part.strip():  # Ignore empty parts
                fragments.append(part.strip())
    return fragments

def get_genius_parameters (sql_query, session):
    conn, msg = database.connectdb(session)
    if "OK" in msg:     
        parameter_mapping = map_query_parameters(sql_query, conn)   
        return parameter_mapping
    return None

def analyze_explain_row(row):
    """
    Generates a comment based on the content of an EXPLAIN ANALYZE row.
    The input row is a dictionary with a 'QUERY PLAN' key.
    """
    query_plan = row.get('QUERY PLAN', '')

    if 'Seq Scan' in query_plan:
        return "⚠️ Sequential scan detected. Consider adding an index."
    elif 'Bitmap Heap Scan' in query_plan:
        return "🟡 Bitmap heap scan used. Consider an index scan if performance is slow."
    elif 'Bitmap Index Scan' in query_plan:
        return "🟡 Bitmap index scan used. Works well if not scanning too many pages."    
    elif 'Index Scan' in query_plan:
        return "✅ Efficient index scan detected."
    elif 'Index Only Scan' in query_plan:
        return "🚀 Very efficient index-only scan. No need to access the table directly."
    elif 'Nested Loop' in query_plan:
        return "⚠️ Nested loop detected. Ensure indexes exist on join conditions."
    elif 'Hash Join' in query_plan:
        return "🟢 Hash join used. Efficient for large datasets."
    elif 'Merge Join' in query_plan:
        return "🟡 Merge join detected. Ensure both tables are sorted for efficiency."
    elif 'Sort' in query_plan:
        return "⚠️ Sorting operation detected. Increase work_mem if sorting large datasets."
    elif 'HashAggregate' in query_plan:
        return "⚠️ Hash aggregate used. May be slow if memory is insufficient."
    elif 'Materialize' in query_plan:
        return "🟡 Materialize used. Can increase memory usage."
    elif 'CTE Scan' in query_plan:
        return "⚠️ Common Table Expression (CTE) Scan. Consider inlining if performance is slow."
    elif 'Gather' in query_plan:
        return "🔄 Parallel execution detected. Improves performance on large datasets."
    elif 'Disk Spill' in query_plan:
        return "❌ Disk spill detected. Increase work_mem to avoid slow disk operations."
    elif 'External Merge Disk' in query_plan:
        return "❌ External disk merge detected. PostgreSQL is using disk instead of memory."
    else:
        return ""