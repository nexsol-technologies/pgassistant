def elements_distincts(liste):
    return list(dict.fromkeys(liste))


def add_or_update_table_info(tables_info, table_name, query_count, avg_execution_time, rows, operation_type, columns):
    """
    Met à jour ou ajoute les informations d'une table dans tables_info, en comptant les occurrences des types d'opérations.
    
    :param tables_info: Liste des dictionnaires contenant les infos des tables.
    :param table_name: Nom de la table concernée.
    :param query_count: Nombre de requêtes exécutées sur cette table.
    :param avg_execution_time: Temps moyen d'exécution de la requête.
    :param rows: Nombre de lignes concernées.
    :param operation_type: Type d'opération (INSERT, UPDATE, DELETE, etc.).
    :param columns: Les colonnes impliquées dans la clause where
    """
    
    # Vérifie si la table existe déjà dans la liste
    for table_info in tables_info:
        if table_info["table_name"] == table_name:
            # Met à jour les statistiques globales
            table_info["query_count"] += query_count
            table_info["rows"] += rows

            # Calcul du nouveau temps moyen pondéré
            total_queries = int(table_info["query_count"])
            table_info["avg_execution_time"] = float(table_info["avg_execution_time"])
            table_info["avg_execution_time"] = (
                (float(table_info.get("avg_execution_time", 0)) * (total_queries - query_count)) + (float(avg_execution_time) * query_count)
            ) / total_queries

            # Met à jour le compteur d'opérations
            if operation_type in table_info["operation_type"]:
                table_info["operation_type"][operation_type] += 1
            else:
                table_info["operation_type"][operation_type] = 1

            table_info["columns"] = elements_distincts(table_info["columns"] + columns)

            return  # Sortir après mise à jour

    # Si la table n'existe pas, ajouter une nouvelle entrée
    new_table_info = {
        "table_name": table_name,
        "query_count": query_count,
        "avg_execution_time": avg_execution_time,
        "rows": rows,
        "columns": columns,
        "operation_type": {operation_type: 1}  # Stockage sous forme de dictionnaire
    }
    tables_info.append(new_table_info)