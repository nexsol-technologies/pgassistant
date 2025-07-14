import sqlglot
from sqlglot.expressions import Column, Table, Where, From, Select, Join, Group, Order, Having

def extract_table_aliases(expression):
    """
    Retrieves the table aliases defined in the FROM clause and the JOIN statements.

    :param expression: The SQLGlot AST expression
    :return: Dictionary {alias: table name}
    """
    aliases = {}

    # Find all tables in FROM and JOIN
    for table in expression.find_all(Table):
        table_name = table.name
        alias = table.alias_or_name
        aliases[alias] = table_name

    return aliases


def extract_tables(expression):
    """
    Extracts all the tables used in the SQL query.

    :param expression: The SQLGlot AST expression
    :return: List of tables present in the query.
    """
    tables = set()
    
    # Find all mentioned tables
    for table in expression.find_all(Table):
        tables.add(table.name)

    return tables


def extract_columns_from_conditions(expression):
    """
    Extracts all the columns used in conditions (WHERE, JOIN ON, GROUP BY, HAVING).

    :param expression: The SQLGlot AST expression
    :return: List of columns used in conditions.
    """
    condition_columns = set()
    
    # Search all clauses containing conditions (WHERE, GROUP BY, HAVING, ORDER BY)
    condition_clauses = expression.find_all((Where, Group, Having, Order))
    
    for clause in condition_clauses:
        for column in clause.find_all(Column):
            condition_columns.add((column.table, column.name))

    # Add columns from `JOIN ON`
    for join in expression.find_all(Join):
        on_condition = join.args.get("on")
        if on_condition:
            for column in on_condition.find_all(Column):
                condition_columns.add((column.table, column.name))

    return condition_columns


def extract_columns_from_select(expression):
    """
    Extracts all the columns used in the SELECT clause.

    :param expression: The SQLGlot AST expression
    :return: List of columns used exclusively in SELECT.
    """
    select_columns = set()
    
    select_clause = expression.find(Select)
    if select_clause:
        for column in select_clause.find_all(Column):
            select_columns.add((column.table, column.name))

    return select_columns


def analyze_table_conditions(sql_query):
    """
    Analyzes an SQL query and returns a dictionary of tables with their columns used in conditions 
    (excluding those used only in SELECT).

    :param sql_query: The SQL query as a string
    :return: Dictionary {table: [columns used in conditions]}
    """
    # Parse the SQL query with sqlglot
    expression = sqlglot.parse_one(sql_query, dialect="postgres")

    # Retrieve table aliases (includes aliases in FROM and JOIN)
    table_aliases = extract_table_aliases(expression)

    # Retrieve all tables mentioned in the query
    tables = extract_tables(expression)

    # Retrieve columns used in conditions (WHERE, JOIN ON, etc.)
    condition_columns = extract_columns_from_conditions(expression)

    # Build a dictionary table -> columns
    table_columns = {table: [] for table in tables}

    for table, column in condition_columns:
        if not table and len(tables) == 1:
            resolved_table = list(tables)[0]
        else:
            resolved_table = table_aliases.get(table, table)

        if resolved_table in table_columns:
            table_columns[resolved_table].append(column)

    return table_columns

def check_index_coverage(indexes_dict, used_columns_dict):
    """
    Renvoie un dictionnaire indiquant, pour chaque table et chaque colonne utilisée,
    si la colonne est couverte par au moins un index existant.

    :param indexes_dict: Dictionnaire des indexes existants, par exemple :
        {
            'payment': {('payment_date', 'payment_id')},
            'actor': {('actor_id',), ('last_name',)},
            ...
        }

    :param used_columns_dict: Dictionnaire des tables et colonnes
                             présentes dans la requête, par exemple :
        {
            'books': ['book_id', 'author_id'],
            'loans': ['book_id', 'borrower_id', 'loan_date'],
            ...
        }

    :return: Un dictionnaire de la forme :
        {
            'books': {
                'book_id': True/False,
                'author_id': True/False
            },
            'loans': {
                'book_id': True/False,
                ...
            },
            ...
        }
    """
    coverage_info = {}

    for table, columns in used_columns_dict.items():
        coverage_info[table] = {}
        # Récupère l'ensemble des indexes pour la table ; renvoie set() si la table n'est pas trouvée
        table_indexes = indexes_dict.get(table, set())

        for col in columns:
            # Vérifie si au moins un index contient cette colonne
            is_covered = any(col in index_tuple for index_tuple in table_indexes)
            coverage_info[table][col] = is_covered

    return coverage_info

