import sqlglot
from sqlglot.expressions import Column, Binary, Literal, And, Or, EQ, GT, LT, Like, Parameter, Table, Select, From, Subquery, In

def extract_binary_conditions(expression):
    """
    Fonction récursive pour extraire toutes les conditions binaires (=, >, <, IN, LIKE, etc.).
    
    :param expression: Noeud de l'AST SQLGlot
    :return: Liste des conditions binaires trouvées
    """
    conditions = []

    if isinstance(expression, (EQ, GT, LT, In, Like)):  # Comparaisons =, >, <, IN, LIKE
        conditions.append(expression)
    
    elif isinstance(expression, (And, Or, Subquery, Select)):  # Si c'est un AND/OR/Sous-requête, on explore ses sous-expressions
        left_expr = expression.args.get("this")
        right_expr = expression.args.get("expression")

        if left_expr:
            conditions.extend(extract_binary_conditions(left_expr))
        if right_expr:
            conditions.extend(extract_binary_conditions(right_expr))

    return conditions


def extract_table_aliases(expression):
    """
    Récupère les alias de table définis dans la clause FROM et les JOIN.

    :param expression: L'expression AST de SQLGlot
    :return: Dictionnaire {alias: vrai_nom_de_la_table}
    """
    aliases = {}

    # Trouver toutes les tables dans FROM et JOIN
    for table in expression.find_all(Table):
        table_name = table.name
        alias = table.alias_or_name
        if alias:  # Si la table a un alias, on l'ajoute
            aliases[alias] = table_name

    return aliases


def find_table_for_column(column, table_aliases, default_table):
    """
    Trouve la table associée à une colonne en remplaçant les alias.

    :param column: L'objet Column de SQLGlot
    :param table_aliases: Dictionnaire des alias de tables
    :param default_table: Nom de la table par défaut
    :return: Nom de la table associée
    """
    if column.table:
        table_name = table_aliases.get(column.table, column.table)  # Remplacer l'alias par le vrai nom
        return table_name
    return default_table


def extract_parameter_columns(sql_query):
    """
    Parse une requête SQL et renvoie un mapping des paramètres ($1, $2, etc.) vers les colonnes utilisées.

    :param sql_query: Requête SQL sous forme de chaîne
    :return: Dictionnaire {paramètre: table.colonne}
    """
    # Parser la requête SQL avec sqlglot
    expression = sqlglot.parse_one(sql_query, dialect="postgres")

    param_columns = {}

    # Récupérer les alias de table
    table_aliases = extract_table_aliases(expression)

    # Récupérer toutes les clauses WHERE (incluant celles dans les sous-requêtes)
    where_clauses = expression.find_all(sqlglot.expressions.Where)

    for where_clause in where_clauses:

        # Trouver la table utilisée dans cette clause WHERE (pour gérer les sous-requêtes)
        parent_select = where_clause.find_ancestor(Select)
        if parent_select:
            subquery_table_aliases = extract_table_aliases(parent_select)
            default_table = next(iter(subquery_table_aliases.values()), None)
        else:
            subquery_table_aliases = table_aliases
            default_table = next(iter(table_aliases.values()), None)

        # Extraire toutes les conditions binaires (y compris celles dans des sous-requêtes)
        conditions = extract_binary_conditions(where_clause.this)

        for condition in conditions:
            left, right = condition.args.get("this"), condition.args.get("expression")

            if left is None or right is None:
                continue

            # Vérifier si `right` est un paramètre (avec un `Literal` dedans)
            if isinstance(left, Column) and isinstance(right, Parameter) and isinstance(right.this, Literal):
                param_key = str(right.this.this)  # Extraire le numéro du paramètre
                column_table = find_table_for_column(left, table_aliases, default_table)  # Appliquer les alias
                column_name = left.name
                full_column_name = f"{column_table}.{column_name}"
                
                param_columns[param_key] = full_column_name
            elif isinstance(right, Column) and isinstance(left, Parameter) and isinstance(left.this, Literal):
                param_key = str(left.this.this)  # Extraire le numéro du paramètre
                column_table = find_table_for_column(right, table_aliases, default_table)  # Appliquer les alias
                column_name = right.name
                full_column_name = f"{column_table}.{column_name}"
                param_columns[param_key] = full_column_name

    return param_columns