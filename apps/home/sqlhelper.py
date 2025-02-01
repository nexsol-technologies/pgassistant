import re
import psycopg2
from sql_metadata import Parser
from sql_formatter.core import format_sql
from . import database
import json

def get_tables(query):
    try:
        tables = Parser(query.lower()).tables
        return tables
    except:
        return []
    
def get_formated_sql(sql_query):
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
    Analyze the SQL query to map parameters ($1, $2, ...) to their table, column, and types.
    Args:
        query: The SQL query string.
        connection: psycopg2 connection object.
    Returns:
        A dictionary { parameter: (table, column, data_type) }.
    """
    # Use sql_metadata to parse the query
    try:
        parser = Parser(query)
    except:
        return {}

    # Extract tables and columns from the query
    tables = parser.tables  # List of tables in the query
    columns_dict = parser.columns_dict  # Dictionary of columns by context

    # Extract parameters like $1, $2, etc.
    parameters = sorted(set(re.findall(r"\$\d+", query)))

    # Prepare table-column pairs for querying PostgreSQL
    table_column_pairs = []
    for context, columns in columns_dict.items():
        for column in columns:
            if '.' in column:  # Ensure the column is fully qualified (table.column)
                table, col = column.split('.', 1)
                table_column_pairs.append((table, col))

    # Query PostgreSQL to get column data types
    column_data_types = get_column_data_types(connection, table_column_pairs)

    # Split the query into manageable fragments
    query_fragments = split_query_by_parameters(query, parameters)

    # Map parameters to their respective tables, columns, and types
    parameter_mapping = {}
    for param in parameters:
        # Locate the parameter in the query fragments
        for fragment in query_fragments:
            if param in fragment:
                
                # Find the most relevant table and column for the parameter
                best_match = None
                for (full_table, column), data_type in column_data_types.items():
                    schema, table = full_table.split('.')
                    alias_variants = [f"{table}.{column}", f"{column}"]  # Add table.column and column formats
                    for variant in alias_variants:
                        if variant in fragment:
                            
                            # Prefer the first exact match
                            best_match = (full_table, column, data_type)
                            break
                if best_match:
                    parameter_mapping[param] = best_match
                    break

    return parameter_mapping


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
        query=format_sql(sql_query)
        
        parameter_mapping = map_query_parameters(query, conn)
        
        return parameter_mapping
    return None


