from sql_metadata import Parser

def extract_where_columns(sql_query, table_name):
    """
    Analyse une requête SQL et extrait les colonnes de la table spécifiée utilisées dans la clause WHERE.
    Utilise sql-metadata pour identifier les colonnes de la clause WHERE.

    :param sql_query: La requête SQL à analyser.
    :param table_name: Le nom de la table cible (ex: 'authors').
    :return: Liste des colonnes de la table utilisées dans la clause WHERE.
    """
    # Parser la requête SQL
    parser = Parser(sql_query)

    # Extraire les colonnes utilisées dans la clause WHERE
    where_columns = parser.columns_dict.get("where", [])

    # Filtrer uniquement les colonnes de la table cible
    filtered_columns = []
    for col in where_columns:
        # Vérifier si la colonne est sous forme "table.colonne"
        if "." in col:
            table, column = col.split(".", 1)
            if table == table_name:
                filtered_columns.append(col)  # On garde le format table.colonne
        else:
            # Cas où la colonne est utilisée sans alias explicite
            filtered_columns.append(f"{table_name}.{col}")

    return list(set(filtered_columns))  # Suppression des doublons

