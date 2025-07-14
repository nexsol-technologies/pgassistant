import sqlglot
from sqlglot.expressions import Column, Binary, Literal, And, Or, EQ, GT, LT, Like, Parameter, Table, Select, From, Subquery, In,Paren, GTE, LTE, NEQ


def extract_binary_conditions(expression):
    """
    Recursive function to extract all binary conditions (=, >, <, IN, LIKE, etc.),
    including those wrapped in parentheses.

    :param expression: AST node from SQLGlot
    :return: List of found binary conditions
    """
    conditions = []

    if expression is None:
        return conditions

    # Base case: it's a binary condition
    if isinstance(expression, (EQ, GT, LT, GTE, LTE, NEQ, In, Like)):
        conditions.append(expression)

    # Handle parentheses (e.g. WHERE (a = $1 AND b = $2))
    elif isinstance(expression, Paren):
        conditions.extend(extract_binary_conditions(expression.this))

    # Handle logical combinations and subqueries
    elif isinstance(expression, (And, Or, Subquery, Select)):
        left_expr = expression.args.get("this")
        right_expr = expression.args.get("expression")

        if left_expr:
            conditions.extend(extract_binary_conditions(left_expr))
        if right_expr:
            conditions.extend(extract_binary_conditions(right_expr))

    return conditions


def extract_table_aliases(expression):
    """
    Retrieves table aliases defined in the FROM clause and JOINs.

    :param expression: AST expression from SQLGlot
    :return: Dictionary {alias: actual_table_name}
    """
    aliases = {}

    # Find all tables in FROM and JOIN
    for table in expression.find_all(Table):
        table_name = table.name
        alias = table.alias_or_name
        if alias:  # If the table has an alias, add it
            aliases[alias] = table_name

    return aliases


def find_table_for_column(column, table_aliases, default_table):
    """
    Finds the table associated with a column by replacing aliases.

    :param column: SQLGlot Column object
    :param table_aliases: Dictionary of table aliases
    :param default_table: Default table name
    :return: Associated table name
    """
    if column.table:
        table_name = table_aliases.get(column.table, column.table)  # Replace alias with actual name
        return table_name
    return default_table


def extract_parameter_columns(sql_query):
    """
    Parses an SQL query and returns a mapping of parameters ($1, $2, etc.) to the used columns.

    :param sql_query: SQL query as a string
    :return: Dictionary {parameter: table.column}
    """
    # Parse the SQL query with sqlglot
    try:
        expression = sqlglot.parse_one(sql_query, dialect="postgres")
    except sqlglot.errors.ParseError as e:
        return {}
    
    param_columns = {}

    # Retrieve table aliases
    table_aliases = extract_table_aliases(expression)

    # Retrieve all WHERE clauses (including those in subqueries)
    where_clauses = expression.find_all(sqlglot.expressions.Where)

    for where_clause in where_clauses:

        # Find the table used in this WHERE clause (to handle subqueries)
        parent_select = where_clause.find_ancestor(Select)
        if parent_select:
            subquery_table_aliases = extract_table_aliases(parent_select)
            default_table = next(iter(subquery_table_aliases.values()), None)
        else:
            subquery_table_aliases = table_aliases
            default_table = next(iter(table_aliases.values()), None)

        # Extract all binary conditions (including those in subqueries)
        conditions = extract_binary_conditions(where_clause.this)

        for condition in conditions:
            left, right = condition.args.get("this"), condition.args.get("expression")

            if left is None or right is None:
                continue

            # Check if `right` is a parameter (with a `Literal` inside)
            if isinstance(left, Column) and isinstance(right, Parameter) and isinstance(right.this, Literal):
                param_key = str(right.this.this)  # Extract the parameter number
                column_table = find_table_for_column(left, table_aliases, default_table)  # Apply aliases
                column_name = left.name
                full_column_name = f"{column_table}.{column_name}"
                
                param_columns[param_key] = full_column_name
            elif isinstance(right, Column) and isinstance(left, Parameter) and isinstance(left.this, Literal):
                param_key = str(left.this.this)  # Extract the parameter number
                column_table = find_table_for_column(right, table_aliases, default_table)  # Apply aliases
                column_name = right.name
                full_column_name = f"{column_table}.{column_name}"
                param_columns[param_key] = full_column_name

    return param_columns